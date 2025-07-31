import aiohttp
from datetime import datetime
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)


class CoinGeckoAPI:
    BASE_URL = "https://api.coingecko.com/api/v3"

    # Mapping of Binance-style symbols to CoinGecko coin IDs and vs_currency
    SYMBOL_MAP = {
        "BTCUSDT": {
            "coin_id": "bitcoin",
            "vs_currency": "usd"
        },
        "ETHUSDT": {
            "coin_id": "ethereum",
            "vs_currency": "usd"
        },
        "ADAUSDT": {
            "coin_id": "cardano",
            "vs_currency": "usd"
        },
        "DOTUSDT": {
            "coin_id": "polkadot",
            "vs_currency": "usd"
        }
    }

    def __init__(self):
        self.session = None
        self.last_request_time = 0
        self.min_request_interval = 1.2  # Ensure < 50 calls per minute

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def get_klines(self,
                         symbol: str,
                         interval: str,
                         limit: int = 200) -> List[Dict]:
        """Get candlestick data from CoinGecko"""
        await self.init_session()

        if symbol not in self.SYMBOL_MAP:
            logger.error(f"Unsupported symbol: {symbol}")
            return []

        coin_id = self.SYMBOL_MAP[symbol]["coin_id"]
        vs_currency = self.SYMBOL_MAP[symbol]["vs_currency"]

        # Map Binance intervals to CoinGecko days
        interval_map = {
            "5m": 1,  # Use 1 day of data and slice for minute-level
            "15m": 1,
            "1h": 1
        }
        days = interval_map.get(interval, 1)

        url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
        params = {"vs_currency": vs_currency, "days": days, "precision": 8}

        try:
            # Rate limiting: wait if necessary
            current_time = time.time()
            if current_time - self.last_request_time < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval -
                                    (current_time - self.last_request_time))
            self.last_request_time = time.time()

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                klines = []
                for item in data[:limit]:  # Slice to respect limit
                    klines.append({
                        'timestamp':
                        datetime.fromtimestamp(item[0] / 1000),
                        'open':
                        float(item[1]),
                        'high':
                        float(item[2]),
                        'low':
                        float(item[3]),
                        'close':
                        float(item[4]),
                        'volume':
                        0.0  # CoinGecko OHLC doesn't include volume
                    })

                return klines
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return []
