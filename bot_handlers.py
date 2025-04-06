import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, 
    MessageHandler, Filters, CallbackContext, ConversationHandler
)
from data_store import DataStore

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# State definitions for conversation handler
CREATE_LIST, ADD_ITEM, SELECT_LIST, RATE_ITEM, SELECTING_ITEM_TO_RATE = range(5)

# Initialize the data store
data_store = DataStore()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to List Rater Bot!\n\n"
        "You can use this bot to create lists and rate items from 0 to 10.\n\n"
        "Commands:\n"
        "/newlist - Create a new list\n"
        "/additem - Add an item to a list\n"
        "/lists - View all available lists\n"
        "/viewlist - View items in a specific list\n"
        "/rate - Rate an item in a list\n"
        "/ratings - View ratings for items in a list\n"
        "/help - Show this help message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(
        "List Rater Bot Commands:\n\n"
        "/newlist - Create a new list\n"
        "/additem - Add an item to a list\n"
        "/lists - View all available lists\n"
        "/viewlist - View items in a specific list\n"
        "/rate - Rate an item in a list\n"
        "/ratings - View ratings for items in a list\n"
        "/help - Show this help message"
    )

# List creation handlers
async def new_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of creating a new list."""
    await update.message.reply_text(
        "Let's create a new list! What would you like to name your list?"
    )
    return CREATE_LIST

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create a new list with the provided name."""
    list_name = update.message.text
    user_id = str(update.effective_user.id)
    
    # Check if list name already exists for this user
    if data_store.list_exists(user_id, list_name):
        await update.message.reply_text(
            f"You already have a list named '{list_name}'. Please choose a different name."
        )
        return CREATE_LIST
    
    # Create the new list
    data_store.create_list(user_id, list_name)
    
    await update.message.reply_text(
        f"Great! I've created a new list called '{list_name}'.\n"
        f"You can add items to it with /additem"
    )
    return ConversationHandler.END

# List viewing handlers
async def show_lists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all lists created by the user."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        await update.message.reply_text(
            "You haven't created any lists yet. Use /newlist to create one!"
        )
        return
    
    message = "Your lists:\n\n"
    for i, list_name in enumerate(lists, 1):
        message += f"{i}. {list_name}\n"
    
    await update.message.reply_text(message)

# Item addition handlers
async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of adding an item to a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        await update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"add_to_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a list to add an item to:", reply_markup=reply_markup)
    
    return SELECT_LIST

async def select_list_for_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the list selection for adding an item."""
    query = update.callback_query
    await query.answer()
    
    list_name = query.data.replace("add_to_", "")
    context.user_data["selected_list"] = list_name
    
    await query.edit_message_text(f"What item would you like to add to '{list_name}'?")
    
    return ADD_ITEM

async def add_item_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Add an item to the selected list."""
    user_id = str(update.effective_user.id)
    list_name = context.user_data.get("selected_list")
    item_name = update.message.text
    
    if not list_name:
        await update.message.reply_text("Something went wrong. Please try again with /additem")
        return ConversationHandler.END
    
    # Check if item already exists in this list
    if data_store.item_exists(user_id, list_name, item_name):
        await update.message.reply_text(
            f"'{item_name}' already exists in '{list_name}'. Please add a different item."
        )
        return ADD_ITEM
    
    # Add the item to the list
    data_store.add_item(user_id, list_name, item_name)
    
    await update.message.reply_text(
        f"Added '{item_name}' to '{list_name}'!\n"
        f"You can rate it with /rate"
    )
    
    return ConversationHandler.END

# View list items handlers
async def view_list_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of viewing items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        await update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"view_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a list to view:", reply_markup=reply_markup)
    
    return SELECT_LIST

async def view_list_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the items in the selected list."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("view_", "")
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        await query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
    else:
        message = f"Items in '{list_name}':\n\n"
        for i, item_data in enumerate(items.items(), 1):
            item_name, ratings = item_data
            avg_rating = sum(ratings) / len(ratings) if ratings else "Not yet rated"
            message += f"{i}. {item_name} - Average rating: {avg_rating}\n"
        
        await query.edit_message_text(message)
    
    return ConversationHandler.END

