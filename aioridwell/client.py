"""Define an API client."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, cast

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError, ContentTypeError
import jwt

from .const import LOGGER
from .errors import (
    InvalidCredentialsError,
    RequestError,
    TokenExpiredError,
    raise_for_data_error,
)
from .model import RidwellAccount
from .query import QUERY_ACCOUNT_DATA, QUERY_AUTH_DATA

API_BASE_URL = "https://api.ridwell.com"

DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 1
DEFAULT_TIMEOUT = 10


def decode_jwt(encoded_jwt: str) -> dict[str, Any]:
    """Decode and return a JWT."""
    return cast(
        Dict[str, Any],
        jwt.decode(
            encoded_jwt,
            "secret",
            algorithms=["HS256"],
            options={"verify_signature": False},
        ),
    )


class Client:  # pylint: disable=too-many-instance-attributes
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
                "query": QUERY_AUTH_DATA,
            },
        )
        self._token = resp["data"]["createAuthentication"]["authenticationToken"]
        assert self._token
        token_data = decode_jwt(self._token)
        self.user_id = token_data["ridwell/userId"]

    async def async_get_accounts(self) -> dict[str, RidwellAccount]:
        """Get all accounts for this user."""
        resp = await self.async_request(
            json={
                "operationName": "user",
                "variables": {"id": self.user_id},
                "query": QUERY_ACCOUNT_DATA,
            }
        )
        user_data = resp["data"]["user"]

        return {
            account["id"]: RidwellAccount(
                self.async_request,
                account["id"],
                account["address"],
                user_data["email"],
                user_data["fullName"],
                user_data["phone"],
                account["activeSubscription"]["id"],
                account["activeSubscription"]["state"] == "active",
            )
            for account in user_data["accounts"]
        }

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
                try:
                    data = await resp.json()
                    resp.raise_for_status()
                except (ClientError, ContentTypeError) as err:
                    raise RequestError(err) from err

                # Ridwell's API can return HTTP 200 responses that are still errors, so
                # we make sure to check for that:
                try:
                    raise_for_data_error(data)
                except TokenExpiredError:
                    retry += 1
                    LOGGER.info(
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

        LOGGER.debug(
            "Received data (operation: %s): %s",
            kwargs.get("json", {}).get("operationName"),
            data,
        )

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
