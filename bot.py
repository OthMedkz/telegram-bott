from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_JSON = os.getenv("GOOGLE_JSON")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")

# Load Google Sheets credentials
creds_dict = json.loads(GOOGLE_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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
        # Create NOWPayments invoice (mock)
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

# MOCK NOWPayments Invoice Function
async def create_nowpayments_invoice(amount):
    # Replace with real NOWPayments API request if needed
    return f"https://nowpayments.io/payment?amount={amount}&currency=usdt"

# CONFIRM PAYMENT (Reply Handler)
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "paid":
        quantity = context.user_data.get('quantity')
        price = context.user_data.get('price')
        username = update.message.from_user.username
        payment_url = context.user_data.get('payment_url')

        # Save to Google Sheet
        sheet.append_row([username, quantity, price, payment_url, "Paid"])

        await update.message.reply_text("✅ Payment confirmed! Your accounts will be delivered shortly. Thank you!")

# MAIN APP
if BOT_TOKEN:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    app.add_handler(CommandHandler("paid", confirm_payment))  # for text "Paid"
    app.add_handler(CommandHandler("Paid", confirm_payment))  # capitalized
    app.add_handler(CommandHandler("PAID", confirm_payment))  # all caps
    app.add_handler(CommandHandler("p", confirm_payment))  # just in case shortcuts
    print("🚀 Bot is running...")
    app.run_polling()
