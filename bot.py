import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json

print("🔵 Starting bot.py...")

load_dotenv()

# Check Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_JSON = os.getenv("GOOGLE_JSON")

if BOT_TOKEN is None:
    print("❌ BOT_TOKEN is not set.")
else:
    print("✅ BOT_TOKEN loaded.")

if GOOGLE_JSON is None:
    print("❌ GOOGLE_JSON is not set.")
else:
    print("✅ GOOGLE_JSON loaded, trying to parse...")

try:
    creds_dict = json.loads(GOOGLE_JSON)
    print("✅ GOOGLE_JSON parsed successfully.")
except Exception as e:
    print(f"❌ Failed to parse GOOGLE_JSON: {e}")
    creds_dict = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I’m your bot and I’m running on Railway 🚀")

if BOT_TOKEN:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 Bot is running...")
    app.run_polling()
