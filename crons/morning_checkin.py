import os
import sys

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.models.user import User
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        whatsapp_service = get_whatsapp_service(account_index)
        
        for user in account_users:
            try:
                name = user.name.split('_')[0] if '_' in user.name else user.name
                
                checkin_message = (
                    f"Good morning {name}! 👋\n\n"
                    "How are you feeling today? Energetic, tired, somewhere in between? "
                    "No right answers here - just meeting you where you are! 💭"
                )
                
                logger.info(f"Sending morning check-in to user {user.user_id}")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                # Store this message as a check-in
                CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_MORNING)
                
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