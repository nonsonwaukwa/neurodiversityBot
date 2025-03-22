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

def send_midday_checkin():
    """Send midday check-in messages to users with incomplete tasks"""
    logger.info("Running midday check-in cron job")
    
    users = User.get_all()
    
    if not users:
        logger.info("No users found for midday check-in")
        return
    
    for user in users:
        try:
            # Get today's tasks for user
            today_tasks = Task.get_tasks_for_date(user.user_id, datetime.now())
            
            # Only send check-in if there are incomplete tasks
            incomplete_tasks = [t for t in today_tasks if t.status != 'completed']
            
            if incomplete_tasks:
                whatsapp_service = get_whatsapp_service(user.account_index)
                
                task_list = "\n".join([f"• {t.description}" for t in incomplete_tasks])
                
                message = (
                    "👋 Checking in on your tasks!\n\n"
                    f"Here's what's still on your list:\n{task_list}\n\n"
                    "How's it going? You can:\n"
                    "• Type 'DONE X' to mark task X complete\n"
                    "• 'STUCK X' if you need support with task X\n"
                    "• 'CHAT' if you'd like to talk through anything\n\n"
                    "Remember, any progress is good progress! 💫"
                )
                
                response = whatsapp_service.send_message(user.user_id, message)
                CheckIn.create(user.user_id, message, CheckIn.TYPE_MIDDAY)
                
                logger.info(f"Sent midday check-in to user {user.user_id}")
                
        except Exception as e:
            logger.error(f"Error in midday check-in for user {user.user_id}: {e}")

if __name__ == "__main__":
    try:
        send_midday_checkin()
    except Exception as e:
        logger.error(f"Failed to run midday check-in: {e}")
        raise 