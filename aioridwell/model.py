"""Define data models for various Ridwell objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Callable, Literal, TypedDict, cast

from titlecase import titlecase

from .const import LOGGER
from .errors import RidwellError
from .query import (
    QUERY_SUBSCRIPTION_PICKUP_QUOTE,
    QUERY_SUBSCRIPTION_PICKUPS,
    QUERY_UPDATE_SUBSCRIPTION_PICKUP,
)

CATEGORY_ADD_ON = "add_on"
CATEGORY_ROTATING = "rotating"
CATEGORY_STANDARD = "standard"

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


class EventState(Enum):
    """Define a representation of an event state."""

    SCHEDULED = 1
    SKIPPED = 2
    INITIALIZED = 3
    UNKNOWN = 99


def convert_pickup_event_state(state: str) -> EventState:
    """Convert a raw pickup event state string into an EventState."""
    try:
        return EventState[state.upper()]
    except KeyError:
        LOGGER.warning("Unknown pickup event state: %s", state)
        return EventState.UNKNOWN


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
                convert_pickup_event_state(event_data["state"]),
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


@dataclass()
class RidwellPickupEvent:
    """Define a Ridwell pickup event."""

    _async_request: Callable = field(compare=False)

    event_id: str
    pickup_date: date
    pickups: list[RidwellPickup]
    state: EventState

    async def _async_opt(self, state: EventState) -> None:
        """Define a helper to opt in/out to/from the pickup event."""
        raw_state = state.name.lower()

        data = await self._async_request(
            json={
                "operationName": "updateSubscriptionPickup",
                "variables": {
                    "input": {
                        "subscriptionPickupId": self.event_id,
                        "state": raw_state,
                    }
                },
                "query": QUERY_UPDATE_SUBSCRIPTION_PICKUP,
            },
        )

        self.state = convert_pickup_event_state(
            data["data"]["updateSubscriptionPickup"]["subscriptionPickup"]["state"]
        )

    async def async_get_estimated_cost(self) -> float:
        """Get the estimated cost (USD) of this pickup based on its pickup types."""
        if not self.pickups:
            return 0.0

        resp = await self._async_request(
            json={
                "operationName": "subscriptionPickupQuote",
                "variables": {
                    "input": {
                        "subscriptionPickupId": self.event_id,
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

    async def async_opt_in(self) -> None:
        """Opt in to the pickup event."""
        await self._async_opt(EventState.SCHEDULED)

    async def async_opt_out(self) -> None:
        """Opt out from the pickup event."""
        await self._async_opt(EventState.SKIPPED)
