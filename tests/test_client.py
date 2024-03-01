"""Define tests for the client."""

import logging
from time import time
from typing import Any
from unittest.mock import Mock

import aiohttp
import pytest
from aresponses import ResponsesMockServer

from aioridwell import async_get_client
from aioridwell.errors import InvalidCredentialsError, RequestError

from .common import generate_jwt


@pytest.mark.asyncio
async def test_dashboard_url(
    authenticated_ridwell_api_server: ResponsesMockServer,
) -> None:
    """Test getting the dashboard URL for a user.

    Args:
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
    """
    async with authenticated_ridwell_api_server:
        client = await async_get_client("user", "password")
        url = client.get_dashboard_url()
        assert url == "https://www.ridwell.com/users/userId1/dashboard"


@pytest.mark.asyncio
async def test_expired_token_successful(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    authentication_response: dict[str, Any],
    caplog: Mock,
    token_expired_response: dict[str, Any],
) -> None:
    """Test that getting a new access token successfully retries the request.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        authentication_response: An API response payload.
        caplog: A mocked logging utility.
        token_expired_response: An API response payload.
    """
    caplog.set_level(logging.INFO)

    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                token_expired_response, status=200
            ),
        )

        # Simulate a JWT that's generated at some point in the future from the original
        # one:
        authentication_response["data"]["createAuthentication"][
            "authenticationToken"
        ] = generate_jwt(issued_at=round(time()) + 1000)

        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                authentication_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response({}, status=200),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client(
                "user",
                "password",
                session=session,
                # We set this parameter low so that this test doesn't take longer than
                # necessary:
                request_retry_delay=0,
            )

            # Perform a fake request that has an expired token:
            await client.async_request()
            assert any(
                "Token failed; refreshing and trying again" in e.message
                for e in caplog.records
            )

            # Verify that the token actually changed between retries:
            request_history = authenticated_ridwell_api_server.history
            token_1 = request_history[1].request.headers["Authorization"]
            token_2 = request_history[3].request.headers["Authorization"]
            assert token_1 != token_2

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_expired_token_failure(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
    authentication_response: dict[str, Any],
    token_expired_response: dict[str, Any],
) -> None:
    """Test that failing to get a new access token is handled correctly.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
        authentication_response: An API response payload.
        token_expired_response: An API response payload.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                token_expired_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                authentication_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                token_expired_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                authentication_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                token_expired_response, status=200
            ),
        )
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aiohttp.web_response.json_response(
                authentication_response, status=200
            ),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client(
                "user",
                "password",
                session=session,
                # We set this parameter low so that this test doesn't take longer than
                # necessary:
                request_retry_delay=0,
            )

            # Perform a fake request that has an expired token:
            with pytest.raises(InvalidCredentialsError):
                await client.async_request()

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_http_error(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
) -> None:
    """Test that a repeated HTTP error is handled.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
    """
    async with authenticated_ridwell_api_server:
        authenticated_ridwell_api_server.add(
            "api.ridwell.com",
            "/",
            "post",
            response=aresponses.Response(text="Not Found", status=404),
        )

        async with aiohttp.ClientSession() as session:
            client = await async_get_client(
                "user",
                "password",
                session=session,
                # We set this parameter low so that this test doesn't take longer than
                # necessary:
                request_retry_delay=0,
            )

            # Perform a fake request that has an expired token:
            with pytest.raises(RequestError):
                await client.async_request()

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_invalid_credentials(
    aresponses: ResponsesMockServer,
    invalid_credentials_response: dict[str, Any],
) -> None:
    """Test that invalid credentials on login are dealt with immediately (no retry).

    Args:
        aresponses: An aresponses server.
        invalid_credentials_response: An API response payload.
    """
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            invalid_credentials_response, status=200
        ),
    )

    async with aiohttp.ClientSession() as session:
        with pytest.raises(InvalidCredentialsError):
            await async_get_client("user", "password", session=session)

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_create_client(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
) -> None:
    """Test the successful creation of a client.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
    """
    async with authenticated_ridwell_api_server, aiohttp.ClientSession() as session:
        client = await async_get_client("user", "password", session=session)
        assert client.user_id == "userId1"

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_create_client_no_session(
    aresponses: ResponsesMockServer,
    authenticated_ridwell_api_server: ResponsesMockServer,
) -> None:
    """Test the successful creation of a client without an explicit ClientSession.

    Args:
        aresponses: An aresponses server.
        authenticated_ridwell_api_server: A mocked authenticated Ridwell API server.
    """
    async with authenticated_ridwell_api_server:
        client = await async_get_client("user", "password")
        assert client.user_id == "userId1"

    aresponses.assert_plan_strictly_followed()
