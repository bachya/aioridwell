"""Run an example script to quickly test."""
import asyncio
import logging

from aiohttp import ClientSession

from aioridwell import async_get_client
from aioridwell.errors import RidwellError

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL>"
PASSWORD = "<PASSWORD>"


async def main() -> None:
    """Create the aiohttp session and run the example."""
    logging.basicConfig(level=logging.INFO)
    async with ClientSession() as session:
        try:
            client = await async_get_client(EMAIL, PASSWORD, session=session)
            # _LOGGER.info("User ID: %s", client.user_id)

            # user_data = await client.async_get_user_data()
            # _LOGGER.info("User Data: %s", user_data)

            pickup_events = await client.async_get_pickup_events()
            _LOGGER.info("Subscription Data: %s", pickup_events)
        except RidwellError as err:
            _LOGGER.error("There was an error: %s", err)


asyncio.run(main())
