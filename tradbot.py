import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging
from datetime import datetime, time, timezone

# -----------------------
# Config
# -----------------------
BOT_TOKEN = "8594787038:AAF9Hg0F7Z3IdZrhn1tIRSKdl2xZyJH-YZg"

# Forex, Crypto, Metal pairs
PAIRS = [
    "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X",  # Forex
    "BTC-USD",  # Crypto
    "XAUUSD=X"      # Gold / Metal
]

EMA_FAST = 50
EMA_SLOW = 200

# Interval for automatic updates (seconds)
AUTO_UPDATE_INTERVAL = 3600  # 1 hour

# Default Buy/Sell limit adjustment percentage
BUY_LIMIT_PERCENT = 0.5   # 0.5% below price for buy
SELL_LIMIT_PERCENT = 0.5  # 0.5% above price for sell

# Optional per-pair limits (overrides defaults if specified)
LIMITS = {
    "EURUSD=X": {"buy": 0.3, "sell": 0.3},
    "USDJPY=X": {"buy": 0.3, "sell": 0.3},
    "GBPUSD=X": {"buy": 0.3, "sell": 0.3},
    "AUDUSD=X": {"buy": 0.3, "sell": 0.3},
    "USDCAD=X": {"buy": 0.3, "sell": 0.3},
    "USDCHF=X": {"buy": 0.3, "sell": 0.3},
    "BTC-USD": {"buy": 0.5, "sell": 0.5},
    "GC=F": {"buy": 0.5, "sell": 0.5},
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------
# EMA trend analysis
# -----------------------
def analyze_trend(symbol, interval="1h"):
    try:
        df = yf.Ticker(symbol).history(period="7d", interval=interval)
        if len(df) < EMA_SLOW:
            return "HOLD", None, None

        df["EMA_FAST"] = df["Close"].ewm(span=EMA_FAST, adjust=False).mean()
        df["EMA_SLOW"] = df["Close"].ewm(span=EMA_SLOW, adjust=False).mean()

        last_fast = df["EMA_FAST"].iloc[-1]
        last_slow = df["EMA_SLOW"].iloc[-1]

        last_price = df["Close"].iloc[-1]
        TP = round(last_price * 1.02, 5)
        SL = round(last_price * 0.98, 5)

        if last_fast > last_slow:
            return "BUY", TP, SL
        elif last_fast < last_slow:
            return "SELL", TP, SL
        else:
            return "HOLD", TP, SL
    except Exception as e:
        print(f"Error analyzing {symbol} {interval}: {e}")
        return "HOLD", None, None

# -----------------------
# Check if it's market hours
# -----------------------
def in_market_hours(symbol):
    now_utc = datetime.now(timezone.utc)
    weekday = now_utc.weekday()  # Mon=0, Sun=6
    current_time = now_utc.time()

    if symbol == "BTC-USD":
        return True  # Crypto 24/7
    elif symbol == "GC=F" or symbol.endswith("=X"):  # Forex / Gold
        if 0 <= weekday <= 4:
            return time(6,0) <= current_time <= time(22,0)
    return False

# -----------------------
# /price command
# -----------------------
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /price SYMBOL\nExample: /price BTC-USD")
        return

    symbol = context.args[0].upper()
    if symbol not in PAIRS:
        await update.message.reply_text(f"{symbol} is not a supported pair.")
        return

    try:
        data = yf.Ticker(symbol)
        last_price = data.history(period="1d")['Close'][-1]
        await update.message.reply_text(f"{symbol} price: ${last_price:.5f}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching {symbol}: {e}")

# -----------------------
# Generate signal message
# -----------------------
def generate_signal_message(symbol):
    if not in_market_hours(symbol):
        return None

    signals = []
    for interval in ["30m", "60m", "4h"]:
        sig, TP, SL = analyze_trend(symbol, interval)
        signals.append(sig)

    buy_count = signals.count("BUY")
    sell_count = signals.count("SELL")

    if buy_count == 3:
        overall = "STRONG BUY"
        emoji = "📈"
    elif sell_count == 3:
        overall = "STRONG SELL"
        emoji = "📉"
    elif buy_count >= 2:
        overall = "BUY"
        emoji = "⬆️"
    elif sell_count >= 2:
        overall = "SELL"
        emoji = "⬇️"
    else:
        overall = "HOLD"
        emoji = "⚪"

    last_price = yf.Ticker(symbol).history(period="1d")['Close'][-1]

    # Determine limits
    buy_pct = LIMITS.get(symbol, {}).get("buy", BUY_LIMIT_PERCENT)
    sell_pct = LIMITS.get(symbol, {}).get("sell", SELL_LIMIT_PERCENT)

    if overall in ["BUY", "STRONG BUY"]:
        limit = round(last_price * (1 - buy_pct / 100), 5)
    elif overall in ["SELL", "STRONG SELL"]:
        limit = round(last_price * (1 + sell_pct / 100), 5)
    else:
        limit = None

    final_msg = (
        f"🔹 {symbol}:\n"
        f"Overall: {emoji} {overall}\n"
        f"TP: {round(last_price*1.02,5)} | SL: {round(last_price*0.98,5)}"
    )
    if limit:
        final_msg += f" | Suggested Limit: {limit}"

    return final_msg

# -----------------------
# /signal command
# -----------------------
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    messages = []
    for symbol in PAIRS:
        msg = generate_signal_message(symbol)
        if msg:
            messages.append(msg)

    if messages:
        await update.message.reply_text("\n\n".join(messages))
    else:
        await update.message.reply_text("No signals available outside market hours.")

# -----------------------
# Periodic automatic signals
# -----------------------
async def periodic_signal(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    messages = []
    for symbol in PAIRS:
        msg = generate_signal_message(symbol)
        if msg:
            messages.append(msg)

    if messages:
        await context.bot.send_message(chat_id=chat_id, text="\n\n".join(messages))

# -----------------------
# /start command
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = (
        "Hi! I’m AMAJAMA TradBot 🤖\n\n"
        "I can help you:\n"
        "- Check latest prices for Forex, BTC (Crypto), and Gold\n"
        "- Suggest trades based on M30, H1, H4 EMA trends\n"
        "- Advise Buy/Sell limits with configurable percentages\n"
        "- Suggest TP and SL levels\n"
        "- Send automatic trade updates during market hours\n\n"
        "Use /help to see all commands."
    )
    await update.message.reply_text(intro)

    # Schedule periodic updates every AUTO_UPDATE_INTERVAL seconds
    context.job_queue.run_repeating(
        periodic_signal,
        interval=AUTO_UPDATE_INTERVAL,
        first=10,
        chat_id=update.effective_chat.id
    )

# -----------------------
# /help command
# -----------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "AMAJAMA TradBot Commands 📜\n\n"
        "/start - Introduce the bot and schedule automatic updates\n"
        "/price SYMBOL - Get the latest price for a supported pair\n"
        "/signal - Get trade recommendations based on EMA trends\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

# -----------------------
# Main
# -----------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))

    print("AMAJAMA TradBot is running...")
    app.run_polling()

# -----------------------
if __name__ == "__main__":
    main()