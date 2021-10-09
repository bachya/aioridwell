"""Define dynamic fixtures."""
import json
from time import time

import jwt
import pytest

from .common import load_fixture


@pytest.fixture(name="authentication_response")
def authentication_response_fixture(jwt_data):
    """Define a fixture to return an authentication response."""
    return {
        "data": {
            "createAuthentication": {
                "authenticationToken": jwt.encode(
                    jwt_data, "secret", algorithm="HS256"
                ),
                "__typename": "CreateAuthenticationOutput",
            }
        }
    }


@pytest.fixture(name="jwt_data")
def jwt_data_fixture():
    """Define a fixture to return a decoded JWT (with datetimes)."""
    # issued_at = round(time())
    # decoded_jwt_response["iat"]: issued_at
    # # The API appears to extend tokens that last for 2 weeks:
    # decoded_jwt_response["exp"]: issued_at * 2 * 7 * 24 * 60 * 60
    # return decoded_jwt_response
    issued_at = round(time())

    return {
        "ridwell/authId": "authId1",
        "ridwell/authType": "login",
        "ridwell/userId": "userId1",
        "ridwell/userIsConfirmed": True,
        "ridwell/userFirstName": "Jane",
        "ridwell/userRoles": [],
        "ridwell/userReferralCode": "JANE123",
        "ridwell/accounts": [
            {
                "id": "accountId1",
                "activeSubscriptionId": "subscriptionId1",
                "roles": ["owner"],
            }
        ],
        "ridwell/zoneSlug": "seattle-98101",
        "ridwell/marketSlug": "seattle",
        "iat": issued_at,
        # # The API appears to produce tokens that last for 2 weeks:
        "exp": issued_at + (2 * 7 * 24 * 60 * 60),
    }


@pytest.fixture(name="invalid_credentials_response", scope="session")
def invalid_credentials_response_fixture():
    """Define a fixture to return an invalid credentials response."""
    return json.loads(load_fixture("invalid_credentials_response.json"))


@pytest.fixture(name="token_expired_response", scope="session")
def token_expired_response_fixture():
    """Define a fixture to return an token expired response."""
    return json.loads(load_fixture("token_expired_response.json"))
