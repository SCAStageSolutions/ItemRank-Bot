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
                update.message.reply_text("Este comando solo está disponible para administradores del chat.")
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
        "\n\nComandos de Administrador (solo disponibles para administradores del chat):\n"
        "/newlist - Crear una nueva lista\n"
        "/deletelist - Eliminar una lista y todos sus elementos\n"
        "/deleteitem - Eliminar un elemento de una lista\n"
        "/deleterating - Eliminar una valoración específica\n"
        "/clearratings - Borrar todas las valoraciones de un elemento"
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
        "\n\nComandos de Administrador (solo disponibles para administradores del chat):\n"
        "/newlist - Crear una nueva lista\n"
        "/deletelist - Eliminar una lista y todos sus elementos\n"
        "/deleteitem - Eliminar un elemento de una lista\n"
        "/deleterating - Eliminar una valoración específica\n"
        "/clearratings - Borrar todas las valoraciones de un elemento"
    )
    
    # Show admin commands only if the user is an admin
    if is_user_admin:
        update.message.reply_text(base_commands + admin_commands)
    else:
        update.message.reply_text(base_commands)

# List creation handlers
@admin_required
def new_list(update: Update, context: CallbackContext) -> int:
    """Start the process of creating a new list."""
    update.message.reply_text(
        "¡Vamos a crear una nueva lista! ¿Cómo quieres llamar a tu lista?"
    )
    return CREATE_LIST

def create_list(update: Update, context: CallbackContext) -> int:
    """Create a new list with the provided name."""
    list_name = update.message.text
    user_id = str(update.effective_user.id)
    
    # Check if list name already exists for this user
    if data_store.list_exists(user_id, list_name):
        update.message.reply_text(
            f"Ya tienes una lista llamada '{list_name}'. Por favor, elige un nombre diferente."
        )
        return CREATE_LIST
    
    # Create the new list
    data_store.create_list(user_id, list_name)
    
    update.message.reply_text(
        f"¡Genial! He creado una nueva lista llamada '{list_name}'.\n"
        f"Puedes añadir elementos con /additem"
    )
    return ConversationHandler.END

# List viewing handlers
def show_lists(update: Update, context: CallbackContext) -> None:
    """Show all lists created by the user."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no has creado ninguna lista. ¡Usa /newlist para crear una!"
        )
        return
    
    message = "Tus listas:\n\n"
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
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"add_to_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Elige una lista para añadir un elemento:", reply_markup=reply_markup)
    
    return SELECT_LIST

def select_list_for_item(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for adding an item."""
    query = update.callback_query
    query.answer()
    
    list_name = query.data.replace("add_to_", "")
    context.user_data["selected_list"] = list_name
    
    query.edit_message_text(f"¿Qué elemento quieres añadir a '{list_name}'?")
    
    return ADD_ITEM

def add_item_to_list(update: Update, context: CallbackContext) -> int:
    """Add an item to the selected list."""
    user_id = str(update.effective_user.id)
    list_name = context.user_data.get("selected_list")
    item_name = update.message.text
    
    if not list_name:
        update.message.reply_text("Algo salió mal. Por favor, inténtalo de nuevo con /additem")
        return ConversationHandler.END
    
    # Check if item already exists in this list
    if data_store.item_exists(user_id, list_name, item_name):
        update.message.reply_text(
            f"'{item_name}' ya existe en '{list_name}'. Por favor, añade un elemento diferente."
        )
        return ADD_ITEM
    
    # Add the item to the list
    data_store.add_item(user_id, list_name, item_name)
    
    update.message.reply_text(
        f"¡Añadido '{item_name}' a '{list_name}'!\n"
        f"Puedes valorarlo con /rate"
    )
    
    return ConversationHandler.END

