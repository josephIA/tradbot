import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALPHA_KEY = os.getenv("ALPHA_KEY")

PAIRS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "USDCHF": "USD/CHF",
    "XAUUSD": "XAU/USD",
    "BTCUSD": "BTC/USD",
}

def get_price(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=CURRENCY_EXCHANGE_RATE"
        f"&from_currency={symbol[:3]}"
        f"&to_currency={symbol[3:]}"
        f"&apikey={ALPHA_KEY}"
    )
    r = requests.get(url, timeout=15).json()
    return r.get("Realtime Currency Exchange Rate", {}).get("5. Exchange Rate")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pairs_list = "\n".join(f"• {v}" for v in PAIRS.values())
    await update.message.reply_text(
        "🤖 *AMAJAMA TradBot*\n\n"
        "I provide trading guidance using M30, H1 & H4.\n\n"
        "*Available pairs:*\n"
        f"{pairs_list}\n\n"
        "Use:\n"
        "`/signal EURUSD`\n"
        "`/price XAUUSD`",
        parse_mode="Markdown"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price EURUSD")
        return

    pair = context.args[0].upper()
    if pair not in PAIRS:
        await update.message.reply_text("Pair not supported.")
        return

    price = get_price(pair)
    if not price:
        await update.message.reply_text("No data available (API limit).")
        return

    await update.message.reply_text(
        f"💰 *{PAIRS[pair]}*\nPrice: `{price}`",
        parse_mode="Markdown"
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /signal EURUSD")
        return

    pair = context.args[0].upper()
    if pair not in PAIRS:
        await update.message.reply_text("Pair not supported.")
        return

    await update.message.reply_text(
        f"📊 *{PAIRS[pair]} Trade Idea*\n\n"
        "Bias: BUY (H4 trend)\n"
        "Entry: Buy Limit near support\n"
        "TP: 1.5RR\n"
        "SL: Below structure\n\n"
        "_Educational purpose only_",
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN or not ALPHA_KEY:
        raise RuntimeError("BOT_TOKEN or ALPHA_KEY not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))
    app.run_polling()

if __name__ == "__main__":
    main()
