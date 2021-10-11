"""Define common test utilities."""
import os
from time import time

import jwt


def generate_jwt(*, issued_at: float = time()) -> str:
    """Generate a JWT."""
    return jwt.encode(
        {
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
            "exp": issued_at + (2 * 7 * 24 * 60 * 60),
        },
        "secret",
        algorithm="HS256",
    )


def load_fixture(filename: str) -> str:
    """Load a fixture."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()
