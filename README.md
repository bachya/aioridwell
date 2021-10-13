# ♻️ aioridwell: A Python3, asyncio-based API for interacting with Ridwell

[![CI](https://github.com/bachya/aioridwell/workflows/CI/badge.svg)](https://github.com/bachya/aioridwell/actions)
[![PyPi](https://img.shields.io/pypi/v/aioridwell.svg)](https://pypi.python.org/pypi/aioridwell)
[![Version](https://img.shields.io/pypi/pyversions/aioridwell.svg)](https://pypi.python.org/pypi/aioridwell)
[![License](https://img.shields.io/pypi/l/aioridwell.svg)](https://github.com/bachya/aioridwell/blob/master/LICENSE)
[![Code Coverage](https://codecov.io/gh/bachya/aioridwell/branch/master/graph/badge.svg)](https://codecov.io/gh/bachya/aioridwell)
[![Maintainability](https://api.codeclimate.com/v1/badges/9c1dcc1c991cecb06eda/maintainability)](https://codeclimate.com/github/bachya/aioridwell/maintainability)
[![Say Thanks](https://img.shields.io/badge/SayThanks-!-1EAEDB.svg)](https://saythanks.io/to/bachya)

`aioridwell` is a Python 3, asyncio-friendly library for interacting with
[Ridwell](https://ridwell.com) to view information on upcoming recycling pickups.

- [Installation](#installation)
- [Python Versions](#python-versions)
- [Usage](#usage)
- [Contributing](#contributing)

# Installation

```python
pip install aioridwell
```

# Python Versions

`aioridwell` is currently supported on:

* Python 3.8
* Python 3.9 

# Usage

## Creating and Using a Client

The `Client` is the primary method of interacting with the API:

```python
import asyncio

from aioridwell import async_get_client


async def main() -> None:
    client = await async_get_client("<EMAIL>", "<PASSWORD>")
    # ...


asyncio.run(main())
```

By default, the library creates a new connection to the API with each coroutine. If
you are calling a large number of coroutines (or merely want to squeeze out every second of runtime savings possible), an
[`aiohttp`](https://github.com/aio-libs/aiohttp) `ClientSession` can be used for connection
pooling:

```python
import asyncio

from aiohttp import ClientSession

from aiowatttime import Client


async def main() -> None:
    async with ClientSession() as session:
        client = await async_get_client("<EMAIL>", "<PASSWORD>", session=session)
        # ...


asyncio.run(main())
```

## Getting Accounts

Getting all accounts associated with this email address is easy:

```python
import asyncio

from aioridwell import async_get_client


async def main() -> None:
    client = await async_get_client("<EMAIL>", "<PASSWORD>")

    accounts = await client.async_get_accounts()
    # >>> {"account_id_1": RidwellAccount(...), ...}


asyncio.run(main())
```

The `RidwellAccount` object comes with some useful properties:

* `account_id`: the Ridwell ID for the account
* `address`: the address being serviced
* `email`: the email address on the account
* `full_name`: the full name of the account owner
* `phone`: the phone number of the account owner
* `subscription_id`: the Ridwell ID for the primary subscription
* `subscription_active`: whether the primary subscription is active

## Getting Pickup Events

Getting all pickup events associated with an account is easy, too:

```python
import asyncio

from aioridwell import async_get_client


async def main() -> None:
    client = await async_get_client("<EMAIL>", "<PASSWORD>")

    accounts = await client.async_get_accounts()
    for account in accounts.values():
        events = await account.async_get_pickup_events()
        # >>> [RidwellPickupEvent(...), ...]


asyncio.run(main())
```

The `RidwellPickupEvent` object comes with some useful properties:

* `pickup_date`: the date of the pickup (in `datetime.date` format)
* `pickups`: a list of `RidwellPickup` objects
* `state`: either `initialized` (not scheduled for pickup) or `scheduled`

Likewise, the `RidwellPickup` object comes with some useful properties:

* `category`: the category of the pickup (`standard`, `rotating`, or `add_on`)
* `name`: the name of the item being picked up
* `offer_id`: the Ridwell ID for this particular offer
* `priority`: the pickup priority
* `product_id`: the Ridwell ID for this particular product
* `quantity`: the amount of the product being picked up

### Calculating a Pickup Event's Esimated Cost

Calculating the estimated cost of a pickup event is, you guessed it, easy:

```python
import asyncio

from aioridwell import async_get_client


async def main() -> None:
    client = await async_get_client("<EMAIL>", "<PASSWORD>")

    accounts = await client.async_get_accounts()
    for account in accounts.values():
        events = await account.async_get_pickup_events()
        event_1_cost = await events[0].async_get_estimated_cost()
        # >>> 22.00


asyncio.run(main())
```

# Contributing

1. [Check for open features/bugs](https://github.com/bachya/aioridwell/issues)
  or [initiate a discussion on one](https://github.com/bachya/aioridwell/issues/new).
2. [Fork the repository](https://github.com/bachya/aioridwell/fork).
3. (_optional, but highly recommended_) Create a virtual environment: `python3 -m venv .venv`
4. (_optional, but highly recommended_) Enter the virtual environment: `source ./.venv/bin/activate`
5. Install the dev environment: `script/setup`
6. Code your new feature or bug fix.
7. Write tests that cover your new functionality.
8. Run tests and ensure 100% code coverage: `script/test`
9. Update `README.md` with any new documentation.
10. Add yourself to `AUTHORS.md`.
11. Submit a pull request!
