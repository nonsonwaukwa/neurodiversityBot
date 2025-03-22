import os
import sys

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.models.user import User
from app.models.task import Task
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

def send_evening_wrapup():
    """Send evening wrap-up messages to all users"""
    logger.info("Running evening wrap-up cron job")
    
    users = User.get_all()
    
    if not users:
        logger.info("No users found for evening wrap-up")
        return
    
    for user in users:
        try:
            whatsapp_service = get_whatsapp_service(user.account_index)
            
            # Get today's tasks
            today_tasks = Task.get_tasks_for_date(user.user_id, datetime.now())
            
            if today_tasks:
                completed_tasks = [t for t in today_tasks if t.status == 'completed']
                incomplete_tasks = [t for t in today_tasks if t.status != 'completed']
                
                completion_rate = len(completed_tasks) / len(today_tasks) * 100
                
                if incomplete_tasks:
                    task_list = "\n".join([f"• {t.description}" for t in incomplete_tasks])
                    message = (
                        "👋 Just checking in before the day wraps up!\n\n"
                        f"You've completed {len(completed_tasks)} out of {len(today_tasks)} tasks "
                        f"({completion_rate:.0f}% completion rate)\n\n"
                        f"Still on your list:\n{task_list}\n\n"
                        "Would you like to:\n"
                        "1. Update any task status?\n"
                        "2. Move them to tomorrow?\n"
                        "3. Chat about what made today challenging?"
                    )
                else:
                    message = (
                        "🌟 Amazing job today!\n\n"
                        f"You've completed all {len(today_tasks)} tasks - "
                        "that's worth celebrating!\n\n"
                        "Would you like to set up tasks for tomorrow?"
                    )
                
                response = whatsapp_service.send_message(user.user_id, message)
                CheckIn.create(user.user_id, message, CheckIn.TYPE_EVENING)
                
                logger.info(f"Sent evening wrap-up to user {user.user_id}")
                
        except Exception as e:
            logger.error(f"Error in evening wrap-up for user {user.user_id}: {e}")

if __name__ == "__main__":
    try:
        send_evening_wrapup()
    except Exception as e:
        logger.error(f"Failed to run evening wrap-up: {e}")
        raise 