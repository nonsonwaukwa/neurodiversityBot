import os
import sys
from pathlib import Path
import json

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
    
    logger.info(f"Found {len(users)} users for morning check-in")
    
    # Group users by account
    users_by_account = {}
    for user in users:
        account_index = user.account_index
        if account_index not in users_by_account:
            users_by_account[account_index] = []
        users_by_account[account_index].append(user)
    
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
                if user.state == 'WEEKLY_REFLECTION':
                    logger.info(
                        f"User {user.user_id} is in weekly reflection state - "
                        "skipping daily check-in"
                    )
                    continue
                
                # Log emotional state if available
                if user.emotional_state:
                    logger.info(
                        f"User {user.user_id} - Current Emotional State: {user.emotional_state}, "
                        f"Energy Level: {user.energy_level}"
                    )
                
                # Handle based on planning type
                if user.planning_type == 'weekly':
                    logger.info(f"User {user.user_id} - Processing weekly plan check-in")
                    _send_weekly_plan_checkin(user, whatsapp_service, instance_id)
                else:
                    logger.info(f"User {user.user_id} - Processing daily plan check-in")
                    _send_daily_plan_checkin(user, whatsapp_service, instance_id)
                
                if response:
                    logger.info(f"Successfully sent morning check-in to user {user.user_id}")
                else:
                    logger.error(f"Failed to send morning check-in to user {user.user_id}")
                    
            except Exception as e:
                logger.error(
                    f"Error sending morning check-in to user {user.user_id}: {str(e)}",
                    exc_info=True
                )

def _send_weekly_plan_checkin(user, whatsapp_service, instance_id):
    """Send check-in for users on weekly planning."""
    name = user.name.split('_')[0] if '_' in user.name else user.name
    current_day = datetime.now().strftime("%A")
    tasks = user.weekly_tasks.get(current_day, [])
    
    logger.info(
        f"User {user.user_id} - Weekly Plan Check-in:\n"
        f"Current Day: {current_day}\n"
        f"Tasks Available: {bool(tasks)}\n"
        f"Number of Tasks: {len(tasks) if tasks else 0}"
    )
    
    if tasks:
        logger.info(f"User {user.user_id} - Today's Tasks:\n{json.dumps(tasks, indent=2)}")
    
    if not tasks:
        message = (
            f"Good morning {name}! 🌅\n\n"
            "I notice you don't have any tasks set for today. "
            "Would you like to plan some tasks for the day?\n\n"
            "Please list them like this:\n"
            "1. First task\n"
            "2. Second task\n"
            "3. Third task"
        )
        logger.info(f"User {user.user_id} - No tasks found, requesting new tasks")
    else:
        task_list = "\n".join(f"{i+1}. {task}" for i, task in enumerate(tasks))
        message = (
            f"Good morning {name}! 🌅\n\n"
            f"Here are your tasks for today:\n\n{task_list}\n\n"
            "How are you feeling about tackling these tasks? Share your thoughts with me, "
            "and I'll help you plan accordingly. 💭"
        )
        logger.info(f"User {user.user_id} - Displaying existing tasks and requesting feelings")
    
    response = whatsapp_service.send_message(user.user_id, message)
    
    # Store check-in and update user state
    checkin = CheckIn.create(user.user_id, message, CheckIn.TYPE_MORNING)
    user.update_user_state('DAILY_CHECK_IN')
    
    logger.info(
        f"User {user.user_id} - Check-in created:\n"
        f"Check-in ID: {checkin.id}\n"
        f"New State: DAILY_CHECK_IN"
    )

def _send_daily_plan_checkin(user, whatsapp_service, instance_id):
    """Send check-in for users on daily planning."""
    name = user.name.split('_')[0] if '_' in user.name else user.name
    
    # Log any focus task if it exists
    if user.focus_task:
        logger.info(
            f"User {user.user_id} - Has focus task:\n"
            f"Task: {user.focus_task}\n"
            f"Breakdown: {json.dumps(user.task_breakdown, indent=2) if user.task_breakdown else 'No breakdown'}"
        )
    
    # Log self-care day status
    if user.is_self_care_day:
        logger.info(f"User {user.user_id} - Currently on a self-care day")
    
    message = (
        f"Good morning {name}! 🌅\n\n"
        "How are you feeling today? Take a moment to check in with yourself. "
        "Your energy levels, mood, or any thoughts you'd like to share - "
        "it all helps me understand how to best support you. 💭\n\n"
        "You can send a voice note or text - whatever feels easier to express yourself with."
    )
    
    response = whatsapp_service.send_message(user.user_id, message)
    
    # Store check-in and update user state
    checkin = CheckIn.create(user.user_id, message, CheckIn.TYPE_MORNING)
    user.update_user_state('DAILY_CHECK_IN')
    
    logger.info(
        f"User {user.user_id} - Daily plan check-in created:\n"
        f"Check-in ID: {checkin.id}\n"
        f"New State: DAILY_CHECK_IN"
    )

if __name__ == "__main__":
    try:
        send_morning_checkin()
    except Exception as e:
        logger.error("Failed to run morning check-in", exc_info=True)
        raise 