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
CREATE_LIST, ADD_ITEM, SELECT_LIST, RATE_ITEM, SELECTING_ITEM_TO_RATE, ADD_COMMENT = range(6)
DELETE_LIST, DELETE_ITEM, DELETE_RATING, CONFIRM_DELETE = range(6, 10)

# Initialize the data store
data_store = DataStore()

# Commands that are restricted to admins only
ADMIN_COMMANDS = ['/newlist', '/deletelist', '/deleteitem', '/deleterating', '/clearratings']

def is_admin(update: Update, context: CallbackContext) -> bool:
    """
    Check if the user is an admin in the chat.
    In private chats, the user is always considered an admin.
    
    Args:
        update: The update object
        context: The context object
        
    Returns:
        bool: True if the user is an admin, False otherwise
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # If in a private chat, the user is always considered an admin
    if update.effective_chat.type == 'private':
        return True
        
    try:
        # Check if the user is an admin in the chat
        chat_member = context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False
        
def admin_required(func):
    """
    Decorator to restrict handler access to admins only.
    """
    def wrapped(update, context, *args, **kwargs):
        # Check if user is admin
        if not is_admin(update, context):
            command = update.message.text.split()[0] if update.message and update.message.text else ""
            if command in ADMIN_COMMANDS:
                update.message.reply_text("This command is only available to chat administrators.")
                return ConversationHandler.END
        
        # Call the original handler
        return func(update, context, *args, **kwargs)
    return wrapped

# Command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message when the command /start is issued."""
    is_user_admin = is_admin(update, context)
    
    base_message = (
        "¡Bienvenido al Bot de Listas y Valoraciones!\n\n"
        "Puedes usar este bot para crear listas y valorar elementos del 0 al 10, con la opción de añadir comentarios a tus valoraciones.\n\n"
        "Comandos:\n"
        "/additem - Añadir un elemento a una lista\n"
        "/lists - Ver todas las listas disponibles\n"
        "/viewlist - Ver elementos de una lista específica\n"
        "/rate - Valorar un elemento de una lista y añadir comentarios\n"
        "/ratings - Ver valoraciones y comentarios de elementos en una lista\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/cancel - Cancelar la operación actual"
    )
    
    admin_commands = (
        "\n\nAdmin Commands (only available to chat administrators):\n"
        "/newlist - Create a new list\n"
        "/deletelist - Delete a list and all its items\n"
        "/deleteitem - Delete an item from a list\n"
        "/deleterating - Delete a specific rating\n"
        "/clearratings - Clear all ratings for an item"
    )
    
    # Show admin commands only if the user is an admin
    if is_user_admin:
        update.message.reply_text(base_message + admin_commands)
    else:
        update.message.reply_text(base_message)

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a help message when the command /help is issued."""
    is_user_admin = is_admin(update, context)
    
    base_commands = (
        "Comandos del Bot de Listas y Valoraciones:\n\n"
        "/additem - Añadir un elemento a una lista\n"
        "/lists - Ver todas las listas disponibles\n"
        "/viewlist - Ver elementos de una lista específica\n"
        "/rate - Valorar un elemento (0-10) y añadir comentarios\n"
        "/ratings - Ver valoraciones y comentarios de elementos\n"
        "/help - Mostrar este mensaje de ayuda\n"
        "/cancel - Cancelar la operación actual\n\n"
        "Consejos para valoraciones:\n"
        "- Al valorar elementos, puedes añadir un comentario explicando tu valoración\n"
        "- Usa /skip para omitir añadir un comentario si no quieres explicar tu valoración"
    )
    
    admin_commands = (
        "\n\nAdmin Commands (only available to chat administrators):\n"
        "/newlist - Create a new list\n"
        "/deletelist - Delete a list and all its items\n"
        "/deleteitem - Delete an item from a list\n"
        "/deleterating - Delete a specific rating\n"
        "/clearratings - Clear all ratings for an item"
    )
    
    # Show admin commands only if the user is an admin
    if is_user_admin:
        update.message.reply_text(base_commands + admin_commands)
    else:
        update.message.reply_text(base_commands)

# List creation handlers
def new_list(update: Update, context: CallbackContext) -> int:
    """Start the process of creating a new list."""
    update.message.reply_text(
        "Let's create a new list! What would you like to name your list?"
    )
    return CREATE_LIST

def create_list(update: Update, context: CallbackContext) -> int:
    """Create a new list with the provided name."""
    list_name = update.message.text
    user_id = str(update.effective_user.id)
    
    # Check if list name already exists for this user
    if data_store.list_exists(user_id, list_name):
        update.message.reply_text(
            f"You already have a list named '{list_name}'. Please choose a different name."
        )
        return CREATE_LIST
    
    # Create the new list
    data_store.create_list(user_id, list_name)
    
    update.message.reply_text(
        f"Great! I've created a new list called '{list_name}'.\n"
        f"You can add items to it with /additem"
    )
    return ConversationHandler.END

# List viewing handlers
def show_lists(update: Update, context: CallbackContext) -> None:
    """Show all lists created by the user."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You haven't created any lists yet. Use /newlist to create one!"
        )
        return
    
    message = "Your lists:\n\n"
    for i, list_name in enumerate(lists, 1):
        message += f"{i}. {list_name}\n"
    
    update.message.reply_text(message)

