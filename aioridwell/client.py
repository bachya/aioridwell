"""Define an API client."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, TypedDict, cast

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
import jwt

from .const import LOGGER
from .errors import (
    InvalidCredentialsError,
    RequestError,
    TokenExpiredError,
    raise_for_data_error,
)
from .query import QUERY_CREATE_AUTHENTICATION, QUERY_SUBSCRIPTION_DATA, QUERY_USER_DATA

API_BASE_URL = "https://api.ridwell.com"

DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 1
DEFAULT_TIMEOUT = 10


class AddressType(TypedDict):
    """Define a type to represent an address."""

    street1: str
    city: str
    state: str
    postal_code: str


@dataclass(frozen=True)
class PickupEvent:
    """Define a waste pickup event."""

    address: AddressType
    pickup_date: date
    pickup_types: list[str]
    subscription_active: bool


def decode_jwt(encoded_jwt: str) -> dict[str, Any]:
    """Decode a JWT and return its data (including actual datetimes)."""
    return cast(
        Dict[str, Any],
        jwt.decode(
            encoded_jwt,
            "secret",
            algorithms=["HS256"],
            options={"verify_signature": False},
        ),
    )


class Client:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Define the client."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        request_retries: int = DEFAULT_RETRIES,
        request_retry_delay: int = DEFAULT_RETRY_DELAY,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize.

        Note that this is not intended to be instantiated directly; instead, users
        should use the async_get_client coroutine method.
        """
        self._email = email
        self._password = password
        self._request_retries = request_retries
        self._request_retry_delay = request_retry_delay
        self._session = session

        # Intended to be filled in after login:
        self._token: str | None = None
        self.user_id: str | None

    async def async_authenticate(self) -> None:
        """Authenticate the API."""
        resp = await self.async_request(
            json={
                "operationName": "createAuthentication",
                "variables": {
                    "input": {"emailOrPhone": self._email, "password": self._password}
                },
                "query": QUERY_CREATE_AUTHENTICATION,
            },
        )
        self._token = resp["data"]["createAuthentication"]["authenticationToken"]
        assert self._token
        token_data = decode_jwt(self._token)
        self.user_id = token_data["ridwell/userId"]

    async def async_get_pickup_events(self) -> list[PickupEvent]:
        """Get upcoming pickup events."""
        data = await self.async_request(
            json={
                "operationName": "user",
                "variables": {"id": self.user_id},
                "query": QUERY_SUBSCRIPTION_DATA,
            }
        )

        return [
            PickupEvent(
                account["address"],
                datetime.strptime(event["startOn"], "%Y-%m-%d").date(),
                sorted([waste["category"]["slug"] for waste in event["pickupOffers"]]),
                account["activeSubscription"]["state"] == "active",
            )
            for account in data["data"]["user"]["accounts"]
            for event in account["activeSubscription"]["futureSubscriptionPickups"]
        ]

    async def async_get_user_data(self) -> dict[str, Any]:
        """Get all user data."""
        return await self.async_request(
            json={
                "operationName": "user",
                "variables": {"id": self.user_id},
                "query": QUERY_USER_DATA,
            }
        )

    async def async_request(self, **kwargs: dict[str, Any]) -> dict[str, Any]:
        """Make an API request (based on a Ridwell "query string")."""
        kwargs.setdefault("headers", {})

        use_running_session = self._session and not self._session.closed
        if use_running_session:
            session = self._session
        else:
            session = ClientSession(timeout=ClientTimeout(total=DEFAULT_TIMEOUT))

        assert session

        data: dict[str, Any] = {}
        retry = 0

        while retry < self._request_retries:
            if self._token:
                kwargs["headers"]["Authorization"] = f"Bearer {self._token}"
            async with session.request("post", API_BASE_URL, **kwargs) as resp:
                data = await resp.json()

                try:
                    resp.raise_for_status()
                except ClientError as err:
                    raise RequestError(err) from err

                # Ridwell's API can return HTTP 200 responses that are still errors, so
                # we make sure to check for that:
                try:
                    raise_for_data_error(data)
                except TokenExpiredError:
                    retry += 1
                    LOGGER.debug(
                        "Token failed; refreshing and trying again (attempt %s of %s)",
                        retry,
                        self._request_retries,
                    )
                    await self.async_authenticate()
                    await asyncio.sleep(self._request_retry_delay)
                    continue

                break
        else:
            # We only end up here if we continue to have credential issues after
            # several retries:
            raise InvalidCredentialsError("Unable to refresh access token") from None

        if not use_running_session:
            await session.close()

        LOGGER.debug("Received data: %s", data)

        return data


async def async_get_client(
    email: str,
    password: str,
    *,
    request_retries: int = DEFAULT_RETRIES,
    request_retry_delay: int = DEFAULT_RETRY_DELAY,
    session: ClientSession | None = None,
) -> Client:
    """Get an authenticated client."""
    client = Client(
        email,
        password,
        request_retries=request_retries,
        request_retry_delay=request_retry_delay,
        session=session,
    )
    await client.async_authenticate()
    return client
