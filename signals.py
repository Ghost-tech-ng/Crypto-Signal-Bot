from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import pandas as pd
from typing import Optional, List, Dict
from smart_money import SmartMoneyAnalyzer, Direction, OrderBlock, FairValueGap


@dataclass
class TradingSignal:
    pair: str
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    rationale: str
    timestamp: datetime
    timeframe: str
    risk_reward: float
    confidence: float


class SignalGenerator:

    def __init__(self, config: dict):
        self.analyzer = SmartMoneyAnalyzer(config)
        self.min_risk_reward = config["min_risk_reward"]
        self.max_risk_percent = config["max_risk_percent"]
        self.confidence_threshold = config["confidence_threshold"]

    def generate_signal(self, df: pd.DataFrame, pair: str,
                        timeframe: str) -> Optional[TradingSignal]:
        """Generate trading signal based on Smart Money Concepts"""
        market_structure = self.analyzer.analyze_market_structure(df)
        order_blocks = self.analyzer.find_order_blocks(df)
        fvgs = self.analyzer.find_fair_value_gaps(df)
        liquidity_sweep = self.analyzer.detect_liquidity_sweep(df)

        signal = self._check_confluence(df, pair, timeframe, market_structure,
                                        order_blocks, fvgs, liquidity_sweep)

        return signal

    def _check_confluence(self, df: pd.DataFrame, pair: str, timeframe: str,
                          market_structure: Dict,
                          order_blocks: List[OrderBlock],
                          fvgs: List[FairValueGap],
                          liquidity_sweep: Dict) -> Optional[TradingSignal]:
        """Check for confluence of signals"""
        current_price = df.iloc[-1]['close']
        bos = market_structure.get('bos')

        if not bos:
            return None

        relevant_ob = None
        for ob in reversed(order_blocks):
            if ob.direction == bos['direction'] and not ob.tested:
                if bos['direction'] == Direction.LONG:
                    if ob.low <= current_price <= ob.high:
                        relevant_ob = ob
                        break
                else:
                    if ob.low <= current_price <= ob.high:
                        relevant_ob = ob
                        break

        if not relevant_ob:
            return None

        unfilled_fvg = None
        for fvg in reversed(fvgs):
            if (fvg.direction == bos['direction'] and not fvg.filled
                    and fvg.low >= relevant_ob.low
                    and fvg.high <= relevant_ob.high):
                unfilled_fvg = fvg
                break

        if not unfilled_fvg:
            return None

        if not liquidity_sweep or liquidity_sweep.get(
                'direction') != bos['direction']:
            return None

        entry_price = current_price

        if bos['direction'] == Direction.LONG:
            stop_loss = relevant_ob.low * 0.999
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.min_risk_reward)
        else:
            stop_loss = relevant_ob.high * 1.001
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.min_risk_reward)

        risk_reward = abs(take_profit - entry_price) / abs(entry_price -
                                                           stop_loss)

        if risk_reward < self.min_risk_reward:
            return None

        confidence = self._calculate_confidence(bos, relevant_ob, unfilled_fvg,
                                                liquidity_sweep)

        if confidence < self.confidence_threshold:
            return None

        rationale = f"BOS + OB + FVG + liquidity sweep @ {timeframe}"

        return TradingSignal(pair=pair,
                             direction=bos['direction'],
                             entry=entry_price,
                             stop_loss=stop_loss,
                             take_profit=take_profit,
                             rationale=rationale,
                             timestamp=datetime.now(),
                             timeframe=timeframe,
                             risk_reward=risk_reward,
                             confidence=confidence)

    def _calculate_confidence(self, bos: Dict, ob: OrderBlock,
                              fvg: FairValueGap,
                              liquidity_sweep: Dict) -> float:
        """Calculate signal confidence based on confluence factors"""
        confidence = 0.0
        confidence += min(bos['strength'], 0.3)
        confidence += min(ob.strength, 0.3)
        confidence += 0.2
        confidence += 0.2
        return confidence
