import os
import requests
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =====================
# LOAD ENV
# =====================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

if not BOT_TOKEN or not ALPHA_KEY:
    raise RuntimeError("BOT_TOKEN or ALPHA_KEY not set!")

# =====================
# PAIRS
# =====================
PAIRS = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "XAUUSD": ("XAU", "USD"),
    "BTCUSD": ("BTC", "USD"),
}

TIMEFRAMES = {
    "M30": "30min",
    "H1": "60min",
    "H4": "240min",
}

# =====================
# DATA
# =====================
def fetch_fx(frm, to, interval):
    url = (
        "https://www.alphavantage.co/query"
        f"?function=FX_INTRADAY"
        f"&from_symbol={frm}"
        f"&to_symbol={to}"
        f"&interval={interval}"
        f"&apikey={ALPHA_KEY}"
    )
    r = requests.get(url, timeout=15).json()
    key = next((k for k in r if "Time Series" in k), None)
    if not key:
        return None
    return float(list(r[key].values())[0]["4. close"])


def fetch_crypto(symbol, market, interval):
    url = (
        "https://www.alphavantage.co/query"
        f"?function=CRYPTO_INTRADAY"
        f"&symbol={symbol}"
        f"&market={market}"
        f"&interval={interval}"
        f"&apikey={ALPHA_KEY}"
    )
    r = requests.get(url, timeout=15).json()
    key = next((k for k in r if "Time Series" in k), None)
    if not key:
        return None
    return float(list(r[key].values())[0]["4. close"])


def build_signal(pair):
    base, quote = PAIRS[pair]
    prices = {}

    for tf, interval in TIMEFRAMES.items():
        if pair == "BTCUSD":
            price = fetch_crypto(base, quote, interval)
        else:
            price = fetch_fx(base, quote, interval)

        if price is None:
            return "⚠️ No data available right now (API limit or market closed)."

        prices[tf] = price

    bias = "BUY" if prices["H1"] > prices["H4"] else "SELL"
    entry = prices["M30"]
    tp = entry * (1.003 if bias == "BUY" else 0.997)
    sl = entry * (0.997 if bias == "BUY" else 1.003)

    return (
        "📊 *AMAJAMA Trade Signal*\n\n"
        f"Pair: `{pair}`\n"
        f"Direction: *{bias}*\n\n"
        f"Entry: `{entry:.4f}`\n"
        f"TP: `{tp:.4f}`\n"
        f"SL: `{sl:.4f}`\n\n"
        f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

# =====================
# COMMANDS
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *AMAJAMA TradBot*\n\n"
        "Use:\n"
        "`/signal EURUSD`\n"
        "`/signal XAUUSD`\n"
        "`/signal BTCUSD`",
        parse_mode="Markdown",
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /signal EURUSD")
        return

    pair = context.args[0].upper()
    if pair not in PAIRS:
        await update.message.reply_text("❌ Unsupported pair.")
        return

    await update.message.reply_text("⏳ Analyzing market...")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, build_signal, pair)

    await update.message.reply_text(result, parse_mode="Markdown")

# =====================
# MAIN
# =====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
