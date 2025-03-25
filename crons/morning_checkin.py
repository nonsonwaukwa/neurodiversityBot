import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp_service import get_whatsapp_service
from app.services.sentiment_service import SentimentService
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
sentiment_service = SentimentService()

def send_morning_checkin():
    """Send morning energy check-in messages to all users"""
    logger.info("Running morning check-in cron job")
    
    users = User.get_all()
    
    if not users:
        logger.info("No users found for morning check-in")
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
        instance_id = f'instance{account_index}'
        whatsapp_service = get_whatsapp_service(instance_id)
        
        for user in account_users:
            try:
                name = user.name.split('_')[0] if '_' in user.name else user.name
                
                # Check if user already received check-in today
                last_checkin = user.last_checkin
                if last_checkin:
                    last_checkin_date = datetime.fromtimestamp(last_checkin).date()
                    if last_checkin_date == datetime.now().date():
                        logger.info(f"User {user.user_id} already received check-in today")
                        continue
                
                # Build personalized message
                message_parts = [
                    f"Good morning {name}! 🌅\n\n",
                    "How are you feeling today? Take a moment to check in with yourself. "
                    "Your energy levels, mood, or any thoughts you'd like to share - "
                    "it all helps me understand how to best support you. 💭\n\n",
                    "You can send a voice note or text - whatever feels easier to express yourself with."
                ]
                
                # Add context based on user's state
                if user.current_state == 'WEEKLY_REFLECTION':
                    message_parts.append(
                        "\nI see you're in the middle of your weekly reflection. "
                        "Take your time with that - we can come back to the daily check-in later."
                    )
                
                # Combine all parts
                checkin_message = "\n".join(message_parts)
                
                logger.info(f"Sending morning check-in to user {user.user_id}")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                # Store this message as a check-in and update user state
                CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_MORNING)
                user.update_user_state('DAILY_CHECK_IN')
                
                if response:
                    logger.info(f"Successfully sent morning check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send morning check-in to user {user.user_id}")
                    
            except Exception as e:
                logger.error(f"Error sending morning check-in to user {user.user_id}: {e}")

if __name__ == "__main__":
    try:
        send_morning_checkin()
    except Exception as e:
        logger.error(f"Failed to run morning check-in: {e}")
        raise 