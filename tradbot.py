import os
import logging
from dotenv import load_dotenv

import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is running!\n"
        "Try:\n"
        "/price BTC-USD"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price BTC-USD")
        return

    symbol = context.args[0].upper()

    try:
        data = yf.Ticker(symbol).history(period="1d")
        if data.empty:
            await update.message.reply_text("Symbol not found")
            return

        price_now = round(data["Close"].iloc[-1], 4)
        await update.message.reply_text(
            f"{symbol} price: {price_now}"
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error fetching price")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.run_polling()

if __name__ == "__main__":
    main()