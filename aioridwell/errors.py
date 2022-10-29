"""Define package exceptions."""
from __future__ import annotations

from typing import Any


class RidwellError(Exception):
    """Define a base exception."""

    pass


class InvalidCredentialsError(RidwellError):
    """Define an error related to a bad credentials."""

    pass


class RequestError(RidwellError):
    """Define an error related to a bad HTTP request."""

    pass


class TokenExpiredError(RidwellError):
    """Define an error related to an expired token."""

    pass


DATA_ERROR_MAP = {
    "The password you entered is incorrect. Please try again.": InvalidCredentialsError,
    "login required": TokenExpiredError,
}


def raise_for_data_error(data: dict[str, Any]) -> None:
    """Raise an appropriate error if a message exists in the response data.

    Args:
        data: An API response payload.

    Raises:
        exc: A RidwellError subclass.
    """
    if "errors" not in data:
        return

    # A response payload may feasibly contain several errors (based on its JSON
    # structure), so we only handle the first one:
    first_error = data["errors"][0]
    message = first_error["message"]
    exc = DATA_ERROR_MAP.get(message, RequestError)
    raise exc(message)
