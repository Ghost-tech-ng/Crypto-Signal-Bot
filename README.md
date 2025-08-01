### 📈 Smart Money Crypto Signal Bot

An advanced Telegram bot for crypto traders that analyzes market structure using **Smart Money Concepts** and delivers **real-time trading signals** via Telegram.

---

### 🚀 Features

* ✅ **Smart Money Concepts (SMC) Analysis**
* 🔍 Detects:

  * Break of Structure (BOS)
  * Change of Character (CHoCH)
  * Order Blocks (OB)
  * Fair Value Gaps (FVG)
  * Liquidity Sweeps
* 🧠 Configurable **risk/reward**, timeframes, pairs, and thresholds
* 💬 Sends signals to Telegram with full rationale, SL/TP, and confidence scores
* 💾 Backtests & saves signals and results to SQLite database
* 📊 Performance analytics (Win rate, PnL, best/worst trades)
* 🟢 Runs continuously with a web keep-alive (Replit compatible)

---

### 📂 Project Structure

```
🔹 main.py                # Bot entry point
🔹 smart_money.py         # Market structure and SMC logic
🔹 coinmarketcap_api.py   # Fetches OHLCV data from CoinMarketCap
🔹 database.py            # Stores signals and backtest results in SQLite
🔹 config.json            # Configuration file
🔹 keep_alive.py          # Web server to keep bot alive (Replit support)
🔹 requirements.txt       # Python dependencies
```

---

### ⚙️ Installation

#### 1. Clone the Repo

```bash
git clone https://github.com/yourusername/smc-telegram-bot.git
cd smc-telegram-bot
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Set Environment Variables

Set your Telegram bot token:

```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
```

#### 4. Configure Settings

Edit `config.json`:

```json
{
  "min_risk_reward": 4.0,
  "max_risk_percent": 0.02,
  "monitored_pairs": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"],
  "timeframes": ["5m", "15m", "1h"],
  "confidence_threshold": 0.7,
  "signal_check_interval": 30,
  "klines_limit": 200,
  "swing_window": 5,
  "order_block_lookback": 20,
  "max_order_blocks": 50,
  "max_fair_value_gaps": 50,
  "max_swing_points": 20,
  "liquidity_sweep_buffer": 0.002
}
```

#### 5. Run the Bot

```bash
python main.py
```

---

### 🤖 Telegram Commands

* `/start` – Help & features
* `/monitor` – Start monitoring for signals
* `/stop` – Stop monitoring
* `/stats` – View performance report
* `/signals` – View active signals

---

### 📊 Example Signal Output

```
🚨 PREMIUM SIGNAL 🚨

Signal #12
📈 LONG ETHUSDT @ 1840.23
🛏 SL = 1825.00 (below OB)
🎯 TP = 1900.00 (4.0× risk)
⏰ Timeframe: 15m
🔍 Rationale: Break of structure confirmed with order block + FVG
📊 Confidence: 85%

Risk Management: Position size ≤ 2% of account
Trailing stop enabled
```

---

### 🧰 Backtesting & Performance

Backtest results and performance stats are saved to `trading_signals.db`. Includes:

* Win rate
* Total and average PnL
* Max profit / loss trades

---

### 🔐 API Key

The CoinMarketCap API key is hardcoded in `coinmarketcap_api.py`. Replace it with your own or load it securely from `.env`.

```python
self.api_key = "your-cmc-api-key"
```

---

### ✅ Requirements

See [`requirements.txt`](./requirements.txt):

* `pandas`, `numpy`, `python-telegram-bot`, `aiohttp`, `flask`, `ta`, `telegram`

---

### 📌 Notes

* Built for Replit (or other always-on hosting) with `keep_alive.py`
* Built-in rate-limiting and error handling
* Easy to extend with more SMC or technical indicators

---

### 📃 License

MIT License. Free to use, modify, and distribute.
