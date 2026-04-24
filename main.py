import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from dotenv import load_dotenv
import parser
import database
from vendors.base import BaseRecipe

load_dotenv()

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States
LISTENING, SELECTING_VENDOR, VALIDATING, AUTOMATING, CHALLENGE = range(5)

SUPPORTED_VENDORS = ["OXXO", "Walmart", "Amazon MX", "Shell", "Other"]

from vendors.oxxo import OxxoRecipe
from vendors.walmart import WalmartRecipe

# Map the vendor name to the class
RECIPES = {
    "OXXO": OxxoRecipe,
    "Walmart": WalmartRecipe
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("MX-AutoInvoice Bot is active. Send me a photo of your ticket, use /history for records, or /status for portal health.")
    return LISTENING

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking portal health... Please wait.")
    
    results = []
    for name, recipe_class in RECIPES.items():
        try:
            worker = recipe_class(headless=True)
            is_healthy, msg = worker.check_health()
            icon = "✅" if is_healthy else "❌"
            results.append(f"{icon} *{name}*: {msg}")
            worker.close()
        except Exception as e:
            results.append(f"❌ *{name}*: Unexpected error {str(e)}")
            
    await update.message.reply_text("\n".join(results), parse_mode='Markdown')

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    records = database.get_user_history(chat_id)
    
    if not records:
        await update.message.reply_text("No previous submissions found.")
        return
    
    msg = "Recent Submissions:\n\n"
    for rec in records:
        msg += f"📅 {rec[4].strftime('%Y-%m-%d %H:%M')}\n📍 {rec[0]} | 📑 {rec[1]} | 💰 ${rec[2]}\nStatus: {rec[3]}\n\n"
    
    await update.message.reply_text(msg)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_path = os.path.join("storage", f"{photo.file_id}.jpg")
    await file.download_to_drive(photo_path)
    
    await update.message.reply_text("Scanning ticket with Gemini...")
    
    ticket_data = parser.parse_ticket(photo_path)
    if not ticket_data:
        await update.message.reply_text("Could not parse ticket. Please send a clearer photo.")
        return LISTENING
    
    context.user_data['ticket_data'] = ticket_data
    context.user_data['photo_path'] = photo_path
    
    # Prompt for Vendor Selection
    keyboard = [[InlineKeyboardButton(v, callback_data=f"vendor_{v}")] for v in SUPPORTED_VENDORS]
    
    # Highlight Gemini's guess
    guess = ticket_data.get('vendor', 'Unknown')
    msg = f"Gemini thinks this is from: *{guess}*\n\nPlease confirm or select the correct vendor:"
    
    await update.message.reply_text(
        msg, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return SELECTING_VENDOR

async def vendor_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_vendor = query.data.replace("vendor_", "")
    context.user_data['ticket_data']['vendor'] = selected_vendor
    ticket_data = context.user_data['ticket_data']
    
    # Save to DB now that vendor is confirmed/selected
    ticket_id = database.add_ticket(
        update.effective_chat.id,
        context.user_data['photo_path'],
        ticket_data.get('vendor'),
        ticket_data.get('folio'),
        ticket_data.get('total'),
        ticket_data.get('date'),
        extra_data=ticket_data.get('extra_data')
    )
    context.user_data['ticket_id'] = ticket_id
    
    extra_msg = ""
    if ticket_data.get('extra_data'):
        for key, value in ticket_data['extra_data'].items():
            if value:
                extra_msg += f"{key.replace('_', ' ').title()}: {value}\n"
    
    msg = (
        f"Confirm details for *{selected_vendor}*:\n"
        f"Folio: {ticket_data.get('folio')}\n"
        f"Total: ${ticket_data.get('total')}\n"
        f"Date: {ticket_data.get('date')}\n"
        f"{extra_msg}\n"
        f"Proceed with automation?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("YES", callback_data='yes'),
            InlineKeyboardButton("EDIT", callback_data='edit'),
            InlineKeyboardButton("CANCEL", callback_data='cancel'),
        ]
    ]
    await query.edit_message_text(
        msg, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return VALIDATING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ticket_id = context.user_data.get('ticket_id')
    
    if query.data == 'yes':
        database.update_ticket_status(ticket_id, 'CONFIRMED')
        await query.edit_message_text("Starting automation... (Email-First)")
        # TODO: Trigger automation worker
        return AUTOMATING
    elif query.data == 'cancel':
        database.update_ticket_status(ticket_id, 'CANCELLED')
        await query.edit_message_text("Operation cancelled.")
        return LISTENING
    else:
        await query.edit_message_text("Edit mode not implemented yet. Please resend photo or cancel.")
        return VALIDATING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

if __name__ == '__main__':
    # Initialize DB
    database.init_db()
    
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start), 
            CommandHandler('history', history),
            CommandHandler('status', status),
            MessageHandler(filters.PHOTO, handle_photo)
        ],
        states={
            LISTENING: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler('history', history),
                CommandHandler('status', status)
            ],
            SELECTING_VENDOR: [CallbackQueryHandler(vendor_selection_handler, pattern="^vendor_")],
            VALIDATING: [CallbackQueryHandler(button_handler)],
            AUTOMATING: [],
            CHALLENGE: []
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(conv_handler)
    print("Bot is running...")
    app.run_polling()