# Item addition handlers
def add_item_start(update: Update, context: CallbackContext) -> int:
    """Start the process of adding an item to a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"add_to_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list to add an item to:", reply_markup=reply_markup)
    
    return SELECT_LIST

def select_list_for_item(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for adding an item."""
    query = update.callback_query
    query.answer()
    
    list_name = query.data.replace("add_to_", "")
    context.user_data["selected_list"] = list_name
    
    query.edit_message_text(f"What item would you like to add to '{list_name}'?")
    
    return ADD_ITEM

def add_item_to_list(update: Update, context: CallbackContext) -> int:
    """Add an item to the selected list."""
    user_id = str(update.effective_user.id)
    list_name = context.user_data.get("selected_list")
    item_name = update.message.text
    
    if not list_name:
        update.message.reply_text("Something went wrong. Please try again with /additem")
        return ConversationHandler.END
    
    # Check if item already exists in this list
    if data_store.item_exists(user_id, list_name, item_name):
        update.message.reply_text(
            f"'{item_name}' already exists in '{list_name}'. Please add a different item."
        )
        return ADD_ITEM
    
    # Add the item to the list
    data_store.add_item(user_id, list_name, item_name)
    
    update.message.reply_text(
        f"Added '{item_name}' to '{list_name}'!\n"
        f"You can rate it with /rate"
    )
    
    return ConversationHandler.END

# View list items handlers
def view_list_start(update: Update, context: CallbackContext) -> int:
    """Start the process of viewing items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"view_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list to view:", reply_markup=reply_markup)
    
    return SELECT_LIST

def view_list_items(update: Update, context: CallbackContext) -> int:
    """Show the items in the selected list."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("view_", "")
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
    else:
        message = f"Items in '{list_name}':\n\n"
        for i, item_data in enumerate(items.items(), 1):
            item_name, ratings = item_data
            
            # Use the get_average_rating helper method
            avg_rating = data_store.get_average_rating(user_id, list_name, item_name)
            avg_rating_text = f"{avg_rating:.1f}" if ratings else "Not yet rated"
            
            message += f"{i}. {item_name} - Average rating: {avg_rating_text}\n"
        
        query.edit_message_text(message)
    
    return ConversationHandler.END

# Rating handlers
def rate_item_start(update: Update, context: CallbackContext) -> int:
    """Start the process of rating an item."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"rate_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list that contains the item you want to rate:", reply_markup=reply_markup)
    
    return SELECT_LIST

def select_list_for_rating(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for rating an item."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("rate_list_", "")
    context.user_data["rating_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"rate_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Choose an item from '{list_name}' to rate:", reply_markup=reply_markup)
    
    return SELECTING_ITEM_TO_RATE

def select_item_for_rating(update: Update, context: CallbackContext) -> int:
    """Handle the item selection for rating."""
    query = update.callback_query
    query.answer()
    
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
    query.edit_message_text(
        f"Rate '{item_name}' on a scale from 0 to 10:",
        reply_markup=reply_markup
    )
    
    return RATE_ITEM

def apply_rating(update: Update, context: CallbackContext) -> int:
    """Store the rating and ask for a comment."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("rating_list")
    item_name = context.user_data.get("rating_item")
    rating = int(query.data.replace("give_rating_", ""))
    
    if not all([list_name, item_name]):
        query.edit_message_text("Something went wrong. Please try again with /rate")
        return ConversationHandler.END
    
    # Store the rating in user_data temporarily
    context.user_data["temp_rating"] = rating
    
    # Ask for a comment
    query.edit_message_text(
        f"You're giving '{item_name}' a {rating}/10!\n\n"
        f"Would you like to add a comment about why you gave this rating?\n"
        f"Type your comment or send /skip to continue without a comment."
    )
    
    return ADD_COMMENT
    
