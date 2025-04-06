import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataStore:
    """
    In-memory data storage for the Telegram bot.
    Stores user lists and item ratings with comments.
    
    Data structure:
    {
        user_id: {
            list_name: {
                item_name: [(rating, comment)]
            }
        }
    }
    """
    
    def __init__(self):
        # Initialize empty data store
        self.data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        logger.debug("DataStore initialized")
    
    def create_list(self, user_id: str, list_name: str) -> None:
        """
        Create a new empty list for a user.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list to create
        """
        # Since we're using defaultdict, we only need to ensure it exists
        if list_name not in self.data[user_id]:
            self.data[user_id][list_name] = defaultdict(list)
            logger.debug(f"Created list '{list_name}' for user {user_id}")
    
    def list_exists(self, user_id: str, list_name: str) -> bool:
        """
        Check if a list exists for a user.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list to check
            
        Returns:
            bool: True if list exists, False otherwise
        """
        return list_name in self.data[user_id]
    
    def get_all_lists(self, user_id: str) -> List[str]:
        """
        Get all list names for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List[str]: List of list names
        """
        return list(self.data[user_id].keys())
    
    def add_item(self, user_id: str, list_name: str, item_name: str) -> None:
        """
        Add an item to a list.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item to add
        """
        # Make sure the list exists
        if not self.list_exists(user_id, list_name):
            self.create_list(user_id, list_name)
        
        # Add the item (with empty ratings list)
        if item_name not in self.data[user_id][list_name]:
            self.data[user_id][list_name][item_name] = []
            logger.debug(f"Added item '{item_name}' to list '{list_name}' for user {user_id}")
    
    def item_exists(self, user_id: str, list_name: str, item_name: str) -> bool:
        """
        Check if an item exists in a list.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item to check
            
        Returns:
            bool: True if item exists, False otherwise
        """
        return list_name in self.data[user_id] and item_name in self.data[user_id][list_name]
    
    def get_list_items(self, user_id: str, list_name: str) -> Dict[str, List[Tuple[int, str]]]:
        """
        Get all items and their ratings from a list.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            
        Returns:
            Dict[str, List[Tuple[int, str]]]: Dictionary of item names to ratings and comments
        """
        if not self.list_exists(user_id, list_name):
            return {}
        
        return dict(self.data[user_id][list_name])
    
    def add_rating(self, user_id: str, list_name: str, item_name: str, rating: int, comment: str = "") -> None:
        """
        Add a rating with an optional comment to an item.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item
            rating: Rating value (0-10)
            comment: Optional comment for the rating
        """
        if not self.item_exists(user_id, list_name, item_name):
            logger.warning(f"Attempted to rate non-existent item '{item_name}' in list '{list_name}'")
            return
        
        # Validate rating
        if not (0 <= rating <= 10):
            logger.warning(f"Invalid rating value: {rating}. Must be between 0 and 10.")
            return
        
        # Add the rating with comment
        self.data[user_id][list_name][item_name].append((rating, comment))
        logger.debug(f"Added rating {rating} with comment '{comment}' to item '{item_name}' in list '{list_name}' for user {user_id}")
    
    def get_item_ratings(self, user_id: str, list_name: str, item_name: str) -> List[Tuple[int, str]]:
        """
        Get all ratings and comments for an item.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item
            
        Returns:
            List[Tuple[int, str]]: List of ratings and comments for the item
        """
        if not self.item_exists(user_id, list_name, item_name):
            return []
        
        return self.data[user_id][list_name][item_name]
        
    def get_average_rating(self, user_id: str, list_name: str, item_name: str) -> float:
        """
        Get the average rating for an item.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item
            
        Returns:
            float: Average rating for the item or 0 if no ratings
        """
        ratings = self.get_item_ratings(user_id, list_name, item_name)
        if not ratings:
            return 0
            
        # Extract just the rating values (first item in each tuple)
        rating_values = [r[0] for r in ratings]
        return sum(rating_values) / len(rating_values)
        
    def delete_list(self, user_id: str, list_name: str) -> bool:
        """
        Delete a list and all its items.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list to delete
            
        Returns:
            bool: True if list was deleted, False if it didn't exist
        """
        if not self.list_exists(user_id, list_name):
            return False
            
        del self.data[user_id][list_name]
        logger.debug(f"Deleted list '{list_name}' for user {user_id}")
        return True
        
    def delete_item(self, user_id: str, list_name: str, item_name: str) -> bool:
        """
        Delete an item from a list.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item to delete
            
        Returns:
            bool: True if item was deleted, False if it didn't exist
        """
        if not self.item_exists(user_id, list_name, item_name):
            return False
            
        del self.data[user_id][list_name][item_name]
        logger.debug(f"Deleted item '{item_name}' from list '{list_name}' for user {user_id}")
        return True
        
    def delete_rating(self, user_id: str, list_name: str, item_name: str, rating_index: int) -> bool:
        """
        Delete a specific rating from an item.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item
            rating_index: Index of the rating to delete (0-based)
            
        Returns:
            bool: True if rating was deleted, False if it didn't exist
        """
        if not self.item_exists(user_id, list_name, item_name):
            return False
            
        ratings = self.data[user_id][list_name][item_name]
        if rating_index < 0 or rating_index >= len(ratings):
            return False
            
        del ratings[rating_index]
        logger.debug(f"Deleted rating at index {rating_index} from item '{item_name}' in list '{list_name}' for user {user_id}")
        return True
        
    def clear_ratings(self, user_id: str, list_name: str, item_name: str) -> bool:
        """
        Clear all ratings for an item.
        
        Args:
            user_id: Telegram user ID
            list_name: Name of the list
            item_name: Name of the item
            
        Returns:
            bool: True if ratings were cleared, False if item didn't exist
        """
        if not self.item_exists(user_id, list_name, item_name):
            return False
            
        self.data[user_id][list_name][item_name] = []
        logger.debug(f"Cleared all ratings for item '{item_name}' in list '{list_name}' for user {user_id}")
        return True
