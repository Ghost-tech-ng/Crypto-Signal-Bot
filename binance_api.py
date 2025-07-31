import aiohttp
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class BinanceAPI:
    BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self):
        self.session = None

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
        """Get candlestick data from Binance"""
        await self.init_session()

        url = f"{self.BASE_URL}/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                klines = []
                for item in data:
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
                        float(item[5])
                    })

                return klines
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return []
