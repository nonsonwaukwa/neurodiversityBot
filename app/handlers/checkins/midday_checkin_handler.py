import logging
import time
from typing import Dict, Any
from app.models.user import User

logger = logging.getLogger(__name__)

class MiddayCheckinHandler:
    """Handler for midday check-ins and task status updates."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service, task_handler):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        self.task_handler = task_handler
        
    def handle_midday_checkin(self, user_id: str, message_text: str, instance_id: str, context: dict):
        """Handle midday check-in response."""
        try:
            logger.info(f"Processing midday check-in for user {user_id}")
            
            # Get user info
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Check if this is a task status update
            if isinstance(message_text, str):
                # Try to handle as task command first
                command_match = re.match(r'^(DONE|PROGRESS|STUCK)\s+(\d+)$', message_text.strip().upper())
                if command_match:
                    response = self.task_handler.handle_task_command(user_id, command_match, instance_id)
                    self.whatsapp.send_message(user_id, response)
                    return
            
            # If not a task command, handle as general check-in
            response = self.task_handler.handle_check_in(user_id, message_text, instance_id)
            self.whatsapp.send_message(user_id, response)
            
            # Update check-in context
            context_updates = {
                'last_midday_checkin': int(time.time()),
                'checkin_count': context.get('checkin_count', 0) + 1
            }
            
            # If this is the first check-in of the day, set next check-in time
            if context.get('checkin_count', 0) == 0:
                context_updates['next_checkin'] = 'evening'
            
            self.task.update_user_state(
                user_id,
                'MIDDAY_CHECK_IN',
                instance_id,
                context_updates
            )
            
            logger.info(f"Successfully processed midday check-in for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in midday check-in: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble processing your check-in. Could you try again?"
            )
            
    def handle_midday_button_response(self, user_id: str, button_data: dict, instance_id: str):
        """Handle interactive button responses during midday check-in."""
        try:
            logger.info(f"Processing midday button response for user {user_id}")
            
            button_id = button_data['button_reply']['id']
            
            # Extract task number from button ID (e.g., 'done_1', 'progress_2', 'stuck_3')
            task_num = int(button_id.split('_')[1]) - 1  # Convert to 0-based index
            command_type = button_id.split('_')[0].upper()
            
            # Create a command match object similar to what we get from regex
            class CommandMatch:
                def __init__(self, command_type, task_num):
                    self.group = lambda n: command_type if n == 1 else str(task_num + 1)
            
            command_match = CommandMatch(command_type, task_num)
            
            # Use task handler to process the command
            response = self.task_handler.handle_task_command(user_id, command_match, instance_id)
            self.whatsapp.send_message(user_id, response)
            
            # Update check-in context
            context_updates = {
                'last_midday_checkin': int(time.time()),
                'checkin_count': context.get('checkin_count', 0) + 1
            }
            
            self.task.update_user_state(
                user_id,
                'MIDDAY_CHECK_IN',
                instance_id,
                context_updates
            )
            
            logger.info(f"Successfully processed midday button response for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in midday button response: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble processing your response. Could you try again?"
            ) 