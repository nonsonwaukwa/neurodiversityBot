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
from app.services.firebase import db
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
    
    # Get users from all instances
    users = []
    for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
        try:
            users_ref = db.collection('instances').document(instance_id).collection('users')
            instance_users = users_ref.stream()
            
            for user_doc in instance_users:
                try:
                    user_data = user_doc.to_dict()
                    account_index = int(instance_id.replace('instance', ''))
                    
                    # Create user object
                    user = User(
                        user_id=user_doc.id,
                        name=user_data.get('name', ''),
                        account_index=account_index
                    )
                    
                    # Set user properties from data
                    user.state = user_data.get('state')
                    user.planning_type = user_data.get('planning_schedule', 'daily')
                    user.context['weekly_tasks'] = user_data.get('weekly_tasks', {})
                    user.last_checkin = user_data.get('last_check_in')
                    
                    users.append(user)
                    logger.info(f"Loaded user {user_doc.id} from {instance_id}")
                    
                except Exception as e:
                    logger.error(f"Error loading user {user_doc.id} from {instance_id}: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error accessing instance {instance_id}: {str(e)}", exc_info=True)
            continue
    
    if not users:
        logger.info("No users found for morning check-in")
        return
    
    logger.info(f"Found {len(users)} users for morning check-in")
    
    # Group users by account
    users_by_account = {}
    for user in users:
        if user.account_index not in users_by_account:
            users_by_account[user.account_index] = []
        users_by_account[user.account_index].append(user)
    
    logger.info(f"Processing users across {len(users_by_account)} accounts")
    
    # Process each account
    for account_index, account_users in users_by_account.items():
        instance_id = f'instance{account_index}'
        whatsapp_service = get_whatsapp_service(instance_id)
        
        logger.info(f"Processing {len(account_users)} users for account {account_index}")
        
        for user in account_users:
            try:
                name = user.name.split('_')[0] if '_' in user.name else user.name
                logger.info(f"Processing user {user.user_id} ({name})")
                
                # Log user's current state and planning type
                logger.info(
                    f"User {user.user_id} - Current State: {user.state}, "
                    f"Planning Type: {user.planning_type}"
                )
                
                # Check if user already received check-in today
                last_checkin = user.last_checkin
                if last_checkin:
                    last_checkin_date = datetime.fromtimestamp(last_checkin).date()
                    if last_checkin_date == datetime.now().date():
                        logger.info(
                            f"User {user.user_id} already received check-in today at "
                            f"{datetime.fromtimestamp(last_checkin).strftime('%H:%M:%S')}"
                        )
                        continue
                
                # If user is in weekly reflection, don't interrupt
                if user.state == User.STATE_WEEKLY_REFLECTION:
                    logger.info(
                        f"User {user.user_id} is in weekly reflection state - "
                        "skipping daily check-in"
                    )
                    continue
                
                # Build personalized message
                message_parts = [
                    f"Good morning {name}! 🌅\n\n",
                    "How are you feeling today? Take a moment to check in with yourself. "
                    "Your energy levels, mood, or any thoughts you'd like to share - "
                    "it all helps me understand how to best support you. 💭\n\n",
                    "You can send a voice note or text - whatever feels easier to express yourself with."
                ]
                
                # Combine all parts
                checkin_message = "".join(message_parts)
                
                logger.info(f"Sending morning check-in to user {user.user_id}")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                if response:
                    # Store this message as a check-in and update user state
                    CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_MORNING)
                    user.update_user_state('DAILY_CHECK_IN')
                    logger.info(f"Successfully sent morning check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send morning check-in to user {user.user_id}")
                    
            except Exception as e:
                logger.error(
                    f"Error sending morning check-in to user {user.user_id}: {str(e)}",
                    exc_info=True
                )

if __name__ == "__main__":
    try:
        send_morning_checkin()
    except Exception as e:
        logger.error("Failed to run morning check-in", exc_info=True)
        raise 