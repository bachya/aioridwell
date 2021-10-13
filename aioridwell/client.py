"""Define an API client."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Dict, Literal, TypedDict, cast

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError, ContentTypeError
import jwt
from titlecase import titlecase

from .const import LOGGER
from .errors import (
    InvalidCredentialsError,
    RequestError,
    RidwellError,
    TokenExpiredError,
    raise_for_data_error,
)
from .query import (
    QUERY_ACCOUNT_DATA,
    QUERY_AUTH_DATA,
    QUERY_SUBSCRIPTION_PICKUP_QUOTE,
    QUERY_SUBSCRIPTION_PICKUPS,
)

API_BASE_URL = "https://api.ridwell.com"

DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 1
DEFAULT_TIMEOUT = 10

CATEGORY_ADD_ON = "add_on"
CATEGORY_ROTATING = "rotating"
CATEGORY_STANDARD = "standard"

EVENT_STATE_INITIALIIZED = "initialized"
EVENT_STATE_SCHEDULED = "scheduled"

PICKUP_TYPES_ADD_ON = [
    "Beyond the Bin",
    "Fluorescent Light Tubes",
    "Latex Paint",
    "Paint",
    "Styrofoam",
]
PICKUP_TYPES_STANDARD = [
    "Batteries",
    "Light Bulbs",
    "Plastic Film",
    "Threads",
]


class AddressType(TypedDict):
    """Define a type to represent an address."""

    street1: str
    city: str
    state: str
    postal_code: str


@dataclass(frozen=True)
class RidwellAccount:  # pylint: disable=too-many-instance-attributes
    """Define a Ridwell account."""

    _async_request: Callable = field(compare=False)

    account_id: str
    address: AddressType
    email: str
    full_name: str
    phone: str
    subscription_id: str
    subscription_active: bool

    async def async_get_next_pickup_event(self) -> RidwellPickupEvent:
        """Get the next pickup event based on today's date."""
        pickup_events = await self.async_get_pickup_events()
        for event in pickup_events:
            if event.pickup_date >= date.today():
                return event
        raise RidwellError("No pickup events found after today")

    async def async_get_pickup_events(self) -> list[RidwellPickupEvent]:
        """Get pickup events for this subscription."""
        resp = await self._async_request(
            json={
                "operationName": "upcomingSubscriptionPickups",
                "variables": {"subscriptionId": self.subscription_id},
                "query": QUERY_SUBSCRIPTION_PICKUPS,
            },
        )

        return [
            RidwellPickupEvent(
                self._async_request,
                event_data["id"],
                datetime.strptime(event_data["pickupOn"], "%Y-%m-%d").date(),
                [
                    RidwellPickup(
                        titlecase(
                            pickup["pickupOfferPickupProduct"]["pickupOffer"][
                                "category"
                            ]["name"]
                        ),
                        pickup["pickupOfferPickupProduct"]["pickupOffer"]["id"],
                        pickup["pickupOfferPickupProduct"]["pickupOffer"]["priority"],
                        pickup["pickupOfferPickupProduct"]["pickupProduct"]["id"],
                        pickup["quantity"],
                    )
                    for pickup in event_data["pickupProductSelections"]
                ],
                event_data["state"],
            )
            for event_data in resp["data"]["upcomingSubscriptionPickups"]
        ]


@dataclass(frozen=True)
class RidwellPickup:
    """Define a Ridwell pickup (i.e., the thing being picked up)."""

    name: str
    offer_id: str
    priority: int
    product_id: str
    quantity: int

    category: Literal["add_on", "rotating", "standard"] = field(init=False)

    def __post_init__(self) -> None:
        """Perform some post-init init."""
        if self.name in PICKUP_TYPES_ADD_ON:
            category = CATEGORY_ADD_ON
        elif self.name in PICKUP_TYPES_STANDARD:
            category = CATEGORY_STANDARD
        else:
            category = CATEGORY_ROTATING
        object.__setattr__(self, "category", category)


@dataclass(frozen=True)
class RidwellPickupEvent:
    """Define a Ridwell pickup event."""

    _async_request: Callable = field(compare=False)
    _event_id: str

    pickup_date: date
    pickups: list[RidwellPickup]
    state: Literal["initialized", "scheduled"]

    async def async_get_estimated_cost(self) -> float:
        """Get the estimated cost (USD) of this pickup based on its pickup types."""
        if not self.pickups:
            return 0.0

        resp = await self._async_request(
            json={
                "operationName": "subscriptionPickupQuote",
                "variables": {
                    "input": {
                        "subscriptionPickupId": self._event_id,
                        "addOnSelections": [
                            {
                                "productId": pickup.product_id,
                                "offerId": pickup.offer_id,
                                "quantity": pickup.quantity,
                            }
                            for pickup in self.pickups
                        ],
                    }
                },
                "query": QUERY_SUBSCRIPTION_PICKUP_QUOTE,
            },
        )

        return cast(float, resp["data"]["subscriptionPickupQuote"]["totalCents"] / 100)


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
