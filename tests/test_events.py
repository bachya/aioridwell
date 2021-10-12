"""Define tests for the client."""
from datetime import date

import aiohttp
import pytest

from aioridwell import async_get_client


@pytest.mark.asyncio
async def test_get_accounts(aresponses, authentication_response, user_response):
    """Test getting all accounts associated with a client."""
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )
    aresponses.add(
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


@pytest.mark.asyncio
async def test_get_pickup_events(
    aresponses,
    authentication_response,
    upcoming_subscription_pickups_response,
    user_response,
):
    """Test getting all upcoming pickup events associated with an account."""
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(user_response, status=200),
    )
    aresponses.add(
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
        assert pickup_events[0].state == "scheduled"
        assert pickup_events[1].pickup_date == date(2021, 10, 27)
        assert pickup_events[1].state == "initialized"

        assert len(pickup_events[0].pickups) == 2
        assert pickup_events[0].pickups[0].category == "Beyond the Bin"
        assert pickup_events[0].pickups[0].offer_id == "pickupOffer1"
        assert pickup_events[0].pickups[0].priority == 1
        assert pickup_events[0].pickups[0].product_id == "pickupProduct1"
        assert pickup_events[0].pickups[0].quantity == 1
        assert pickup_events[0].pickups[0].special is False
        assert pickup_events[0].pickups[1].category == "Chocolate"
        assert pickup_events[0].pickups[1].offer_id == "pickupOffer2"
        assert pickup_events[0].pickups[1].priority == 2
        assert pickup_events[0].pickups[1].product_id == "pickupProduct2"
        assert pickup_events[0].pickups[1].quantity == 1
        assert pickup_events[0].pickups[1].special is True

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_get_pickup_events_cost(
    aresponses,
    authentication_response,
    subscription_pickup_quote_response,
    upcoming_subscription_pickups_response,
    user_response,
):
    """Test getting the cost of upcoming pickup events."""
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(user_response, status=200),
    )
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            upcoming_subscription_pickups_response, status=200
        ),
    )
    aresponses.add(
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