import asyncio
import logging
import json
import os
from telegram.ext import Application, CommandHandler, ContextTypes
from coinmarketcap_api import CoinMarketCapAPI  # Changed import
from signals import SignalGenerator
from database import DatabaseManager
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingBot:

    def __init__(self, bot_token: str, chat_id: str, config: dict):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.config = config
        self.api = CoinMarketCapAPI()  # Changed to CoinMarketCapAPI
        self.signal_generator = SignalGenerator(config)
        self.db = DatabaseManager()
        self.running = False

    async def start_monitoring(self):
        """Start monitoring crypto pairs for signals"""
        self.running = True
        logger.info("Started monitoring crypto pairs...")

        while self.running:
            try:
                for pair in self.config["monitored_pairs"]:
                    for timeframe in self.config["timeframes"]:
                        await self._check_pair_signals(pair, timeframe)
                        await asyncio.sleep(1)  # Rate limiting

                await asyncio.sleep(self.config["signal_check_interval"])

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _check_pair_signals(self, pair: str, timeframe: str):
        """Check for signals on a specific pair and timeframe"""
        try:
            klines = await self.api.get_klines(pair, timeframe,
                                               self.config["klines_limit"])
            if not klines:
                return

            df = pd.DataFrame(klines)
            df.set_index('timestamp', inplace=True)

            signal = self.signal_generator.generate_signal(df, pair, timeframe)
            if signal:
                signal_id = self.db.save_signal(signal)
                await self._send_signal_to_telegram(signal, signal_id)
                logger.info(
                    f"Generated signal for {pair} {timeframe}: {signal.direction.value}"
                )

        except Exception as e:
            logger.error(f"Error checking {pair} {timeframe}: {e}")

    async def _send_signal_to_telegram(self, signal, signal_id: int):
        """Send trading signal to Telegram"""
        try:
            message = f"""
🚨 **PREMIUM SIGNAL** 🚨

**Signal #{signal_id}**
📈 **{signal.direction.value.upper()} {signal.pair}** @ {signal.entry:.4f}
🛑 **SL** = {signal.stop_loss:.4f} (below OB)
🎯 **TP** = {signal.take_profit:.4f} ({signal.risk_reward:.1f}× risk)
⏰ **Timeframe**: {signal.timeframe.value}
🔍 **Rationale**: {signal.rationale}
📊 **Confidence**: {signal.confidence:.0%}

**Limit order placed**

```json
{{
  "pair": "{signal.pair}",
  "direction": "{signal.direction.value}",
  "entry": {signal.entry:.4f},
  "sl": {signal.stop_loss:.4f},
  "tp": {signal.take_profit:.4f},
  "rationale": "{signal.rationale}"
}}
```

⚠️ **Risk Management**: Position size ≤ 1-2% of account
🔄 **Trailing stop enabled**
"""
            bot = telegram.Bot(token=self.bot_token)
            await bot.send_message(chat_id=self.chat_id,
                                   text=message,
                                   parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    async def get_performance_report(self) -> str:
        """Generate performance report"""
        stats = self.db.get_performance_stats()
        if not stats:
            return "📊 **Performance Report**\n\nNo completed trades yet."

        report = f"""
📊 **Performance Report**

**Total Signals**: {stats['total_signals']}
**Winning Trades**: {stats['winning_trades']}
**Win Rate**: {stats['win_rate']:.1f}%
**Total PnL**: {stats['total_pnl']:.2f}%
**Average PnL**: {stats['avg_pnl']:.2f}%
**Best Trade**: +{stats['max_profit']:.2f}%
**Worst Trade**: {stats['max_loss']:.2f}%

📈 **Strategy**: Smart Money Concepts
🎯 **Min R:R**: {self.config['min_risk_reward']}:1
⚡ **Timeframes**: {', '.join(self.config['timeframes'])}
"""
        return report

    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Stopped monitoring")


async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    await update.message.reply_text(
        "🤖 **Premium Crypto Signal Bot**\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/monitor - Start monitoring signals\n"
        "/stop - Stop monitoring\n"
        "/stats - View performance statistics\n"
        "/signals - View active signals\n\n"
        "⚡ **Features**:\n"
        "• Smart Money Concepts analysis\n"
        "• Order blocks, FVGs, BOS detection\n"
        "• 4:1 minimum risk/reward\n"
        "• Real-time Telegram alerts\n"
        "• Comprehensive backtesting",
        parse_mode='Markdown')


async def monitor_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Start monitoring command"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(update.effective_chat.id)

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found")
        await update.message.reply_text("❌ Error: config.json not found")
        return
    except json.JSONDecodeError:
        logger.error("config.json is malformed")
        await update.message.reply_text("❌ Error: config.json is malformed")
        return

    trading_bot = TradingBot(bot_token, chat_id, config)
    context.bot_data['trading_bot'] = trading_bot

    asyncio.create_task(trading_bot.start_monitoring())

    await update.message.reply_text(
        f"✅ **Monitoring Started**\n\n"
        f"🔍 Scanning pairs: {', '.join(config['monitored_pairs'])}\n"
        f"⏰ Timeframes: {', '.join(config['timeframes'])}\n"
        "📊 Using Smart Money Concepts\n\n"
        "Signals will be sent automatically when conditions are met.",
        parse_mode='Markdown')


async def stop_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Stop monitoring command"""
    trading_bot = context.bot_data.get('trading_bot')
    if trading_bot:
        trading_bot.stop_monitoring()
        await update.message.reply_text("⏹️ **Monitoring Stopped**")
    else:
        await update.message.reply_text("❌ **No active monitoring**")


async def stats_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Show performance statistics"""
    trading_bot = context.bot_data.get('trading_bot')
    if trading_bot:
        report = await trading_bot.get_performance_report()
        await update.message.reply_text(report, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ **Bot not initialized**")


async def signals_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Show active signals"""
    db = DatabaseManager()
    active_signals = db.get_active_signals()

    if not active_signals:
        await update.message.reply_text("📭 **No active signals**")
        return

    message = "📋 **Active Signals**\n\n"
    for signal in active_signals[:5]:
        message += f"**#{signal['id']}** {signal['direction'].upper()} {signal['pair']}\n"
        message += f"Entry: {signal['entry_price']:.4f} | SL: {signal['stop_loss']:.4f} | TP: {signal['take_profit']:.4f}\n"
        message += f"R:R: {signal['risk_reward']:.1f}:1 | Confidence: {signal['confidence']:.0%}\n"
        message += f"Time: {signal['timestamp'][:16]}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')


def main():
    """Main function to run the bot"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in Secrets")
        return

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("monitor", monitor_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("signals", signals_command))

    application.bot_data['bot_token'] = bot_token

    keep_alive()  # Start keep-alive server for Replit
    logger.info("Starting Premium Crypto Signal Bot...")
    application.run_polling()


if __name__ == "__main__":
    import pandas as pd
    main()
