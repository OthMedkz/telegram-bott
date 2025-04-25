from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import json
import aiohttp
from aiohttp import web
import gspread
from google.oauth2.service_account import Credentials
import nest_asyncio
nest_asyncio.apply()

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_JSON = os.getenv("GOOGLE_JSON")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")

# Load Google Sheets credentials
creds_dict = json.loads(GOOGLE_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1

# START HANDLER
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Continue", callback_data="continue")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to Daliov Shop!\n\n"
        "🛒 Buy eBay Kleinanzeigen Accounts.\n\n"
        "💲 Each account is 5 USDT.\n\n"
        "⚠️ Minimum 2 accounts required due to crypto limits.\n\n"
        "👇 Click the button below to continue.",
        reply_markup=reply_markup
    )

# CALLBACK HANDLER
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "continue":
        quantities = [2, 3, 5, 10, 25, 50, 100]
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f"qty_{q}")] for q in quantities]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛒 Select the quantity of accounts you want to buy (minimum 2):", reply_markup=reply_markup)

    elif query.data.startswith("qty_"):
        quantity = int(query.data.split("_")[1])
        total_price = quantity * 5
        payment_url = await create_nowpayments_invoice(total_price)

        context.user_data['quantity'] = quantity
        context.user_data['price'] = total_price
        context.user_data['payment_url'] = payment_url

        await query.edit_message_text(
            f"💳 You selected {quantity} account(s).\n\n"
            f"💰 Total: {total_price} USDT\n\n"
            f"👉 Pay here: {payment_url}\n\n"
            f"After payment, reply with 'Paid' to confirm."
        )

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
        "ipn_callback_url": "https://telegram-bott-production.up.railway.app/ipn"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            result = await resp.json()
            print("NOWPayments API Response:", result)

            if resp.status == 200 and "invoice_url" in result:
                return result["invoice_url"]
            else:
                raise Exception(f"NOWPayments error: {result}")

# CONFIRM PAYMENT (Manual Text Handler)
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "paid":
        quantity = context.user_data.get('quantity')
        price = context.user_data.get('price')
        username = update.message.from_user.username
        payment_url = context.user_data.get('payment_url')

        sheet.append_row([username, quantity, price, payment_url, "Paid"])

        await update.message.reply_text("✅ Payment confirmed! Your accounts will be delivered shortly. Thank you!")

# Webhook handler for NOWPayments IPN
async def handle_webhook(request):
    data = await request.json()
    print("Received IPN:", data)

    payment_status = data.get("payment_status")
    pay_amount = data.get("price_amount")
    order_description = data.get("order_description")
    payment_id = data.get("payment_id")

    if payment_status == "finished":
        print(f"Payment {payment_id} confirmed for {pay_amount} - {order_description}")
        # Optional: update sheet or notify

    return web.Response(text="OK")

# MAIN FUNCTION
async def main():
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_handler(CommandHandler("paid", confirm_payment))

    # Start Telegram bot polling
    telegram_task = telegram_app.run_polling()

    # Start aiohttp webhook server
    app_web = web.Application()
    app_web.router.add_post('/ipn', handle_webhook)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🚀 Bot and webhook server running...")

    await telegram_task

# Run everything
import asyncio
asyncio.run(main())