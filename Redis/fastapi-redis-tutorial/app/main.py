import functools
import json
import logging
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Union

import httpx
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import FastAPI

import redis.asyncio as redis_client
from redis.exceptions import ResponseError

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings

DEFAULT_KEY_PREFIX = 'is-bitcoin-lit'
COINGECKO_MARKET_CHART_URL = (
    "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    "?vs_currency=usd"
    "&days=1"
    "&interval=hourly"
)
TWO_MINUTES = 60 + 60
HOURLY_BUCKET = '3600000'
UNAVAILABLE = 'unavailable'

BitcoinPricePoint = Dict[str, Union[int, float]]
BitcoinPriceHistory = List[BitcoinPricePoint]


def prefixed_key(f):
    """
    A method decorator that prefixes return values.

    Prefixes any string that the decorated method `f` returns with the value of
    the `prefix` attribute on the owner object `self`.
    """

    def prefixed_method(*args, **kwargs):
        self = args[0]
        key = f(*args, **kwargs)
        return f'{self.prefix}:{key}'

    return prefixed_method


class Keys:
    """Methods to generate key names for Redis data structures."""

    def __init__(self, prefix: str = DEFAULT_KEY_PREFIX):
        self.prefix = prefix

    @prefixed_key
    def timeseries_sentiment_key(self) -> str:
        """A time series containing 30-second snapshots of BTC sentiment."""
        return f'sentiment:mean:30s'

    @prefixed_key
    def timeseries_price_key(self) -> str:
        """A time series containing 30-second snapshots of BTC price."""
        return f'price:mean:30s'

    @prefixed_key
    def cache_key(self) -> str:
        return f'cache'


class Config(BaseSettings):
    # The default URL expects the app to run using Docker and docker-compose.
    redis_url: str = "redis://localhost:6383"


log = logging.getLogger(__name__)
config = Config()
app = FastAPI(title='FastAPI Redis Tutorial')
redis = redis_client.from_url(config.redis_url, decode_responses=True)


async def add_many_to_timeseries(
    timeseries_key: str,
    data: BitcoinPriceHistory,
):
    """
    Add many price samples to a single timeseries key.
    """
    if not data:
        return None

    partial = functools.partial(redis.execute_command, 'TS.MADD')
    for datapoint in data:
        partial = functools.partial(
            partial,
            timeseries_key,
            int(datapoint['timestamp_ms']),
            float(datapoint['btc_price']),
        )
    return await partial()


def make_keys():
    return Keys()


def parse_coingecko_prices(payload: Dict[str, Any]) -> BitcoinPriceHistory:
    prices = payload.get('prices') or []
    normalized_prices: BitcoinPriceHistory = []

    for price_point in prices:
        if len(price_point) != 2:
            continue

        timestamp_ms, price = price_point
        normalized_prices.append(
            {
                'timestamp_ms': int(timestamp_ms),
                'btc_price': float(price),
            }
        )

    if not normalized_prices:
        raise ValueError('CoinGecko payload did not include any price samples.')

    return normalized_prices


async def persist(keys: Keys, data: Dict[str, Any]):
    ts_price_key = keys.timeseries_price_key()
    await add_many_to_timeseries(ts_price_key, parse_coingecko_prices(data))


async def get_latest_timestamp(ts_key: str):
    response = await redis.execute_command(
        'TS.GET', ts_key
    )

    # Returns a list of the structure [timestamp, value]
    return response

async def get_hourly_average(ts_key: str, top_of_the_hour: int):
    response = await redis.execute_command(
        'TS.RANGE', ts_key, top_of_the_hour, '+',
        'AGGREGATION', 'avg', HOURLY_BUCKET,
    )
    # Returns a list of the structure [timestamp, average].
    return response


def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, str) and v.endswith('+00:00'):
            try:
                dct[k] = datetime.fromisoformat(v)
            except:
                pass
    return dct


async def get_cache(keys: Keys):
    current_hour_cache_key = keys.cache_key()
    current_hour_stats = await redis.get(current_hour_cache_key)

    if current_hour_stats:
        return json.loads(current_hour_stats, object_hook=datetime_parser)


async def set_cache(data, keys: Keys):
    def serialize_dates(v):
        return v.isoformat() if isinstance(v, datetime) else v

    await redis.set(
        keys.cache_key(),
        json.dumps(data, default=serialize_dates),
        ex=TWO_MINUTES,
    )


def get_direction(last_three_hours, key: str):
    if not last_three_hours:
        return UNAVAILABLE

    if last_three_hours[0][key] is None or last_three_hours[-1][key] is None:
        return UNAVAILABLE

    if last_three_hours[0][key] < last_three_hours[-1][key]:
        return 'rising'
    elif last_three_hours[0][key] > last_three_hours[-1][key]:
        return 'falling'
    else:
        return 'flat'


async def calculate_three_hours_of_data(keys: Keys) -> Dict[str, Any]:
    price_key = keys.timeseries_price_key()
    latest_data = await get_latest_timestamp(price_key)

    if not latest_data:
        return {
            'hourly_average_of_averages': [],
            'sentiment_direction': UNAVAILABLE,
            'price_direction': UNAVAILABLE,
        }

    three_hours_ago_ms = latest_data[0] - (1000 * 60 * 60 * 2)
    price = await get_hourly_average(price_key, three_hours_ago_ms)

    # CoinGecko market_chart gives us price history only, so sentiment remains
    # intentionally unavailable in the cached summary shape.
    last_three_hours = [{
        'price': float(data[1]),
        'sentiment': None,
        'time': datetime.fromtimestamp(data[0] / 1000, tz=timezone.utc),
    }
        for data in price]

    return {
        'hourly_average_of_averages': last_three_hours,
        'sentiment_direction': UNAVAILABLE,
        'price_direction': get_direction(last_three_hours, 'price'),
    }


@app.post('/refresh')
async def refresh(background_tasks: BackgroundTasks, keys: Keys = Depends(make_keys)):
    async with httpx.AsyncClient() as client:
        data = await client.get(COINGECKO_MARKET_CHART_URL)
        data.raise_for_status()
    await persist(keys, data.json())
    data = await calculate_three_hours_of_data(keys)
    background_tasks.add_task(set_cache, data, keys)
    return data


@app.get('/is-bitcoin-lit')
async def bitcoin(background_tasks: BackgroundTasks, keys: Keys = Depends(make_keys)):
    data = await get_cache(keys)

    if not data:
        data = await calculate_three_hours_of_data(keys)
        background_tasks.add_task(set_cache, data, keys)

    return data


async def make_timeseries(key):
    """
    Create a timeseries with the Redis key `key`.

    We'll use the duplicate policy known as "first," which ignores
    duplicate pairs of timestamp and values if we add them.

    Because of this, we don't worry about handling this logic
    ourselves -- but note that there is a performance cost to writes
    using this policy.
    """
    try:
        await redis.execute_command(
            'TS.CREATE', key,
            'DUPLICATE_POLICY', 'first',
        )
    except ResponseError as e:
        # Time series probably already exists
        log.info('Could not create timeseries %s, error: %s', key, e)


async def initialize_redis(keys: Keys):
    await make_timeseries(keys.timeseries_sentiment_key())
    await make_timeseries(keys.timeseries_price_key())


@app.on_event('startup')
async def startup_event():
    keys = Keys()
    await initialize_redis(keys)