# View list items handlers
def view_list_start(update: Update, context: CallbackContext) -> int:
    """Start the process of viewing items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"view_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Elige una lista para ver:", reply_markup=reply_markup)
    
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
            f"La lista '{list_name}' está vacía. Añade elementos con /additem"
        )
    else:
        message = f"Elementos en '{list_name}':\n\n"
        for i, item_data in enumerate(items.items(), 1):
            item_name, ratings = item_data
            
            # Use the get_average_rating helper method
            avg_rating = data_store.get_average_rating(user_id, list_name, item_name)
            avg_rating_text = f"{avg_rating:.1f}" if ratings else "Sin valorar"
            
            message += f"{i}. {item_name} - Valoración media: {avg_rating_text}\n"
        
        query.edit_message_text(message)
    
    return ConversationHandler.END

# Rating handlers
def rate_item_start(update: Update, context: CallbackContext) -> int:
    """Start the process of rating an item."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"rate_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Elige una lista que contenga el elemento que quieres valorar:", reply_markup=reply_markup)
    
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
            f"La lista '{list_name}' está vacía. Añade elementos con /additem"
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"rate_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Elige un elemento de '{list_name}' para valorar:", reply_markup=reply_markup)
    
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
        f"Valora '{item_name}' en una escala del 0 al 10:",
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
        query.edit_message_text("Algo salió mal. Por favor, inténtalo de nuevo con /rate")
        return ConversationHandler.END
    
    # Store the rating in user_data temporarily
    context.user_data["temp_rating"] = rating
    
    # Ask for a comment
    query.edit_message_text(
        f"¡Has dado a '{item_name}' un {rating}/10!\n\n"
        f"¿Te gustaría añadir un comentario sobre por qué has dado esta valoración?\n"
        f"Escribe tu comentario o envía /skip para continuar sin un comentario."
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
        update.message.reply_text("Algo salió mal. Por favor, inténtalo de nuevo con /rate")
        return ConversationHandler.END
    
    # Add the rating with comment to the item
    data_store.add_rating(user_id, list_name, item_name, rating, comment)
    
    update.message.reply_text(
        f"Has valorado '{item_name}' con un {rating}/10 y el comentario:\n\n"
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
        update.message.reply_text("Algo salió mal. Por favor, inténtalo de nuevo con /rate")
        return ConversationHandler.END
    
    # Add the rating without comment
    data_store.add_rating(user_id, list_name, item_name, rating)
    
    update.message.reply_text(
        f"Has valorado '{item_name}' con un {rating}/10 sin comentario."
    )
    
    return ConversationHandler.END

# View ratings handlers
def view_ratings_start(update: Update, context: CallbackContext) -> int:
    """Start the process of viewing ratings for items in a list."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"ratings_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Elige una lista para ver las valoraciones:", reply_markup=reply_markup)
    
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
            f"La lista '{list_name}' está vacía. Añade elementos con /additem"
        )
    else:
        message = f"Valoraciones para elementos en '{list_name}':\n\n"
        for item_name, ratings in items.items():
            if ratings:
                # Use the get_average_rating helper method
                avg_rating = data_store.get_average_rating(user_id, list_name, item_name)
                
                message += f"• {item_name}\n"
                message += f"  Promedio: {avg_rating:.1f}/10\n"
                message += f"  Todas las valoraciones:\n"
                
                # Show each rating with its comment if available
                for i, (rating, comment) in enumerate(ratings, 1):
                    message += f"    {i}. {rating}/10"
                    if comment:
                        message += f" - \"{comment}\""
                    message += "\n"
                message += "\n"
            else:
                message += f"• {item_name}: Sin valorar aún\n\n"
        
        # If message is too long, split it
        if len(message) > 4000:  # Telegram message limit is around 4096 characters
            message = message[:3950] + "\n\n... (mensaje truncado debido a su longitud)"
            
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
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("⚠️ Elige una lista para ELIMINAR:", reply_markup=reply_markup)
    
    return DELETE_LIST

def confirm_delete_list(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting a list."""
    query = update.callback_query
    query.answer()
    
    list_name = query.data.replace("delete_list_", "")
    context.user_data["delete_list_name"] = list_name
    
    keyboard = [
        [InlineKeyboardButton("Sí, eliminar esta lista", callback_data="confirm_delete_list")],
        [InlineKeyboardButton("No, mantener esta lista", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ ¿Estás seguro de que quieres eliminar la lista '{list_name}' y todos sus elementos y valoraciones?\n\n"
        "¡Esta acción no se puede deshacer!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_delete_list(update: Update, context: CallbackContext) -> int:
    """Delete the selected list after confirmation."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_list_name")
    
    if not list_name:
        query.edit_message_text("Algo salió mal. Por favor, inténtalo de nuevo con /deletelist")
        return ConversationHandler.END
    
    # Delete the list
    success = data_store.delete_list(user_id, list_name)
    
    if success:
        query.edit_message_text(f"✅ La lista '{list_name}' ha sido eliminada junto con todos sus elementos y valoraciones.")
    else:
        query.edit_message_text(f"❌ No se pudo eliminar la lista '{list_name}'. Por favor, inténtalo de nuevo.")
    
    return ConversationHandler.END

# Delete item handlers
@admin_required
def delete_item_start(update: Update, context: CallbackContext) -> int:
    """Start the process of deleting an item. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_item_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Selecciona una lista que contenga el elemento que quieres eliminar:", reply_markup=reply_markup)
    
    return DELETE_ITEM

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
            f"La lista '{list_name}' está vacía. No hay elementos para eliminar."
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"delete_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"⚠️ Selecciona un elemento de '{list_name}' para ELIMINAR:", reply_markup=reply_markup)
    
    return CONFIRM_DELETE

def confirm_delete_item(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting an item."""
    query = update.callback_query
    query.answer()
    
    item_name = query.data.replace("delete_item_", "")
    context.user_data["delete_item_name"] = item_name
    
    keyboard = [
        [InlineKeyboardButton("Sí, eliminar este elemento", callback_data="confirm_delete_item")],
        [InlineKeyboardButton("No, mantener este elemento", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ ¿Estás seguro de que quieres eliminar '{item_name}' y todas sus valoraciones?\n\n"
        "¡Esta acción no se puede deshacer!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_delete_item(update: Update, context: CallbackContext) -> int:
    """Delete the selected item after confirmation."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_item_list")
    item_name = context.user_data.get("delete_item_name")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Algo salió mal. Por favor, inténtalo de nuevo con /deleteitem")
        return ConversationHandler.END
    
    # Delete the item
    success = data_store.delete_item(user_id, list_name, item_name)
    
    if success:
        query.edit_message_text(f"✅ '{item_name}' ha sido eliminado de '{list_name}' junto con todas sus valoraciones.")
    else:
        query.edit_message_text(f"❌ No se pudo eliminar '{item_name}'. Por favor, inténtalo de nuevo.")
    
    return ConversationHandler.END

# Delete rating handlers
@admin_required
def delete_rating_start(update: Update, context: CallbackContext) -> int:
    """Start the process of deleting a rating. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"delete_rating_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Selecciona una lista que contenga la valoración que quieres eliminar:", reply_markup=reply_markup)
    
    return DELETE_RATING

def select_list_for_delete_rating(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for deleting a rating."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("delete_rating_list_", "")
    context.user_data["delete_rating_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    
    # Filter only items with ratings
    items_with_ratings = {name: ratings for name, ratings in items.items() if ratings}
    
    if not items_with_ratings:
        query.edit_message_text(
            f"No hay valoraciones para eliminar en la lista '{list_name}'."
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items_with_ratings:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"delete_rating_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Selecciona un elemento de '{list_name}' para ver sus valoraciones:", reply_markup=reply_markup)
    
    return CONFIRM_DELETE

def select_item_for_delete_rating(update: Update, context: CallbackContext) -> int:
    """Handle the item selection for deleting a rating."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_rating_list")
    item_name = query.data.replace("delete_rating_item_", "")
    context.user_data["delete_rating_item"] = item_name
    
    ratings = data_store.get_item_ratings(user_id, list_name, item_name)
    
    if not ratings:
        query.edit_message_text(
            f"No hay valoraciones para '{item_name}' en la lista '{list_name}'."
        )
        return ConversationHandler.END
    
    message = f"Valoraciones para '{item_name}':\n\n"
    keyboard = []
    
    for i, (rating, comment) in enumerate(ratings, 0):  # Start from 0 for index
        comment_text = f" - \"{comment}\"" if comment else ""
        message += f"{i+1}. {rating}/10{comment_text}\n"
        keyboard.append([InlineKeyboardButton(f"Eliminar valoración {i+1}", callback_data=f"delete_rating_{i}")])
    
    message += "\nSelecciona una valoración para eliminar:"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(message, reply_markup=reply_markup)
    
    return CONFIRM_DELETE

def confirm_delete_rating(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before deleting a rating."""
    query = update.callback_query
    query.answer()
    
    rating_index = int(query.data.replace("delete_rating_", ""))
    context.user_data["delete_rating_index"] = rating_index
    
    keyboard = [
        [InlineKeyboardButton("Sí, eliminar esta valoración", callback_data="confirm_delete_rating")],
        [InlineKeyboardButton("No, mantener esta valoración", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ ¿Estás seguro de que quieres eliminar la valoración #{rating_index + 1}?\n\n"
        "¡Esta acción no se puede deshacer!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_delete_rating(update: Update, context: CallbackContext) -> int:
    """Delete the selected rating after confirmation."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("delete_rating_list")
    item_name = context.user_data.get("delete_rating_item")
    rating_index = context.user_data.get("delete_rating_index")
    
    if not all([list_name, item_name, rating_index is not None]):
        query.edit_message_text("Algo salió mal. Por favor, inténtalo de nuevo con /deleterating")
        return ConversationHandler.END
    
    # Delete the rating
    success = data_store.delete_rating(user_id, list_name, item_name, rating_index)
    
    if success:
        query.edit_message_text(f"✅ La valoración #{rating_index + 1} para '{item_name}' ha sido eliminada.")
    else:
        query.edit_message_text(f"❌ No se pudo eliminar la valoración. Por favor, inténtalo de nuevo.")
    
    return ConversationHandler.END

# Clear ratings handlers
@admin_required
def clear_ratings_start(update: Update, context: CallbackContext) -> int:
    """Start the process of clearing all ratings for an item. Admin only."""
    user_id = str(update.effective_user.id)
    lists = data_store.get_all_lists(user_id)
    
    if not lists:
        update.message.reply_text(
            "Aún no tienes listas. Crea una primero con /newlist"
        )
        return ConversationHandler.END
    
    keyboard = []
    for list_name in lists:
        keyboard.append([InlineKeyboardButton(list_name, callback_data=f"clear_ratings_list_{list_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Selecciona una lista que contenga el elemento cuyas valoraciones quieres borrar:", reply_markup=reply_markup)
    
    return DELETE_RATING

def select_list_for_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Handle the list selection for clearing ratings."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = query.data.replace("clear_ratings_list_", "")
    context.user_data["clear_ratings_list"] = list_name
    
    items = data_store.get_list_items(user_id, list_name)
    
    # Filter only items with ratings
    items_with_ratings = {name: ratings for name, ratings in items.items() if ratings}
    
    if not items_with_ratings:
        query.edit_message_text(
            f"No hay valoraciones para borrar en la lista '{list_name}'."
        )
        return ConversationHandler.END
    
    keyboard = []
    for item_name in items_with_ratings:
        keyboard.append([InlineKeyboardButton(item_name, callback_data=f"clear_ratings_item_{item_name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"⚠️ Selecciona un elemento de '{list_name}' cuyas valoraciones quieres BORRAR:", reply_markup=reply_markup)
    
    return CONFIRM_DELETE

def confirm_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Ask for confirmation before clearing all ratings for an item."""
    query = update.callback_query
    query.answer()
    
    item_name = query.data.replace("clear_ratings_item_", "")
    context.user_data["clear_ratings_item"] = item_name
    
    keyboard = [
        [InlineKeyboardButton("Sí, borrar todas las valoraciones", callback_data="confirm_clear_ratings")],
        [InlineKeyboardButton("No, mantener las valoraciones", callback_data="cancel_delete")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⚠️ ¿Estás seguro de que quieres borrar TODAS las valoraciones para '{item_name}'?\n\n"
        "¡Esta acción no se puede deshacer!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_DELETE

def execute_clear_ratings(update: Update, context: CallbackContext) -> int:
    """Clear all ratings for the selected item after confirmation."""
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    list_name = context.user_data.get("clear_ratings_list")
    item_name = context.user_data.get("clear_ratings_item")
    
    if not all([list_name, item_name]):
        query.edit_message_text("Algo salió mal. Por favor, inténtalo de nuevo con /clearratings")
        return ConversationHandler.END
    
    # Clear all ratings for the item
    success = data_store.clear_ratings(user_id, list_name, item_name)
    
    if success:
        query.edit_message_text(f"✅ Todas las valoraciones para '{item_name}' han sido borradas.")
    else:
        query.edit_message_text(f"❌ No se pudieron borrar las valoraciones. Por favor, inténtalo de nuevo.")
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the current conversation."""
    update.message.reply_text(
        "Operación cancelada. ¿Qué más te gustaría hacer?"
    )
    return ConversationHandler.END
    
def setup_handlers(dispatcher):
    """Set up the Telegram bot handlers on an existing dispatcher."""
    # Basic command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("lists", show_lists))
    
    # Create list conversation
    create_list_handler = ConversationHandler(
        entry_points=[CommandHandler("newlist", new_list)],
        states={
            CREATE_LIST: [MessageHandler(Filters.text & ~Filters.command, create_list)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(create_list_handler)
    
    # Add item conversation
    add_item_handler = ConversationHandler(
        entry_points=[CommandHandler("additem", add_item_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(select_list_for_item, pattern=r"^add_to_")],
            ADD_ITEM: [MessageHandler(Filters.text & ~Filters.command, add_item_to_list)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(add_item_handler)
    
    # View list conversation
    view_list_handler = ConversationHandler(
        entry_points=[CommandHandler("viewlist", view_list_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(view_list_items, pattern=r"^view_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(view_list_handler)
    
    # Rate item conversation
    rate_item_handler = ConversationHandler(
        entry_points=[CommandHandler("rate", rate_item_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(select_list_for_rating, pattern=r"^rate_list_")],
            SELECTING_ITEM_TO_RATE: [CallbackQueryHandler(select_item_for_rating, pattern=r"^rate_item_")],
            RATE_ITEM: [CallbackQueryHandler(apply_rating, pattern=r"^give_rating_")],
            ADD_COMMENT: [
                MessageHandler(Filters.text & ~Filters.command, add_rating_comment),
                CommandHandler("skip", skip_comment),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(rate_item_handler)
    
    # View ratings conversation
    view_ratings_handler = ConversationHandler(
        entry_points=[CommandHandler("ratings", view_ratings_start)],
        states={
            SELECT_LIST: [CallbackQueryHandler(view_list_ratings, pattern=r"^ratings_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(view_ratings_handler)
    
    # Delete list conversation
    delete_list_handler = ConversationHandler(
        entry_points=[CommandHandler("deletelist", delete_list_start)],
        states={
            DELETE_LIST: [CallbackQueryHandler(confirm_delete_list, pattern=r"^delete_list_")],
            CONFIRM_DELETE: [
                CallbackQueryHandler(execute_delete_list, pattern=r"^confirm_delete_list$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel_delete$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(delete_list_handler)
    
    # Delete item conversation
    delete_item_handler = ConversationHandler(
        entry_points=[CommandHandler("deleteitem", delete_item_start)],
        states={
            DELETE_ITEM: [CallbackQueryHandler(select_list_for_delete_item, pattern=r"^delete_item_list_")],
            CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_delete_item, pattern=r"^delete_item_"),
                CallbackQueryHandler(execute_delete_item, pattern=r"^confirm_delete_item$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel_delete$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(delete_item_handler)
    
    # Delete rating conversation
    delete_rating_handler = ConversationHandler(
        entry_points=[CommandHandler("deleterating", delete_rating_start)],
        states={
            DELETE_RATING: [CallbackQueryHandler(select_list_for_delete_rating, pattern=r"^delete_rating_list_")],
            CONFIRM_DELETE: [
                CallbackQueryHandler(select_item_for_delete_rating, pattern=r"^delete_rating_item_"),
                CallbackQueryHandler(confirm_delete_rating, pattern=r"^delete_rating_\d+$"),
                CallbackQueryHandler(execute_delete_rating, pattern=r"^confirm_delete_rating$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel_delete$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(delete_rating_handler)
    
    # Clear ratings conversation
    clear_ratings_handler = ConversationHandler(
        entry_points=[CommandHandler("clearratings", clear_ratings_start)],
        states={
            DELETE_RATING: [CallbackQueryHandler(select_list_for_clear_ratings, pattern=r"^clear_ratings_list_")],
            CONFIRM_DELETE: [
                CallbackQueryHandler(confirm_clear_ratings, pattern=r"^clear_ratings_item_"),
                CallbackQueryHandler(execute_clear_ratings, pattern=r"^confirm_clear_ratings$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel_delete$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dispatcher.add_handler(clear_ratings_handler)
    
    # Fallback for cancel command outside of conversation
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    
    # Add fallback handler for unknown commands
    dispatcher.add_handler(MessageHandler(Filters.command, help_command))

def setup_bot():
    """Set up the Telegram bot with all handlers."""
    # Create the Updater
    token = os.environ.get('TELEGRAM_TOKEN')
    if not token:
        raise ValueError("No TELEGRAM_TOKEN environment variable found. Please set it and restart.")
    
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher
    
    # Set up all handlers
    setup_handlers(dispatcher)
    
    return updater