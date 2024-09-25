"""Define dynamic fixtures."""

import json
from collections.abc import Generator
from typing import Any, cast

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from .common import generate_jwt, load_fixture


@pytest.fixture(name="authenticated_ridwell_api_server")
def authenticated_ridwell_api_server_fixture(
    authentication_response: dict[str, Any],
) -> Generator[ResponsesMockServer]:
    """Return a fixture that mocks an authenticated Ridwell API server.

    Args:
        authentication_response: An API response payload
    """
    server = ResponsesMockServer()
    server.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )
    yield server


@pytest.fixture(name="authentication_response")
def authentication_response_fixture() -> dict[str, Any]:
    """Define a fixture to return an authentication response.

    Returns:
        An API payload response.
    """
    return {"data": {"createAuthentication": {"authenticationToken": generate_jwt()}}}


@pytest.fixture(name="invalid_credentials_response", scope="session")
def invalid_credentials_response_fixture() -> dict[str, Any]:
    """Define a fixture to return an invalid credentials response.

    Returns:
        An API payload response.
    """
    return cast(
        dict[str, Any], json.loads(load_fixture("invalid_credentials_response.json"))
    )


@pytest.fixture(name="subscription_pickup_quote_response", scope="session")
def subscription_pickup_quote_response_fixture() -> dict[str, Any]:
    """Define a fixture to return estimated event cost info.

    Returns:
        An API payload response.
    """
    return cast(
        dict[str, Any],
        json.loads(load_fixture("subscription_pickup_quote_response.json")),
    )


@pytest.fixture(name="token_expired_response", scope="session")
def token_expired_response_fixture() -> dict[str, Any]:
    """Define a fixture to return an token expired response.

    Returns:
        An API payload response.
    """
    return cast(dict[str, Any], json.loads(load_fixture("token_expired_response.json")))


@pytest.fixture(name="upcoming_subscription_pickups_response", scope="session")
def upcoming_subscription_pickups_response_fixture() -> dict[str, Any]:
    """Define a fixture to return an info on all upcoming pickups.

    Returns:
        An API payload response.
    """
    return cast(
        dict[str, Any],
        json.loads(load_fixture("upcoming_subscription_pickups_response.json")),
    )


@pytest.fixture(name="update_subscription_pickup_response", scope="session")
def update_subscription_pickup_response_fixture() -> dict[str, Any]:
    """Define a fixture to return a response to opt in to a pickup event.

    Returns:
        An API payload response.
    """
    return cast(
        dict[str, Any],
        json.loads(load_fixture("update_subscription_pickup_response.json")),
    )


@pytest.fixture(name="user_response", scope="session")
def user_response_fixture() -> dict[str, Any]:
    """Define a fixture to return an user info response.

    Returns:
        An API payload response.
    """
    return cast(dict[str, Any], json.loads(load_fixture("user_response.json")))
