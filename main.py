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

# Security Whitelist
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

def restricted(func):
    """Decorator to restrict access to the bot to admins only."""
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            logging.warning(f"Unauthorized access attempt by {user_id}")
            await update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

import sys
import warnings
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)

# Silence httpx logger to avoid log saturation
logging.getLogger("httpx").setLevel(logging.WARNING)

# States
SELECTING_VENDOR, WAITING_FOR_PHOTO, VALIDATING, AUTOMATING, CHALLENGE = range(5)

SUPPORTED_VENDORS = ["OXXO", "Walmart"]

from vendors.oxxo import OxxoRecipe
from vendors.walmart import WalmartRecipe

# Map the vendor name to the class
RECIPES = {
    "OXXO": OxxoRecipe,
    "Walmart": WalmartRecipe
}

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v, callback_data=f"vendor_{v}")] for v in SUPPORTED_VENDORS]
    await update.message.reply_text(
        "MX-AutoInvoice Bot is active.\nPlease select the vendor for your ticket:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_VENDOR

@restricted
async def handle_photo_without_vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v, callback_data=f"vendor_{v}")] for v in SUPPORTED_VENDORS]
    await update.message.reply_text(
        "Please select a vendor first before sending the photo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_VENDOR

@restricted
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

@restricted
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

@restricted
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_vendor = context.user_data.get('selected_vendor')
    if not selected_vendor:
        keyboard = [[InlineKeyboardButton(v, callback_data=f"vendor_{v}")] for v in SUPPORTED_VENDORS]
        await update.message.reply_text("Please select a vendor first:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECTING_VENDOR

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_path = os.path.join("storage", f"{photo.file_id}.jpg")
    await file.download_to_drive(photo_path)
    
    await update.message.reply_text(f"Scanning ticket for {selected_vendor} with Gemini...")
    
    try:
        ticket_data = parser.parse_ticket(photo_path, selected_vendor)
        if not ticket_data:
            await update.message.reply_text("😕 Gemini scanned the photo but couldn't find invoice data. Please try a clearer or closer photo.")
            return WAITING_FOR_PHOTO
    except Exception as e:
        logging.error(f"Gemini API Error: {e}")
        await update.message.reply_text("⚠️ Gemini API is currently unavailable or returned an error. Please try again in a few minutes.")
        return WAITING_FOR_PHOTO
    
    ticket_data['vendor'] = selected_vendor
    
    context.user_data['ticket_data'] = ticket_data
    context.user_data['photo_path'] = photo_path
    
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
    await update.message.reply_text(
        msg, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return VALIDATING

async def vendor_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_vendor = query.data.replace("vendor_", "")
    context.user_data['selected_vendor'] = selected_vendor
    
    logging.info(f"User {update.effective_user.id} selected vendor: {selected_vendor}")
    
    await query.edit_message_text(f"Vendor selected: *{selected_vendor}*\n\nPlease send me a photo of your ticket now.", parse_mode='Markdown')
    return WAITING_FOR_PHOTO

import asyncio

async def run_automation_worker(recipe_class, ticket_data, chat_id, ticket_id, context):
    """Asynchronous worker to run the browser automation."""
    try:
        # Run the blocking DrissionPage code in a separate thread to keep bot responsive
        def _run():
            worker = recipe_class(headless=True)
            try:
                return worker.run(ticket_data)
            finally:
                worker.close()

        result = await asyncio.to_thread(_run)
        
        status = 'COMPLETED' if "SUCCESS" in result else 'FAILED'
        database.update_ticket_status(ticket_id, status)
        
        await context.bot.send_message(chat_id=chat_id, text=f"🤖 *Automation Result:*\n{result}", parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Worker Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ *Critical Error:* {str(e)}", parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    ticket_id = context.user_data.get('ticket_id')
    ticket_data = context.user_data.get('ticket_data')
    chat_id = update.effective_chat.id
    
    if query.data == 'yes':
        logging.info(f"User {chat_id} confirmed automation for ticket {ticket_id}")
        database.update_ticket_status(ticket_id, 'CONFIRMED')
        await query.edit_message_text("🚀 Starting automation worker... I will notify you when finished.")
        
        recipe_class = RECIPES.get(ticket_data['vendor'])
        if recipe_class:
            # Start the background task
            asyncio.create_task(run_automation_worker(recipe_class, ticket_data, chat_id, ticket_id, context))
        else:
            await query.edit_message_text(f"❌ Vendor {ticket_data['vendor']} not implemented yet.")
        
        return SELECTING_VENDOR # Return to selecting vendor state while worker runs in BG
    elif query.data == 'cancel':
        logging.info(f"User {chat_id} cancelled automation for ticket {ticket_id}")
        database.update_ticket_status(ticket_id, 'CANCELLED')
        await query.edit_message_text("Operation cancelled.")
        return SELECTING_VENDOR
    else:
        await query.edit_message_text("Edit mode not implemented yet. Please resend photo or cancel.")
        return VALIDATING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks here.
    logging.error("Exception while handling an update:", exc_info=context.error)

    # Handle common network errors silently
    from telegram.error import NetworkError, TimedOut
    if isinstance(context.error, (NetworkError, TimedOut)):
        logging.warning(f"Telegram Network Error: {context.error}. Bot will retry automatically.")
        return

    # For other errors, notify the user if possible
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ An unexpected error occurred. Please try again later.")

if __name__ == '__main__':
    # Initialize DB
    database.init_db()
    
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start), 
            CommandHandler('history', history),
            CommandHandler('status', status),
            MessageHandler(filters.PHOTO, handle_photo_without_vendor)
        ],
        states={
            SELECTING_VENDOR: [
                CallbackQueryHandler(vendor_selection_handler, pattern="^vendor_"),
                CommandHandler('history', history),
                CommandHandler('status', status),
                MessageHandler(filters.PHOTO, handle_photo_without_vendor)
            ],
            WAITING_FOR_PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler('history', history),
                CommandHandler('status', status)
            ],
            VALIDATING: [CallbackQueryHandler(button_handler)],
            AUTOMATING: [],
            CHALLENGE: []
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
    )
    
    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)
    print("Bot is running...")
    app.run_polling()
