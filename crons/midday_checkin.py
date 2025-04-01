import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp_service import get_whatsapp_service
from app.services.sentiment_service import SentimentService
from app.services.firebase import db
import logging
from datetime import datetime
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
sentiment_service = SentimentService()

def send_midday_checkin():
    """Send midday check-in messages to users with incomplete tasks"""
    logger.info("Running midday check-in cron job")
    
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
                    user.context['daily_tasks'] = user_data.get('daily_tasks', [])
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
        logger.info("No users found for midday check-in")
        return
    
    logger.info(f"Found {len(users)} users for midday check-in")
    
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
                
                # Get today's tasks based on planning type
                today_tasks = []
                if user.planning_type == User.PLANNING_TYPE_WEEKLY:
                    today = datetime.now().strftime('%A')
                    today_tasks = user.get_tasks_for_day(today)
                else:
                    today_tasks = user.daily_tasks
                
                # Filter incomplete tasks
                incomplete_tasks = [t for t in today_tasks if t.get('status', '') != 'completed']
                
                if incomplete_tasks:
                    # Send initial check-in message
                    initial_message = f"Hey {name}! 👋 How are your tasks coming along? Let me check in on each one:"
                    whatsapp_service.send_message(user.user_id, initial_message)
                    
                    # Send individual messages for each task with interactive buttons
                    for i, task in enumerate(incomplete_tasks, 1):
                        task_message = (
                            f"Task {i}: {task['task']}\n\n"
                            "How's this going? Use:\n"
                            "• DONE to mark as complete\n"
                            "• PROGRESS to mark as in progress\n"
                            "• STUCK if you need help"
                        )
                        whatsapp_service.send_interactive_message(
                            user.user_id,
                            task_message,
                            [
                                {"id": f"done_{i}", "title": "Done ✅"},
                                {"id": f"progress_{i}", "title": "In Progress 🔄"},
                                {"id": f"stuck_{i}", "title": "Stuck ❓"}
                            ]
                        )
                    
                    # Store check-in in database
                    CheckIn.create(
                        user.user_id,
                        "midday_checkin",
                        CheckIn.TYPE_MIDDAY,
                        {
                            'incomplete_tasks': len(incomplete_tasks),
                            'total_tasks': len(today_tasks),
                            'timestamp': int(time.time())
                        }
                    )
                    
                    # Update user state
                    user_ref = db.collection('instances').document(instance_id).collection('users').document(user.user_id)
                    user_ref.update({
                        'last_check_in': int(time.time()),
                        'state': 'TASK_UPDATE',
                        'context.current_checkin_source': 'midday'
                    })
                    
                    logger.info(f"Sent midday check-in to user {user.user_id} for {len(incomplete_tasks)} tasks")
                else:
                    # All tasks completed
                    congrats_message = (
                        f"Amazing work {name}! 🎉\n\n"
                        "I see you've completed all your tasks for today! "
                        "That's fantastic progress. Would you like to:\n\n"
                        "1. Add more tasks for today\n"
                        "2. Start planning for tomorrow\n"
                        "3. Take some time to reflect on your achievements"
                    )
                    whatsapp_service.send_message(user.user_id, congrats_message)
                    logger.info(f"User {user.user_id} has completed all tasks")
                
            except Exception as e:
                logger.error(f"Error in midday check-in for user {user.user_id}: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        send_midday_checkin()
    except Exception as e:
        logger.error("Failed to run midday check-in", exc_info=True)
        raise 