import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
from app.services.sentiment import SentimentService
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
sentiment_service = SentimentService()

def send_weekly_checkin():
    """Send weekly check-in messages to all users to determine their planning schedule"""
    logger.info("Running weekly check-in cron job")
    
    users = User.get_all()
    
    if not users:
        logger.info("No users found for weekly check-in")
        return
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        whatsapp_service = get_whatsapp_service(account_index)
        
        for user in account_users:
            try:
                name = user.name.split('_')[0] if '_' in user.name else user.name
                
                # Get user's last week's sentiment data and tasks
                last_week_sentiment = user.get_last_week_sentiment()
                weekly_tasks = user.weekly_tasks
                
                # Build a personalized message
                message_parts = []
                
                # Add task-related reflection if they had weekly tasks
                if weekly_tasks:
                    completed_tasks = [task for task in weekly_tasks if task.get('status') == 'completed']
                    if completed_tasks:
                        message_parts.append(
                            "Looking back at last week, you made progress on some of your goals - "
                            "that's worth celebrating! Even small steps forward count. 🌟"
                        )
                    else:
                        message_parts.append(
                            "I noticed last week might have been challenging with the tasks we set. "
                            "That's completely okay - some weeks are harder than others. 💙"
                        )
                
                # Add main check-in message
                message_parts.append(
                    "How are you feeling about the week ahead? You can share anything - "
                    "your energy levels, any concerns, or what you're looking forward to. "
                    "This helps me understand how to best support you. 💭"
                )
                
                # Add context based on last week's state
                if last_week_sentiment and last_week_sentiment.get('stress_level') == 'high':
                    message_parts.append(
                        "I know last week felt pretty heavy. Remember, it's okay if you need to take things "
                        "slower or focus more on self-care. We'll figure out what feels manageable together. 💝"
                    )
                
                # Combine all parts
                checkin_message = (
                    f"Happy Sunday, {name}! 🌅\n\n" +
                    "\n\n".join(message_parts) +
                    "\n\nYou can send a voice note or text - whatever feels easier to express yourself with. "
                    "Based on how you're feeling, we'll find the right approach for the week ahead. 🌱"
                )
                
                logger.info(f"Sending weekly check-in to user {user.user_id}")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                # Store this message as a check-in and update user state
                CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_WEEKLY)
                user.update_user_state('WEEKLY_REFLECTION')
                
                if response:
                    logger.info(f"Successfully sent weekly check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send weekly check-in to user {user.user_id}")
                    
            except Exception as e:
                logger.error(f"Error sending weekly check-in to user {user.user_id}: {e}")

if __name__ == "__main__":
    try:
        send_weekly_checkin()
    except Exception as e:
        logger.error(f"Failed to run weekly check-in: {e}")
        raise 