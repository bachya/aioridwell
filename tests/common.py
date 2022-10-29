"""Define common test utilities."""
from __future__ import annotations

import os
from time import time

import jwt


def generate_jwt(*, issued_at: float | None = None) -> str:
    """Generate a JWT.

    Args:
        issued_at: A timestamp at which the JWT is issued.

    Returns:
        The JWT string.
    """
    if not issued_at:
        issued_at = time()

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
    """Load a fixture.

    Args:
        filename: The filename of the fixtures/ file to load.

    Returns:
        A string containing the contents of the file.
    """
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()