def add_rating_comment(update: Update, context: CallbackContext) -> int:
    """Apply the rating with the user's comment."""
    comment = update.message.text
    user_id = str(update.effective_user.id)
    list_name = context.user_data.get("rating_list")
    item_name = context.user_data.get("rating_item")
    rating = context.user_data.get("temp_rating")
    
    if not all([list_name, item_name, rating is not None]):
        update.message.reply_text("Something went wrong. Please try again with /rate")
        return ConversationHandler.END
    
    # Add the rating with comment to the item
    data_store.add_rating(user_id, list_name, item_name, rating, comment)
    
    update.message.reply_text(
        f"You rated '{item_name}' a {rating}/10 with the comment:\n\n"
        f"\"{comment}\""
    )
    
    return ConversationHandler.END
    
def skip_comment(update: Update, context: CallbackContext) -> int:
    """Skip adding a comment and just save the rating."""
    user_id = str(update.effective_user.id)
    list_name = context.user_data.get("rating_list")
    item_name = context.user_data.get("rating_item")
    rating = context.user_data.get("temp_rating")
    
    if not all([list_name, item_name, rating is not None]):
        update.message.reply_text("Something went wrong. Please try again with /rate")
        return ConversationHandler.END
    
    # Add the rating without comment
    data_store.add_rating(user_id, list_name, item_name, rating)
    
    update.message.reply_text(
        f"You rated '{item_name}' a {rating}/10 without a comment."
    )
    
    return ConversationHandler.END

# View ratings handlers
def view_ratings_start(update: Update, context: CallbackContext) -> int:
    """Start the process of viewing ratings for items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"ratings_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list to view ratings:", reply_markup=reply_markup)
    
    return SELECT_LIST

def view_list_ratings(update: Update, context: CallbackContext) -> int:
    """Show the ratings for items in the selected list."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("ratings_", "")
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
    else:
        message = f"Ratings for items in '{list_name}':\n\n"
        for item_name, ratings in items.items():
            if ratings:
                # Use the get_average_rating helper method
                avg_rating = data_store.get_average_rating(user_id, list_name, item_name)
                
                message += f"• {item_name}\n"
                message += f"  Average: {avg_rating:.1f}/10\n"
                message += f"  All ratings:\n"
                
                # Show each rating with its comment if available
                for i, (rating, comment) in enumerate(ratings, 1):
                    message += f"    {i}. {rating}/10"
                    if comment:
                        message += f" - \"{comment}\""
                    message += "\n"
                message += "\n"
            else:
                message += f"• {item_name}: Not yet rated\n\n"
        
        # If message is too long, split it
        if len(message) > 4000:  # Telegram message limit is around 4096 characters
            message = message[:3950] + "\n\n... (message truncated due to length)"
            
        query.edit_message_text(message)
    
    return ConversationHandler.END

