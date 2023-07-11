"""Define data models for various Ridwell objects."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, TypedDict, cast

from titlecase import titlecase

from .const import LOGGER
from .errors import RidwellError
from .query import (
    QUERY_SUBSCRIPTION_PICKUP_QUOTE,
    QUERY_SUBSCRIPTION_PICKUPS,
    QUERY_UPDATE_SUBSCRIPTION_PICKUP,
)


class PickupCategory(Enum):
    """Define a representation of a pickup category."""

    ADD_ON = "add_on"
    ROTATING = "rotating"
    STANDARD = "standard"


PICKUP_CATEGORIES_MAP = {
    "Batteries": PickupCategory.STANDARD,
    "Beyond the Bin": PickupCategory.ADD_ON,
    "Fluorescent Light Tubes": PickupCategory.ADD_ON,
    "Latex Paint": PickupCategory.ADD_ON,
    "Light Bulbs": PickupCategory.STANDARD,
    "Multi-Layer Plastic": PickupCategory.STANDARD,
    "Paint": PickupCategory.ADD_ON,
    "Plastic Film": PickupCategory.STANDARD,
    "Styrofoam": PickupCategory.ADD_ON,
    "Threads": PickupCategory.STANDARD,
}


class AddressType(TypedDict):
    """Define a type to represent an address."""

    street1: str
    city: str
    state: str
    postal_code: str


class EventState(Enum):
    """Define a representation of an event state."""

    INITIALIZED = "initialized"
    NOTIFIED = "notified"
    SCHEDULED = "scheduled"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


def convert_pickup_event_state(state: str) -> EventState:
    """Convert a raw pickup event state string into an EventState.

    Args:
        state: A raw event state.

    Returns:
        A parsed EventState object.
    """
    try:
        return EventState(state)
    except ValueError:
        LOGGER.warning("Unknown pickup event state: %s", state)
        return EventState.UNKNOWN


@dataclass(frozen=True)
class RidwellAccount:
    """Define a Ridwell account."""

    _async_request: Callable[..., Awaitable[dict[str, Any]]] = field(compare=False)

    account_id: str
    address: AddressType
    email: str
    full_name: str
    phone: str
    subscription_id: str
    subscription_active: bool

    async def async_get_next_pickup_event(self) -> RidwellPickupEvent:
        """Get the next pickup event based on today's date.

        Returns:
            A RidwellPickupEvent object.

        Raises:
            RidwellError: Raised when no valid pickup events are found.
        """
        pickup_events = await self.async_get_pickup_events()
        for event in pickup_events:
            if event.pickup_date >= date.today():
                return event
        raise RidwellError("No pickup events found after today")

    async def async_get_pickup_events(self) -> list[RidwellPickupEvent]:
        """Get pickup events for this subscription.

        Returns:
            A list of RidwellPickupEvent objects.
        """
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

    category: PickupCategory = field(init=False)

    def __post_init__(self) -> None:
        """Perform some post-init init."""
        category = PICKUP_CATEGORIES_MAP.get(self.name, PickupCategory.ROTATING)

        if category == PickupCategory.ROTATING:
            # Our method of detecting rotating pickups is pretty "loose" (i.e., if a
            # category isn't a known standard or add-on, we assume it's rotating). This
            # could lead to future issues if Ridwell introduces a new standard or add-on
            # type that isn't mapped here. We try to be unintrusive and merely log that
            # we've found a "rotating" pickup so that it can later tell the full story:
            LOGGER.info("Detected assumed rotating pickup: %s", self.name)

        object.__setattr__(
            self,
            "category",
            PICKUP_CATEGORIES_MAP.get(self.name, PickupCategory.ROTATING),
        )


@dataclass(frozen=True)
class RidwellPickupEvent:
    """Define a Ridwell pickup event."""

    _async_request: Callable[..., Awaitable[dict[str, Any]]] = field(compare=False)

    event_id: str
    pickup_date: date
    pickups: list[RidwellPickup]
    state: EventState

    async def _async_opt(self, state: EventState) -> None:
        """Define a helper to opt in/out to/from the pickup event.

        Args:
            state: An EventState object denoting the desired state.
        """
        data = await self._async_request(
            json={
                "operationName": "updateSubscriptionPickup",
                "variables": {
                    "input": {
                        "subscriptionPickupId": self.event_id,
                        "state": state.value,
                    }
                },
                "query": QUERY_UPDATE_SUBSCRIPTION_PICKUP,
            },
        )

        object.__setattr__(
            self,
            "state",
            convert_pickup_event_state(
                data["data"]["updateSubscriptionPickup"]["subscriptionPickup"]["state"]
            ),
        )

    async def async_get_estimated_cost(self) -> float:
        """Get the estimated cost (USD) of this pickup based on its pickup types.

        Returns:
            A float denoting the estimated cost.
        """
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
