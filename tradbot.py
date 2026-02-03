import os
import asyncio
from functools import partial
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

PAIR_MAP = {
    # Forex
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USDCHF": "USDCHF",
    "NZDUSD": "NZDUSD",

    # Crypto
    "BTCUSD": "BTC/USD",

    # Gold
    "XAUUSD": "XAU/USD",
}

TIMEFRAMES = {
    "M30": "30min",
    "H1": "60min",
    "H4": "240min",
}

# =========================
# DATA FETCH
# =========================
def fetch_alpha(symbol: str, interval: str):
    """
    Fetch intraday data from Alpha Vantage.
    Returns latest close price.
    """
    if symbol in ["BTC/USD", "XAU/USD"]:
        # DIGITAL_CURRENCY_INTRADAY
        url = f"https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol={symbol.split('/')[0]}&market=USD&interval={interval}&apikey={ALPHA_KEY}"
    else:
        # FX_INTRADAY
        url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={interval}&apikey={ALPHA_KEY}"

    try:
        r = requests.get(url)
        data = r.json()
        time_key = [k for k in data.keys() if "Time Series" in k]
        if not time_key:
            return None
        latest = list(data[time_key[0]].values())[0]
        return float(latest["4. close"])
    except Exception as e:
        print(f"Fetch error {symbol} {interval}: {e}")
        return None

# =========================
# SIGNAL GENERATOR
# =========================
def generate_signal(pair: str):
    symbol = PAIR_MAP.get(pair.upper())
    if not symbol:
        return "❌ Unsupported pair."

    prices = {}
    for tf_name, tf in TIMEFRAMES.items():
        price = fetch_alpha(symbol, tf)
        if price is None:
            return f"⚠️ No data available for {pair} ({tf_name})"
        prices[tf_name] = price

    # Simple demo logic: Compare H1 and H4
    bias = "BUY" if prices["H1"] > prices["H4"] else "SELL"
    entry = prices["M30"]
    tp = entry * (1.002 if bias == "BUY" else 0.998)
    sl = entry * (0.998 if bias == "BUY" else 1.002)

    return (
        f"📊 *AMAJAMA Trade Signal*\n\n"
        f"Pair: `{pair}`\n"
        f"Bias: *{bias}*\n"
        f"Entry: `{entry:.4f}`\n"
        f"TP: `{tp:.4f}`\n"
        f"SL: `{sl:.4f}`\n"
        f"Timeframes: M30 | H1 | H4\n"
        f"Strategy: Simple H1/H4 bias\n"
        f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

# =========================
# TELEGRAM HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to AMAJAMA TradBot*\n\n"
        "I provide multi-timeframe trade signals for Forex, BTC, and Gold.\n\n"
        "📈 Example commands:\n"
        "`/signal EURUSD`\n"
        "`/signal BTCUSD`\n"
        "`/signal XAUUSD`",
        parse_mode="Markdown"
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Usage: `/signal EURUSD`", parse_mode="Markdown")
        return

    pair = context.args[0].upper()
    if pair not in PAIR_MAP:
        await update.message.reply_text(
            "❌ Unsupported pair.\nAvailable pairs: " + ", ".join(PAIR_MAP.keys())
        )
        return

    await update.message.reply_text("⏳ Analyzing market… please wait")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, partial(generate_signal, pair))
    await update.message.reply_text(result, parse_mode="Markdown")

# =========================
# MAIN
# =========================
def main():
    if not BOT_TOKEN or not ALPHA_KEY:
        raise RuntimeError("BOT_TOKEN or ALPHA_KEY not set!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    print("🤖 AMAJAMA TradBot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
