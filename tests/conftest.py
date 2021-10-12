"""Define dynamic fixtures."""
import json

import pytest

from .common import generate_jwt, load_fixture


@pytest.fixture(name="authentication_response")
def authentication_response_fixture():
    """Define a fixture to return an authentication response."""
    return {"data": {"createAuthentication": {"authenticationToken": generate_jwt()}}}


@pytest.fixture(name="invalid_credentials_response", scope="session")
def invalid_credentials_response_fixture():
    """Define a fixture to return an invalid credentials response."""
    return json.loads(load_fixture("invalid_credentials_response.json"))


@pytest.fixture(name="subscription_pickup_quote_response", scope="session")
def subscription_pickup_quote_response_fixture():
    """Define a fixture to return estimated event cost info."""
    return json.loads(load_fixture("subscription_pickup_quote_response.json"))


@pytest.fixture(name="token_expired_response", scope="session")
def token_expired_response_fixture():
    """Define a fixture to return an token expired response."""
    return json.loads(load_fixture("token_expired_response.json"))


@pytest.fixture(name="upcoming_subscription_pickups_response", scope="session")
def upcoming_subscription_pickups_response_fixture():
    """Define a fixture to return an info on all upcoming pickups."""
    return json.loads(load_fixture("upcoming_subscription_pickups_response.json"))


@pytest.fixture(name="user_response", scope="session")
def user_response_fixture():
    """Define a fixture to return an user info response."""
    return json.loads(load_fixture("user_response.json"))
