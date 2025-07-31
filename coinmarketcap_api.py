import aiohttp
from datetime import datetime
from typing import List, Dict
import logging
import time
import asyncio

logger = logging.getLogger(__name__)


class CoinMarketCapAPI:
    BASE_URL = "https://pro-api.coinmarketcap.com/v2"

    # Mapping of Binance-style symbols to CoinMarketCap symbols
    SYMBOL_MAP = {
        "BTCUSDT": {
            "symbol": "BTC",
            "convert": "USD"
        },
        "ETHUSDT": {
            "symbol": "ETH",
            "convert": "USD"
        },
        "ADAUSDT": {
            "symbol": "ADA",
            "convert": "USD"
        },
        "DOTUSDT": {
            "symbol": "DOT",
            "convert": "USD"
        }
    }

    def __init__(self):
        self.session = None
        self.api_key = "90c98c72-fcb4-4a44-b5ba-dea47729d744"  # Hardcoded API key
        self.last_request_time = 0
        self.min_request_interval = 6.0  # Increased to 1 call every 6 seconds

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Initialized new aiohttp session")

    async def close_session(self):
        if self.session:
            await self.session.close()
            logger.info("Closed aiohttp session")

    async def get_klines(self,
                         symbol: str,
                         interval: str,
                         limit: int = 200) -> List[Dict]:
        """Get candlestick data from CoinMarketCap"""
        await self.init_session()
        logger.info(
            f"Fetching klines for symbol: {symbol}, interval: {interval}, limit: {limit}"
        )

        if symbol not in self.SYMBOL_MAP:
            logger.error(f"Unsupported symbol: {symbol}")
            return []

        coin_symbol = self.SYMBOL_MAP[symbol]["symbol"]
        convert = self.SYMBOL_MAP[symbol]["convert"]

        # Map Binance intervals to CoinMarketCap intervals
        interval_map = {"5m": "5m", "15m": "15m", "1h": "1h"}
        cmc_interval = interval_map.get(interval, "1h")
        logger.debug(f"Mapped interval {interval} to {cmc_interval}")

        url = f"{self.BASE_URL}/cryptocurrency/ohlcv/historical"
        headers = {"X-CMC_PRO_API_KEY": self.api_key}
        params = {
            "symbol": coin_symbol,
            "convert": convert,
            "interval": cmc_interval,
            "count": limit
        }
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request params: {params}")

        try:
            # Rate limiting: wait if necessary
            current_time = time.time()
            if current_time - self.last_request_time < self.min_request_interval:
                sleep_time = self.min_request_interval - (
                    current_time - self.last_request_time)
                logger.debug(
                    f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
            self.last_request_time = time.time()
            logger.debug(
                f"Request sent at: {datetime.fromtimestamp(self.last_request_time)}"
            )

            async with self.session.get(url, headers=headers,
                                        params=params) as response:
                logger.debug(
                    f"Received response with status: {response.status}")
                full_response = await response.text()
                logger.error(f"Full response: {full_response}"
                             )  # Log full response for debugging
                response.raise_for_status()
                data = await response.json()

                # Extract OHLCV data
                quotes = data["data"][coin_symbol][0]["quotes"]
                klines = []
                for item in quotes[:limit]:
                    quote = item["quote"][convert]
                    klines.append({
                        'timestamp':
                        datetime.fromisoformat(item["timestamp"].rstrip("Z")),
                        'open':
                        float(quote["open"]),
                        'high':
                        float(quote["high"]),
                        'low':
                        float(quote["low"]),
                        'close':
                        float(quote["close"]),
                        'volume':
                        float(quote["volume"])
                    })
                logger.info(
                    f"Successfully fetched {len(klines)} klines for {symbol}")
                return klines
        except aiohttp.ClientResponseError as e:
            logger.error(f"API error: {e.status} - {e.message}")
            full_response = await response.text() if 'response' in locals(
            ) else "No response body"
            logger.error(f"Full response: {full_response}")
            if e.status == 403:
                logger.error(
                    "Possible causes: Exceeded quota, IP not whitelisted, or plan issue"
                )
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching klines: {e}",
                         exc_info=True)
            return []

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
