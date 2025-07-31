from collections import deque
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class OrderBlock:
    high: float
    low: float
    timestamp: datetime
    direction: Direction
    strength: float
    tested: bool = False


@dataclass
class FairValueGap:
    high: float
    low: float
    timestamp: datetime
    direction: Direction
    filled: bool = False


class SmartMoneyAnalyzer:

    def __init__(self, config: dict):
        self.config = config
        self.order_blocks = deque(maxlen=config["max_order_blocks"])
        self.fair_value_gaps = deque(maxlen=config["max_fair_value_gaps"])
        self.swing_highs = deque(maxlen=config["max_swing_points"])
        self.swing_lows = deque(maxlen=config["max_swing_points"])
        self.last_bos = None
        self.market_structure = "ranging"

    def analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """Analyze market structure for BOS and CHoCH"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        swing_highs = self._find_swing_highs(highs)
        swing_lows = self._find_swing_lows(lows)

        bos_signal = self._detect_bos(swing_highs, swing_lows, closes[-1])
        choch_signal = self._detect_choch(swing_highs, swing_lows)

        return {
            'bos': bos_signal,
            'choch': choch_signal,
            'trend': self._determine_trend(swing_highs, swing_lows)
        }

    def _find_swing_highs(self, highs: np.array) -> List[Tuple[int, float]]:
        """Find swing highs using local maxima"""
        window = self.config["swing_window"]
        swing_highs = []
        for i in range(window, len(highs) - window):
            if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                swing_highs.append((i, highs[i]))
        return swing_highs

    def _find_swing_lows(self, lows: np.array) -> List[Tuple[int, float]]:
        """Find swing lows using local minima"""
        window = self.config["swing_window"]
        swing_lows = []
        for i in range(window, len(lows) - window):
            if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                swing_lows.append((i, lows[i]))
        return swing_lows

    def _detect_bos(self, swing_highs: List, swing_lows: List,
                    current_price: float) -> Optional[Dict]:
        """Detect Break of Structure"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None

        recent_high = max(swing_highs[-2:], key=lambda x: x[1])
        if current_price > recent_high[1] * (
                1 + self.config["liquidity_sweep_buffer"]):
            return {
                'direction': Direction.LONG,
                'level': recent_high[1],
                'strength': (current_price - recent_high[1]) / recent_high[1]
            }

        recent_low = min(swing_lows[-2:], key=lambda x: x[1])
        if current_price < recent_low[1] * (
                1 - self.config["liquidity_sweep_buffer"]):
            return {
                'direction': Direction.SHORT,
                'level': recent_low[1],
                'strength': (recent_low[1] - current_price) / recent_low[1]
            }

        return None

    def _detect_choch(self, swing_highs: List,
                      swing_lows: List) -> Optional[Dict]:
        """Detect Change of Character"""
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None

        recent_highs = [h[1] for h in swing_highs[-3:]]
        recent_lows = [l[1] for l in swing_lows[-3:]]

        if recent_highs[0] > recent_highs[1] and recent_highs[
                2] > recent_highs[1]:
            return {'direction': Direction.LONG, 'strength': 0.7}

        if recent_lows[0] < recent_lows[1] and recent_lows[2] < recent_lows[1]:
            return {'direction': Direction.SHORT, 'strength': 0.7}

        return None

    def _determine_trend(self, swing_highs: List, swing_lows: List) -> str:
        """Determine overall market trend"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "ranging"

        recent_highs = [h[1] for h in swing_highs[-2:]]
        recent_lows = [l[1] for l in swing_lows[-2:]]

        higher_highs = recent_highs[-1] > recent_highs[-2]
        higher_lows = recent_lows[-1] > recent_lows[-2]

        if higher_highs and higher_lows:
            return "bullish"
        elif not higher_highs and not higher_lows:
            return "bearish"
        else:
            return "ranging"

    def find_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """Identify order blocks based on price action"""
        order_blocks = []
        lookback = self.config["order_block_lookback"]

        for i in range(lookback, len(df) - 5):
            candle = df.iloc[i]

            if (candle['close'] < candle['open']
                    and df.iloc[i + 1]['close'] > df.iloc[i + 1]['open']
                    and df.iloc[i + 2]['close'] > candle['high']):

                ob = OrderBlock(
                    high=candle['high'],
                    low=candle['low'],
                    timestamp=candle['timestamp'],
                    direction=Direction.LONG,
                    strength=abs(candle['close'] - candle['open']) /
                    candle['open'])
                order_blocks.append(ob)

            elif (candle['close'] > candle['open']
                  and df.iloc[i + 1]['close'] < df.iloc[i + 1]['open']
                  and df.iloc[i + 2]['close'] < candle['low']):

                ob = OrderBlock(
                    high=candle['high'],
                    low=candle['low'],
                    timestamp=candle['timestamp'],
                    direction=Direction.SHORT,
                    strength=abs(candle['close'] - candle['open']) /
                    candle['open'])
                order_blocks.append(ob)

        return order_blocks

    def find_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        """Identify Fair Value Gaps (FVG)"""
        fvgs = []

        for i in range(1, len(df) - 1):
            prev_candle = df.iloc[i - 1]
            current_candle = df.iloc[i]
            next_candle = df.iloc[i + 1]

            if (prev_candle['high'] < next_candle['low']
                    and current_candle['close'] > current_candle['open']):

                fvg = FairValueGap(high=next_candle['low'],
                                   low=prev_candle['high'],
                                   timestamp=current_candle['timestamp'],
                                   direction=Direction.LONG)
                fvgs.append(fvg)

            elif (prev_candle['low'] > next_candle['high']
                  and current_candle['close'] < current_candle['open']):

                fvg = FairValueGap(high=prev_candle['low'],
                                   low=next_candle['high'],
                                   timestamp=current_candle['timestamp'],
                                   direction=Direction.SHORT)
                fvgs.append(fvg)

        return fvgs

    def detect_liquidity_sweep(self, df: pd.DataFrame) -> Dict:
        """Detect liquidity sweeps at key levels"""
        if len(df) < 20:
            return {}

        current_price = df.iloc[-1]['close']
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()

        if current_price > recent_high * (
                1 + self.config["liquidity_sweep_buffer"]):
            return {
                'type': 'high_sweep',
                'level': recent_high,
                'direction': Direction.SHORT
            }

        if current_price < recent_low * (
                1 - self.config["liquidity_sweep_buffer"]):
            return {
                'type': 'low_sweep',
                'level': recent_low,
                'direction': Direction.LONG
            }

        return {}
