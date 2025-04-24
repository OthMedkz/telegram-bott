import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web
import aiohttp
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_JSON = os.getenv("GOOGLE_JSON")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")

# Google Sheets Setup
creds_dict = json.loads(GOOGLE_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1

# Telegram Handlers (start, button_handler, confirm_payment - same as you have)

# ... keep your Telegram handlers unchanged ...

# NOWPayments Invoice Function
async def create_nowpayments_invoice(amount):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_description": "eBay Accounts",
        "ipn_callback_url": "https://telegram-bott-production.up.railway.app/ipn"  # Set your Railway URL
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            result = await resp.json()
            print("NOWPayments API Response:", result)

            if resp.status == 200 and "invoice_url" in result:
                return result["invoice_url"]
            else:
                raise Exception(f"NOWPayments error: {result}")

# Webhook Handler for IPN
async def handle_webhook(request):
    data = await request.json()
    print("Received IPN:", data)

    payment_status = data.get("payment_status")
    pay_amount = data.get("price_amount")
    order_description = data.get("order_description")
    payment_id = data.get("payment_id")

    if payment_status == "finished":
        print(f"Payment {payment_id} confirmed for {pay_amount} - {order_description}")
        # Update Google Sheets, send message, etc.

    return web.Response(text="OK")

# COMBINED RUN FUNCTION
async def main():
    # Start Telegram bot
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_handler(CommandHandler("confirm", confirm_payment))
    telegram_app.add_handler(CommandHandler("paid", confirm_payment))

    # Start aiohttp server
    app_web = web.Application()
    app_web.router.add_post('/ipn', handle_webhook)

    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Webhook server running on port 8080...")

    # Run Telegram bot polling concurrently
    await telegram_app.run_polling()

# ENTRY POINT
if __name__ == "__main__":
    asyncio.run(main())
