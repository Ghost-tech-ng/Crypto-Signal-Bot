import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict

@dataclass
class BacktestResult:
    signal_id: str
    entry_price: float
    exit_price: float
    pnl: float
    outcome: str
    duration: timedelta

class DatabaseManager:
    def __init__(self, db_path: str = "trading_signals.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    rationale TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    timeframe TEXT NOT NULL,
                    risk_reward REAL NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT DEFAULT 'active'
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    outcome TEXT NOT NULL,
                    duration_hours REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (signal_id) REFERENCES signals (id)
                )
            ''')

    def save_signal(self, signal) -> int:
        """Save trading signal to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO signals (pair, direction, entry_price, stop_loss, take_profit,
                                   rationale, timestamp, timeframe, risk_reward, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.pair, signal.direction.value, signal.entry, signal.stop_loss,
                signal.take_profit, signal.rationale, signal.timestamp,
                signal.timeframe, signal.risk_reward, signal.confidence
            ))
            return cursor.lastrowid

    def get_active_signals(self) -> List[Dict]:
        """Get all active signals"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM signals WHERE status = 'active' ORDER BY timestamp DESC
            ''')
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def update_signal_status(self, signal_id: int, status: str):
        """Update signal status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE signals SET status = ? WHERE id = ?
            ''', (status, signal_id))

    def save_backtest_result(self, result: BacktestResult, signal_id: int):
        """Save backtest result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO backtest_results (signal_id, entry_price, exit_price, pnl,
                                            outcome, duration_hours, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, result.entry_price, result.exit_price, result.pnl,
                result.outcome, result.duration.total_seconds() / 3600, datetime.now()
            ))

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_profit,
                    MIN(pnl) as max_loss
                FROM backtest_results
            ''')

            result = cursor.fetchone()
            if result and result[0] > 0:
                return {
                    'total_signals': result[0],
                    'winning_trades': result[1],
                    'win_rate': result[1] / result[0] * 100,
                    'total_pnl': result[2],
                    'avg_pnl': result[3],
                    'max_profit': result[4],
                    'max_loss': result[5]
                }
            return {}