import logging
import time
import re
from typing import Dict, Any
from app.models.user import User
from app.services.sentiment_service import SentimentService

logger = logging.getLogger(__name__)

class DailyCheckinHandler:
    """Handler for daily check-in flow."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        
    def handle_daily_checkin(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle daily check-in flow."""
        try:
            # Get or create user
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Analyze sentiment if message is text
            if isinstance(message_text, str):
                analysis = self.sentiment.analyze_checkin_text(message_text)
                logger.info(f"Sentiment analysis for user {user_id}: {analysis}")
                
                needs_support = (
                    analysis.get('emotional_state') == 'negative' or
                    analysis.get('energy_level') == 'low' or
                    any(emotion in analysis.get('key_emotions', []) 
                        for emotion in ['overwhelmed', 'anxious', 'stressed'])
                )
            else:
                needs_support = False
                analysis = {}
            
            # Store check-in data
            context_updates = {
                'last_check_in': int(time.time()),
                'last_sentiment': analysis,
                'check_in_type': 'daily'
            }
            
            if needs_support:
                message = (
                    f"I hear you, {name}. Let's take it one step at a time today.\n\n"
                    "Would you like to:"
                )
                self.whatsapp.send_interactive_buttons(
                    user_id,
                    message,
                    [
                        {"id": "talk_feelings", "title": "Talk through feelings"},
                        {"id": "small_task", "title": "Try small task"},
                        {"id": "self_care", "title": "Self-care day"}
                    ]
                )
                self.task.update_user_state(
                    user_id, 'AWAITING_SUPPORT_CHOICE', instance_id, context_updates
                )
            else:
                # User is feeling good, ask for tasks
                message = (
                    f"Great energy, {name}! Let's plan your tasks for today.\n\n"
                    "Please list your tasks in this format:\n"
                    "1. [Your first task]\n"
                    "2. [Your second task]\n"
                    "3. [Your third task]\n\n"
                    "For example:\n"
                    "1. Review project documents\n"
                    "2. Send follow-up emails\n"
                    "3. Update task tracker"
                )
                self.whatsapp.send_message(user_id, message)
                self.task.update_user_state(
                    user_id, 'DAILY_TASK_INPUT', instance_id, context_updates
                )
            
        except Exception as e:
            logger.error(f"Error in daily check-in: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I encountered an error processing your check-in. Let's try again - how are you feeling?"
            )
            
    def handle_daily_task_input(self, user_id: str, message_text: str, instance_id: str, context: dict):
        """Handle daily task list input from user."""
        try:
            logger.info(f"Processing daily task input for user {user_id}")
            logger.info(f"Task input: {message_text}")
            
            # Get user info
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Parse tasks from the message
            tasks = []
            lines = message_text.strip().split('\n')
            for line in lines:
                # Remove any numbering, invisible characters, and leading/trailing whitespace
                task = re.sub(r'^\d+\.?\s*⁠?\s*', '', line).strip()
                if task:
                    tasks.append({
                        'task': task,
                        'status': 'pending',
                        'created_at': int(time.time())
                    })
            
            if not tasks:
                # If no valid tasks found, ask user to try again
                response = (
                    "I couldn't find any tasks in your message. Please list your tasks like this:\n\n"
                    "1. [Your first task]\n"
                    "2. [Your second task]\n"
                    "3. [Your third task]"
                )
                self.whatsapp.send_message(user_id, response)
                return
            
            # Store the tasks
            try:
                logger.info(f"Storing tasks for user {user_id}: {tasks}")
                self.task.store_daily_tasks(user_id, tasks, instance_id)
                
                # Format tasks for display
                task_list = "\n".join([f"{i}. {task['task']}" for i, task in enumerate(tasks, 1)])
                
                # Send confirmation with task update instructions
                response = (
                    f"Got it! I've saved your tasks for today:\n\n"
                    f"{task_list}\n\n"
                    "You can update your tasks using these commands:\n"
                    "• DONE [number] - Mark a task as complete\n"
                    "• PROGRESS [number] - Mark a task as in progress\n"
                    "• STUCK [number] - Let me know if you need help\n"
                    "• ADD [task] - Add a new task\n"
                    "• REMOVE [number] - Remove a task\n\n"
                    "I'll check in with you later to see how you're doing! 💪"
                )
                self.whatsapp.send_message(user_id, response)
                
                # Update user state
                context_updates = {
                    'daily_tasks': tasks,
                    'last_task_update': int(time.time())
                }
                self.task.update_user_state(
                    user_id,
                    'TASK_UPDATE',
                    instance_id,
                    context_updates
                )
                logger.info(f"Successfully stored tasks and updated state for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error storing daily tasks: {str(e)}")
                self.whatsapp.send_message(
                    user_id,
                    "I had trouble saving your tasks. Could you try sending them again?"
                )
                
        except Exception as e:
            logger.error(f"Error processing daily task input: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble understanding your task list. Please make sure it follows the format:\n\n"
                "1. [Your first task]\n"
                "2. [Your second task]\n"
                "3. [Your third task]"
            ) 