# Rating handlers
async def rate_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of rating an item."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        await update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"rate_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a list that contains the item you want to rate:", reply_markup=reply_markup)
    
    return SELECT_LIST

async def select_list_for_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the list selection for rating an item."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("rate_list_", "")
    context.user_data["rating_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        await query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"rate_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Choose an item from '{list_name}' to rate:", reply_markup=reply_markup)
    
    return SELECTING_ITEM_TO_RATE

async def select_item_for_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the item selection for rating."""
    query = update.callback_query
    await query.answer()
    
    item_name = query.data.replace("rate_item_", "")
    context.user_data["rating_item"] = item_name
    
    # Create rating keyboard with buttons 0-10
    keyboard = []
    row = []
    for i in range(11):  # 0 to 10
        row.append(InlineKeyboardButton(str(i), callback_data=f"give_rating_{i}"))
        if len(row) == 4 or i == 10:  # 4 buttons per row, or last button
            keyboard.append(row.copy())
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Rate '{item_name}' on a scale from 0 to 10:",
        reply_markup=reply_markup
    )
    
    return RATE_ITEM

async def apply_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Apply the rating to the selected item."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("rating_list")
    item_name = context.user_data.get("rating_item")
    rating = int(query.data.replace("give_rating_", ""))
    
    if not all([list_name, item_name]):
        await query.edit_message_text("Something went wrong. Please try again with /rate")
        return ConversationHandler.END
    
    # Add the rating to the item
    data_store.add_rating(user_id, list_name, item_name, rating)
    
    await query.edit_message_text(
        f"You rated '{item_name}' a {rating}/10!"
    )
    
    return ConversationHandler.END

# View ratings handlers
async def view_ratings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of viewing ratings for items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        await update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"ratings_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a list to view ratings:", reply_markup=reply_markup)
    
    return SELECT_LIST

async def view_list_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the ratings for items in the selected list."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("ratings_", "")
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        await query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
    else:
        message = f"Ratings for items in '{list_name}':\n\n"
        for item_name, ratings in items.items():
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                all_ratings = ", ".join(str(r) for r in ratings)
                message += f"• {item_name}\n"
                message += f"  Average: {avg_rating:.1f}/10\n"
                message += f"  All ratings: {all_ratings}\n\n"
            else:
                message += f"• {item_name}: Not yet rated\n\n"
        
        await query.edit_message_text(message)
    
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def setup_bot():
    """Set up the Telegram bot with all handlers."""
    # Get telegram token from environment
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
    # Create the application
    application = ApplicationBuilder().token(telegram_token).build()
    
    # Add handlers
    # Create list conversation
    create_list_handler = ConversationHandler(
        entry_points=[CommandHandler("newlist", new_list)],
        states={
            CREATE_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_list)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add item conversation
    add_item_handler = ConversationHandler(
        entry_points=[CommandHandler("additem", add_item_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(select_list_for_item, pattern="^add_to_")],
            ADD_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_to_list)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # View list conversation
    view_list_handler = ConversationHandler(
        entry_points=[CommandHandler("viewlist", view_list_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(view_list_items, pattern="^view_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Rate item conversation
    rate_item_handler = ConversationHandler(
        entry_points=[CommandHandler("rate", rate_item_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(select_list_for_rating, pattern="^rate_list_")],
            SELECTING_ITEM_TO_RATE: [CallbackQueryHandler(select_item_for_rating, pattern="^rate_item_")],
            RATE_ITEM: [CallbackQueryHandler(apply_rating, pattern="^give_rating_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # View ratings conversation
    view_ratings_handler = ConversationHandler(
        entry_points=[CommandHandler("ratings", view_ratings_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(view_list_ratings, pattern="^ratings_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add all handlers to the application
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lists", show_lists))
    application.add_handler(create_list_handler)
    application.add_handler(add_item_handler)
    application.add_handler(view_list_handler)
    application.add_handler(rate_item_handler)
    application.add_handler(view_ratings_handler)
    
    # Start the bot (polling mode)
    application.run_polling()
    
    return application
