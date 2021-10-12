"""Define tests for the client."""
import logging
from time import time

import aiohttp
import pytest

from aioridwell import async_get_client
from aioridwell.errors import InvalidCredentialsError, RequestError

from .common import generate_jwt


@pytest.mark.asyncio
async def test_expired_token_successful(
    aresponses, authentication_response, caplog, token_expired_response
):
    """Test that getting a new access token successfully retries the request."""
    caplog.set_level(logging.INFO)

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
        response=aiohttp.web_response.json_response(token_expired_response, status=200),
    )

    # Simulate a JWT that's generated at some point in the future from the original one:
    authentication_response["data"]["createAuthentication"][
        "authenticationToken"
    ] = generate_jwt(issued_at=round(time()) + 1000)

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
        token_1 = aresponses.history[1].request.headers["Authorization"]
        token_2 = aresponses.history[3].request.headers["Authorization"]
        assert token_1 != token_2

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_expired_token_failure(
    aresponses, authentication_response, token_expired_response
):
    """Test that failing to get a new access token is handled correctly."""
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
        response=aiohttp.web_response.json_response(token_expired_response, status=200),
    )
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
        response=aiohttp.web_response.json_response(token_expired_response, status=200),
    )
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
        response=aiohttp.web_response.json_response(token_expired_response, status=200),
    )
    aresponses.add(
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
async def test_http_error(aresponses, authentication_response):
    """Test that a repeated HTTP error is handled."""
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
async def test_invalid_credentials(aresponses, invalid_credentials_response):
    """Test that invalid credentials on login are dealt with immediately (no retry)."""
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
async def test_create_client(aresponses, authentication_response):
    """Test the successful creation of a client."""
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )

    async with aiohttp.ClientSession() as session:
        client = await async_get_client("user", "password", session=session)
        assert client.user_id == "userId1"

    aresponses.assert_plan_strictly_followed()


@pytest.mark.asyncio
async def test_create_client_no_session(aresponses, authentication_response):
    """Test the successful creation of a client without an explicit ClientSession."""
    aresponses.add(
        "api.ridwell.com",
        "/",
        "post",
        response=aiohttp.web_response.json_response(
            authentication_response, status=200
        ),
    )

    client = await async_get_client("user", "password")
    assert client.user_id == "userId1"

    aresponses.assert_plan_strictly_followed()
