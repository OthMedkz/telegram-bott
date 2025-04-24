from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import json
import gspread
from google.oauth2.service_account import Credentials
import aiohttp
import asyncio
from aiohttp import web

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
        "🛒 Buy eBay Kleinanzeigen Accounts for only 5 USDT each.\n\n"
        "🚀 Fast delivery | Verified & ready to use\n\n"
        "👇 Click the button below to continue.",
        reply_markup=reply_markup
    )

# CALLBACK HANDLER
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "continue":
        quantities = [1, 2, 3, 5, 10, 25, 50, 100]
        keyboard = [[InlineKeyboardButton(str(q), callback_data=f"qty_{q}")] for q in quantities]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛒 Select the quantity of accounts you want to buy:", reply_markup=reply_markup)

    elif query.data.startswith("qty_"):
        quantity = int(query.data.split("_")[1])
        total_price = quantity * 5
        context.user_data['quantity'] = quantity
        context.user_data['price'] = total_price

        if quantity == 1:
            msg = (
                f"💳 You selected {quantity} account.\n\n"
                "💰 Total: 5 USDT\n\n"
                "Available payment methods for 1 account:\n"
                "LTC, DOGE, XRP, BNB (BEP20).\n\n"
                "👇 Choose your payment method:"
            )
            coins = ["ltc", "doge", "xrp", "bnbbep20"]
        else:
            msg = (
                f"💳 You selected {quantity} accounts.\n\n"
                f"💰 Total: {total_price} USDT\n\n"
                "Available payment methods:\n"
                "USDT (TRC20), LTC, DOGE, XRP, BNB (BEP20).\n\n"
                "👇 Choose your payment method:"
            )
            coins = ["usdttrc20", "ltc", "doge", "xrp", "bnbbep20"]

        keyboard = [[InlineKeyboardButton(coin.upper(), callback_data=f"pay_{coin}")] for coin in coins]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, reply_markup=reply_markup)

    elif query.data.startswith("pay_"):
        pay_currency = query.data.split("_")[1]
        quantity = context.user_data['quantity']
        total_price = context.user_data['price']

        payment_url = await create_nowpayments_invoice(total_price, pay_currency)

        context.user_data['payment_url'] = payment_url
        context.user_data['pay_currency'] = pay_currency

        await query.edit_message_text(
            f"💳 You selected {quantity} account(s).\n\n"
            f"💰 Total: {total_price} USD\n\n"
            f"👉 Pay with {pay_currency.upper()} here: {payment_url}\n\n"
            f"After payment, reply with 'Paid' to confirm."
        )

# NOWPayments Invoice Function
async def create_nowpayments_invoice(amount, pay_currency):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": pay_currency,
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

# CONFIRM PAYMENT (Manual)
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "paid":
        quantity = context.user_data.get('quantity')
        price = context.user_data.get('price')
        username = update.message.from_user.username
        payment_url = context.user_data.get('payment_url')
        pay_currency = context.user_data.get('pay_currency')

        sheet.append_row([username, quantity, price, pay_currency, payment_url, "Paid"])

        await update.message.reply_text("✅ Payment confirmed! Your accounts will be delivered shortly. Thank you!")

# IPN HANDLER (Auto Payment Confirmation)
async def handle_webhook(request):
    data = await request.json()
    print("Received IPN:", data)

    payment_status = data.get("payment_status")
    pay_amount = data.get("price_amount")
    order_description = data.get("order_description")
    payment_id = data.get("payment_id")

    if payment_status == "finished":
        print(f"Payment {payment_id} confirmed for {pay_amount} - {order_description}")
        # TODO: Auto send accounts or update sheet

    return web.Response(text="OK")

# MAIN APP
async def main():
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_handler(CommandHandler("confirm", confirm_payment))
    telegram_app.add_handler(CommandHandler("paid", confirm_payment))

    aiohttp_app = web.Application()
    aiohttp_app.router.add_post('/ipn', handle_webhook)

    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    print("🚀 Bot and webhook are running...")
    await telegram_app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())