# Delete list handlers
@admin_required
def delete_list_start(update: Update, context: CallbackContext) -> int:
    """Start the process of deleting a list. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("⚠️ Choose a list to DELETE:", reply_markup=reply_markup)
    
    return DELETE_LIST

def confirm_delete_list(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting a list."""
    query = update.callback_query
    query.answer()
    
    list_name = query.data.replace("delete_list_", "")
    context.user_data["delete_list_name"] = list_name
    
    keyboard = [
        [InlineKeyboardButton("Yes, delete this list", callback_data="confirm_delete_list")],
        [InlineKeyboardButton("No, keep this list", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ Are you sure you want to delete the list '{list_name}' and all its items and ratings?\n\n"
        "This action cannot be undone!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_delete_list(update: Update, context: CallbackContext) -> int:
    """Delete the selected list after confirmation."""
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel_delete":
        query.edit_message_text("Deletion cancelled. Your list is safe.")
        return ConversationHandler.END
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_list_name")
    
    if not list_name:
        query.edit_message_text("Something went wrong. Please try again with /deletelist")
        return ConversationHandler.END
    
    # Delete the list
    success = data_store.delete_list(user_id, list_name)
    
    if success:
        query.edit_message_text(f"The list '{list_name}' has been deleted.")
    else:
        query.edit_message_text(f"Failed to delete the list '{list_name}'. Please try again later.")
    
    return ConversationHandler.END

# Delete item handlers
@admin_required
def delete_item_start(update: Update, context: CallbackContext) -> int:
    """Start the process of deleting an item. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_item_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list that contains the item you want to delete:", reply_markup=reply_markup)
    
    return DELETE_LIST

def select_list_for_delete_item(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for deleting an item."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("delete_item_list_", "")
    context.user_data["delete_item_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    
    if not items:
        query.edit_message_text(
            f"The list '{list_name}' is empty. Add items with /additem"
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"delete_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"⚠️ Choose an item from '{list_name}' to DELETE:", reply_markup=reply_markup)
    
    return DELETE_ITEM

def confirm_delete_item(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting an item."""
    query = update.callback_query
    query.answer()
    
    item_name = query.data.replace("delete_item_", "")
    list_name = context.user_data.get("delete_item_list")
    
    if not list_name:
        query.edit_message_text("Something went wrong. Please try again with /deleteitem")
        return ConversationHandler.END
    
    context.user_data["delete_item_name"] = item_name
    
    keyboard = [
        [InlineKeyboardButton("Yes, delete this item", callback_data="confirm_delete_item")],
        [InlineKeyboardButton("No, keep this item", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ Are you sure you want to delete the item '{item_name}' from the list '{list_name}'?\n\n"
        "This will delete all ratings and comments for this item. This action cannot be undone!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_delete_item(update: Update, context: CallbackContext) -> int:
    """Delete the selected item after confirmation."""
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel_delete":
        query.edit_message_text("Deletion cancelled. Your item is safe.")
        return ConversationHandler.END
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_item_list")
    item_name = context.user_data.get("delete_item_name")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Something went wrong. Please try again with /deleteitem")
        return ConversationHandler.END
    
    # Delete the item
    success = data_store.delete_item(user_id, list_name, item_name)
    
    if success:
        query.edit_message_text(f"The item '{item_name}' has been deleted from the list '{list_name}'.")
    else:
        query.edit_message_text(f"Failed to delete the item '{item_name}'. Please try again later.")
    
    return ConversationHandler.END

# Delete rating handlers
@admin_required
def delete_rating_start(update: Update, context: CallbackContext) -> int:
    """Start the process of deleting a rating. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_rating_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list that contains the item with ratings you want to delete:", reply_markup=reply_markup)
    
    return DELETE_LIST

def select_list_for_delete_rating(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for deleting a rating."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("delete_rating_list_", "")
    context.user_data["delete_rating_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    items_with_ratings = {item: ratings for item, ratings in items.items() if ratings}
    
    if not items_with_ratings:
        query.edit_message_text(
            f"No items in the list '{list_name}' have ratings yet."
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items_with_ratings:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"delete_rating_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Choose an item from '{list_name}' with ratings to delete:", reply_markup=reply_markup)
    
    return DELETE_ITEM

def select_item_for_delete_rating(update: Update, context: CallbackContext) -> int:
    """Handle the item selection for deleting a rating."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    item_name = query.data.replace("delete_rating_item_", "")
    list_name = context.user_data.get("delete_rating_list")
    
    if not list_name:
        query.edit_message_text("Something went wrong. Please try again with /deleterating")
        return ConversationHandler.END
    
    context.user_data["delete_rating_item"] = item_name
    
    ratings = data_store.get_item_ratings(user_id, list_name, item_name)
    
    keyboard = []
    for i, (rating, comment) in enumerate(ratings):
        display_text = f"{rating}/10"
        if comment:
            # Truncate long comments for the button
            display_comment = comment if len(comment) <= 20 else comment[:17] + "..."
            display_text += f" - \"{display_comment}\""
        
        keyboard.append([InlineKeyboardButton(display_text, callback_data=f"delete_rating_{i}")])
    
    keyboard.append([InlineKeyboardButton("Delete ALL ratings", callback_data="delete_all_ratings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ Choose a rating to DELETE for the item '{item_name}':",
        reply_markup=reply_markup
    )
    
    return DELETE_RATING

def confirm_delete_rating(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting a rating."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_rating_list")
    item_name = context.user_data.get("delete_rating_item")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Something went wrong. Please try again with /deleterating")
        return ConversationHandler.END
    
    if query.data == "delete_all_ratings":
        context.user_data["delete_all_ratings"] = True
        
        keyboard = [
            [InlineKeyboardButton("Yes, delete ALL ratings", callback_data="confirm_delete_rating")],
            [InlineKeyboardButton("No, keep the ratings", callback_data="cancel_delete")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"⚠️ Are you sure you want to delete ALL ratings for the item '{item_name}'?\n\n"
            "This action cannot be undone!",
            reply_markup=reply_markup
        )
        
    else:
        rating_index = int(query.data.replace("delete_rating_", ""))
        context.user_data["delete_rating_index"] = rating_index
        
        ratings = data_store.get_item_ratings(user_id, list_name, item_name)
        rating, comment = ratings[rating_index]
        
        # Format the rating information for display
        rating_info = f"{rating}/10"
        if comment:
            rating_info += f" with comment: \"{comment}\""
        
        keyboard = [
            [InlineKeyboardButton("Yes, delete this rating", callback_data="confirm_delete_rating")],
            [InlineKeyboardButton("No, keep this rating", callback_data="cancel_delete")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"⚠️ Are you sure you want to delete the rating ({rating_info}) for the item '{item_name}'?\n\n"
            "This action cannot be undone!",
            reply_markup=reply_markup
        )
    
    return CONFIRM_DELETE

def execute_delete_rating(update: Update, context: CallbackContext) -> int:
    """Delete the selected rating after confirmation."""
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel_delete":
        query.edit_message_text("Deletion cancelled. The rating is safe.")
        return ConversationHandler.END
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_rating_list")
    item_name = context.user_data.get("delete_rating_item")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Something went wrong. Please try again with /deleterating")
        return ConversationHandler.END
    
    # Check if we're deleting all ratings or just one
    if context.user_data.get("delete_all_ratings", False):
        success = data_store.clear_ratings(user_id, list_name, item_name)
        message = f"All ratings for the item '{item_name}' have been deleted."
    else:
        rating_index = context.user_data.get("delete_rating_index")
        if rating_index is None:
            query.edit_message_text("Something went wrong. Please try again with /deleterating")
            return ConversationHandler.END
            
        success = data_store.delete_rating(user_id, list_name, item_name, rating_index)
        message = f"The selected rating for the item '{item_name}' has been deleted."
    
    if success:
        query.edit_message_text(message)
    else:
        query.edit_message_text("Failed to delete the rating. Please try again later.")
    
    return ConversationHandler.END

# Clear all ratings for an item
@admin_required
def clear_ratings_start(update: Update, context: CallbackContext) -> int:
    """Start the process of clearing all ratings for an item. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "You don't have any lists yet. Create one first with /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"clear_ratings_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a list that contains the item with ratings you want to clear:", reply_markup=reply_markup)
    
    return DELETE_LIST

def select_list_for_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for clearing ratings."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("clear_ratings_list_", "")
    context.user_data["clear_ratings_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    items_with_ratings = {item: ratings for item, ratings in items.items() if ratings}
    
    if not items_with_ratings:
        query.edit_message_text(
            f"No items in the list '{list_name}' have ratings yet."
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items_with_ratings:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"clear_ratings_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Choose an item from '{list_name}' to clear all ratings:", reply_markup=reply_markup)
    
    return DELETE_ITEM

def confirm_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before clearing all ratings for an item."""
    query = update.callback_query
    query.answer()
    
    item_name = query.data.replace("clear_ratings_item_", "")
    list_name = context.user_data.get("clear_ratings_list")
    
    if not list_name:
        query.edit_message_text("Something went wrong. Please try again with /clearratings")
        return ConversationHandler.END
    
    context.user_data["clear_ratings_item"] = item_name
    
    keyboard = [
        [InlineKeyboardButton("Yes, clear ALL ratings", callback_data="confirm_clear_ratings")],
        [InlineKeyboardButton("No, keep the ratings", callback_data="cancel_clear")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ Are you sure you want to clear ALL ratings for the item '{item_name}'?\n\n"
        "This will delete all ratings and comments for this item. This action cannot be undone!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Clear all ratings for the selected item after confirmation."""
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel_clear":
        query.edit_message_text("Operation cancelled. Your ratings are safe.")
        return ConversationHandler.END
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("clear_ratings_list")
    item_name = context.user_data.get("clear_ratings_item")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Something went wrong. Please try again with /clearratings")
        return ConversationHandler.END
    
    # Clear all ratings
    success = data_store.clear_ratings(user_id, list_name, item_name)
    
    if success:
        query.edit_message_text(f"All ratings for the item '{item_name}' have been cleared.")
    else:
        query.edit_message_text(f"Failed to clear ratings for the item '{item_name}'. Please try again later.")
    
    return ConversationHandler.END

# Cancel handler
def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the current conversation."""
    update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def setup_handlers(dispatcher):
    """Set up the Telegram bot handlers on an existing dispatcher."""
    # This function is used by bot_main.py when starting the bot in standalone mode
    
    # Create list conversation (admin only)
    create_list_handler = ConversationHandler(
        entry_points=[CommandHandler("newlist", new_list)],
        states={
            CREATE_LIST: [MessageHandler(Filters.text & ~Filters.command, create_list)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add item conversation
    add_item_handler = ConversationHandler(
        entry_points=[CommandHandler("additem", add_item_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(select_list_for_item, pattern="^add_to_")],
            ADD_ITEM: [MessageHandler(Filters.text & ~Filters.command, add_item_to_list)]
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
            RATE_ITEM: [CallbackQueryHandler(apply_rating, pattern="^give_rating_")],
            ADD_COMMENT: [
                MessageHandler(Filters.text & ~Filters.command, add_rating_comment),
                CommandHandler("skip", skip_comment)
            ]
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
    
    # Delete list conversation (admin only)
    delete_list_handler = ConversationHandler(
        entry_points=[CommandHandler("deletelist", delete_list_start)],
        states={
            DELETE_LIST: [CallbackQueryHandler(confirm_delete_list, pattern="^delete_list_")],
            CONFIRM_DELETE: [CallbackQueryHandler(execute_delete_list, pattern="^(confirm_delete_list|cancel_delete)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Delete item conversation (admin only)
    delete_item_handler = ConversationHandler(
        entry_points=[CommandHandler("deleteitem", delete_item_start)],
        states={
            DELETE_LIST: [CallbackQueryHandler(select_list_for_delete_item, pattern="^delete_item_list_")],
            DELETE_ITEM: [CallbackQueryHandler(confirm_delete_item, pattern="^delete_item_")],
            CONFIRM_DELETE: [CallbackQueryHandler(execute_delete_item, pattern="^(confirm_delete_item|cancel_delete)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Delete rating conversation (admin only)
    delete_rating_handler = ConversationHandler(
        entry_points=[CommandHandler("deleterating", delete_rating_start)],
        states={
            DELETE_LIST: [CallbackQueryHandler(select_list_for_delete_rating, pattern="^delete_rating_list_")],
            DELETE_ITEM: [CallbackQueryHandler(select_item_for_delete_rating, pattern="^delete_rating_item_")],
            DELETE_RATING: [CallbackQueryHandler(confirm_delete_rating, pattern="^(delete_rating_|delete_all_ratings)")],
            CONFIRM_DELETE: [CallbackQueryHandler(execute_delete_rating, pattern="^(confirm_delete_rating|cancel_delete)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Clear ratings conversation (admin only)
    clear_ratings_handler = ConversationHandler(
        entry_points=[CommandHandler("clearratings", clear_ratings_start)],
        states={
            DELETE_LIST: [CallbackQueryHandler(select_list_for_clear_ratings, pattern="^clear_ratings_list_")],
            DELETE_ITEM: [CallbackQueryHandler(confirm_clear_ratings, pattern="^clear_ratings_item_")],
            CONFIRM_DELETE: [CallbackQueryHandler(execute_clear_ratings, pattern="^(confirm_clear_ratings|cancel_clear)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add basic command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("lists", show_lists))
    
    # Add user conversation handlers
    dispatcher.add_handler(add_item_handler)
    dispatcher.add_handler(view_list_handler)
    dispatcher.add_handler(rate_item_handler)
    dispatcher.add_handler(view_ratings_handler)
    
    # Add admin conversation handlers
    dispatcher.add_handler(create_list_handler)  # Admin-only
    dispatcher.add_handler(delete_list_handler)  # Admin-only
    dispatcher.add_handler(delete_item_handler)  # Admin-only
    dispatcher.add_handler(delete_rating_handler)  # Admin-only
    dispatcher.add_handler(clear_ratings_handler)  # Admin-only
    
    # Log all errors
    dispatcher.add_error_handler(lambda update, context: logger.error(
        f"Update {update} caused error: {context.error}"
    ))

def setup_bot():
    """Set up the Telegram bot with all handlers."""
    # Get telegram token from environment
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_TOKEN environment variable is not set")
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
    # Create the updater and dispatcher
    updater = Updater(token=telegram_token)
    dispatcher = updater.dispatcher
    
    # Use the shared setup_handlers function to set up all handlers
    setup_handlers(dispatcher)
    
    # Return the updater to allow graceful stop in server mode
    return updater