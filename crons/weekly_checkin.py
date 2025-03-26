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
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
sentiment_service = SentimentService()

def send_weekly_checkin():
    """Send weekly check-in messages to all users"""
    logger.info("Running weekly check-in cron job")
    
    # Get users from all instances
    users = []
    for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
        try:
            users_ref = db.collection('instances').document(instance_id).collection('users')
            instance_users = users_ref.stream()
            
            for user_doc in instance_users:
                try:
                    user_data = user_doc.to_dict()
                    if not user_data:
                        logger.warning(f"No data found for user {user_doc.id} in {instance_id}")
                        continue
                        
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
                    user.last_weekly_checkin = user_data.get('last_weekly_checkin')
                    user.last_week_sentiment = user_data.get('last_week_sentiment')
                    
                    users.append(user)
                    logger.info(f"Loaded user {user_doc.id} from {instance_id}")
                    
                except Exception as e:
                    logger.error(f"Error loading user {user_doc.id} from {instance_id}: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error accessing instance {instance_id}: {str(e)}", exc_info=True)
            continue
    
    if not users:
        logger.info("No users found for weekly check-in")
        return
    
    logger.info(f"Found {len(users)} users for weekly check-in")
    
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
                
                # Check if user needs weekly check-in
                current_time = int(datetime.now().timestamp())
                last_weekly = user.last_weekly_checkin
                
                if last_weekly:
                    try:
                        # Convert string to int if needed
                        if isinstance(last_weekly, str):
                            last_weekly = int(last_weekly)
                            
                        last_weekly_date = datetime.fromtimestamp(last_weekly).date()
                        days_since_last = (datetime.now().date() - last_weekly_date).days
                        
                        if days_since_last < 7:
                            logger.info(
                                f"User {user.user_id} last weekly check-in was {days_since_last} days ago. "
                                "Skipping weekly check-in."
                            )
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Invalid timestamp for user {user.user_id}: {last_weekly}. "
                            "Proceeding with check-in."
                        )
                
                # Build personalized message
                message_parts = [
                    f"Hi {name}! 🌟\n\n",
                    "It's time for our weekly check-in! How has your week been? "
                    "Take a moment to reflect on:\n\n",
                    "• Your achievements and progress\n",
                    "• Any challenges you faced\n",
                    "• How you're feeling overall\n\n",
                    "Share your thoughts with me, and I'll help you plan for the week ahead. 💭"
                ]
                
                # Combine all parts
                checkin_message = "".join(message_parts)
                
                logger.info(f"Sending weekly check-in to user {user.user_id}")
                response = whatsapp_service.send_message(user.user_id, checkin_message)
                
                if response:
                    # Store this message as a check-in and update user state
                    CheckIn.create(user.user_id, checkin_message, CheckIn.TYPE_WEEKLY)
                    user.update_user_state(User.STATE_WEEKLY_REFLECTION)
                    logger.info(f"Successfully sent weekly check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send weekly check-in to user {user.user_id}")
                    
            except Exception as e:
                logger.error(
                    f"Error sending weekly check-in to user {user.user_id}: {str(e)}",
                    exc_info=True
                )

if __name__ == "__main__":
    try:
        send_weekly_checkin()
    except Exception as e:
        logger.error("Failed to run weekly check-in", exc_info=True)
        raise 