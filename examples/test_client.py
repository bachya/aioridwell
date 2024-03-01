"""Run an example script to quickly test."""

import asyncio
import logging

from aiohttp import ClientSession

from aioridwell import async_get_client
from aioridwell.errors import RidwellError

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL>"
PASSWORD = "<PASSWORD>"  # noqa: S105


async def main() -> None:
    """Create the aiohttp session and run the example."""
    logging.basicConfig(level=logging.INFO)
    async with ClientSession() as session:
        try:
            client = await async_get_client(EMAIL, PASSWORD, session=session)
            _LOGGER.info("User ID: %s", client.user_id)

            accounts = await client.async_get_accounts()
            _LOGGER.info("Accounts: %s", accounts)

            for account in accounts.values():
                events = await account.async_get_pickup_events()
                _LOGGER.info("Events for account ID %s: %s", account.account_id, events)

                first_event = events[0]
                estimated_addon_cost = (
                    await first_event.async_get_estimated_addon_cost()
                )
                _LOGGER.info(
                    "Estimated add-on cost for event %s: %s",
                    first_event.event_id,
                    estimated_addon_cost,
                )
        except RidwellError as err:
            _LOGGER.error("There was an error: %s", err)


asyncio.run(main())
