"""Define tests for the client."""
import logging
from datetime import date
from typing import Any
from unittest.mock import Mock

import aiohttp
import pytest
from aresponses import ResponsesMockServer
from freezegun import freeze_time

from aioridwell import async_get_client
from aioridwell.errors import RidwellError
from aioridwell.model import EventState, PickupCategory


@pytest.mark.asyncio
async def test_get_accounts(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    user_response: dict[str, Any],
) -> None:
    """Test getting all accounts associated with a client.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        user_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"
            assert account.address == {
                "street1": "123 Main Street",
                "city": "Seattle",
                "subdivision": "WA",
                "postalCode": "98101",
            }
            assert account.email == "user@email.com"
            assert account.full_name == "Jane Doe"
            assert account.phone == "1234567890"
            assert account.subscription_id == "subscriptionId1"
            assert account.subscription_active is True

    aresponses.assert_plan_strictly_followed()


@freeze_time("2021-10-01")
@pytest.mark.asyncio
async def test_get_next_pickup_event(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    caplog: Mock,
    upcoming_subscription_pickups_response: dict[str, Any],
    user_response: dict[str, Any],
) -> None:
    """Test getting the next upcoming pickup event associated with an account.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        caplog: A mocked logging utility.
        upcoming_subscription_pickups_response: An API response payload.
        user_response: An API response payload.
    """
    caplog.set_level(logging.DEBUG)

    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                upcoming_subscription_pickups_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"

            pickup_event = await account.async_get_next_pickup_event()
            assert pickup_event.pickup_date == date(2021, 10, 13)
            assert pickup_event.state == EventState.SCHEDULED

            assert len(pickup_event.pickups) == 3
            assert pickup_event.pickups[0].name == "Threads"
            assert pickup_event.pickups[0].offer_id == "pickupOffer1"
            assert pickup_event.pickups[0].priority == 1
            assert pickup_event.pickups[0].product_id == "pickupProduct1"
            assert pickup_event.pickups[0].quantity == 1
            assert pickup_event.pickups[0].category == PickupCategory.STANDARD
            assert pickup_event.pickups[1].name == "Beyond the Bin"
            assert pickup_event.pickups[1].offer_id == "pickupOffer2"
            assert pickup_event.pickups[1].priority == 1
            assert pickup_event.pickups[1].product_id == "pickupProduct2"
            assert pickup_event.pickups[1].quantity == 2
            assert pickup_event.pickups[1].category == PickupCategory.ADD_ON
            assert pickup_event.pickups[2].name == "Chocolate"
            assert pickup_event.pickups[2].offer_id == "pickupOffer3"
            assert pickup_event.pickups[2].priority == 2
            assert pickup_event.pickups[2].product_id == "pickupProduct3"
            assert pickup_event.pickups[2].quantity == 1
            assert pickup_event.pickups[2].category == PickupCategory.ROTATING

            assert any(
                "Detected assumed rotating pickup: Chocolate" in e.message
                for e in caplog.records
            )

    aresponses.assert_plan_strictly_followed()


@freeze_time("2021-10-31")
@pytest.mark.asyncio
async def test_get_next_pickup_event_none_left(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    upcoming_subscription_pickups_response: dict[str, Any],
    user_response: dict[str, Any],
) -> None:
    """Test getting the next pickup event with no supporting data.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        upcoming_subscription_pickups_response: An API response payload.
        user_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                upcoming_subscription_pickups_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"

            with pytest.raises(RidwellError):
                await account.async_get_next_pickup_event()

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_get_pickup_events(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    upcoming_subscription_pickups_response: dict[str, Any],
    user_response: dict[str, Any],
) -> None:
    """Test getting all upcoming pickup events associated with an account.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        upcoming_subscription_pickups_response: An API response payload.
        user_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                upcoming_subscription_pickups_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"

            pickup_events = await account.async_get_pickup_events()
            assert len(pickup_events) == 2
            assert pickup_events[0].pickup_date == date(2021, 10, 13)
            assert pickup_events[0].state == EventState.SCHEDULED
            assert pickup_events[1].pickup_date == date(2021, 10, 27)
            assert pickup_events[1].state == EventState.INITIALIZED

            assert len(pickup_events[0].pickups) == 3
            assert pickup_events[0].pickups[0].name == "Threads"
            assert pickup_events[0].pickups[0].offer_id == "pickupOffer1"
            assert pickup_events[0].pickups[0].priority == 1
            assert pickup_events[0].pickups[0].product_id == "pickupProduct1"
            assert pickup_events[0].pickups[0].quantity == 1
            assert pickup_events[0].pickups[0].category == PickupCategory.STANDARD
            assert pickup_events[0].pickups[1].name == "Beyond the Bin"
            assert pickup_events[0].pickups[1].offer_id == "pickupOffer2"
            assert pickup_events[0].pickups[1].priority == 1
            assert pickup_events[0].pickups[1].product_id == "pickupProduct2"
            assert pickup_events[0].pickups[1].quantity == 2
            assert pickup_events[0].pickups[1].category == PickupCategory.ADD_ON
            assert pickup_events[0].pickups[2].name == "Chocolate"
            assert pickup_events[0].pickups[2].offer_id == "pickupOffer3"
            assert pickup_events[0].pickups[2].priority == 2
            assert pickup_events[0].pickups[2].product_id == "pickupProduct3"
            assert pickup_events[0].pickups[2].quantity == 1
            assert pickup_events[0].pickups[2].category == PickupCategory.ROTATING

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_get_pickup_events_cost(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    subscription_pickup_quote_response: dict[str, Any],
    upcoming_subscription_pickups_response: dict[str, Any],
    user_response: dict[str, Any],
) -> None:
    """Test getting the cost of upcoming pickup events.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        subscription_pickup_quote_response: An API response payload.
        upcoming_subscription_pickups_response: An API response payload.
        user_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                upcoming_subscription_pickups_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                subscription_pickup_quote_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"

            pickup_events = await account.async_get_pickup_events()
            assert len(pickup_events) == 2

            event_1_cost = await pickup_events[0].async_get_estimated_cost()
            assert event_1_cost == 22.00

            event_2_cost = await pickup_events[1].async_get_estimated_cost()
            assert event_2_cost == 0.00

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_opt_in(  # pylint: disable=too-many-arguments
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    caplog: Mock,
    upcoming_subscription_pickups_response: dict[str, Any],
    update_subscription_pickup_response: dict[str, Any],
    user_response: dict[str, Any],
) -> None:
    """Test opting in/out of a pickup.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        caplog: A mocked logging utility.
        upcoming_subscription_pickups_response: An API response payload.
        update_subscription_pickup_response: An API response payload.
        user_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(user_response, status=200),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                upcoming_subscription_pickups_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                update_subscription_pickup_response, status=200
            ),
        )

        update_subscription_pickup_response["data"]["updateSubscriptionPickup"][
            "subscriptionPickup"
        ]["state"] = "skipped"

        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                update_subscription_pickup_response, status=200
            ),
        )

        update_subscription_pickup_response["data"]["updateSubscriptionPickup"][
            "subscriptionPickup"
        ]["state"] = "fake_state"

        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                update_subscription_pickup_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client("user", "password", session=session)
            assert client.user_id == "userId1"

            accounts = await client.async_get_accounts()
            assert len(accounts) == 1

            account = accounts["accountId1"]
            assert account.account_id == "accountId1"

            pickup_events = await account.async_get_pickup_events()
            assert len(pickup_events) == 2

            await pickup_events[0].async_opt_in()
            assert pickup_events[0].state == EventState.SCHEDULED

            await pickup_events[0].async_opt_out()
            new_state = pickup_events[0].state
            assert new_state == EventState.SKIPPED

            await pickup_events[0].async_opt_in()
            assert any(
                "Unknown pickup event state: fake_state" in e.message
                for e in caplog.records
            )
            assert pickup_events[0].state == EventState.UNKNOWN

    aresponses.assert_plan_strictly_followed()
