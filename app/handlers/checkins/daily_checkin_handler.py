import logging
import time
import re
from typing import Dict, Any
from app.models.user import User
from app.services.sentiment_service import SentimentService
from datetime import datetime

logger = logging.getLogger(__name__)

class DailyCheckinHandler:
    """Handler for daily check-ins and task management."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        # Message deduplication cache
        self._message_cache = {}
        
    def _is_duplicate_message(self, message_id: str, user_id: str) -> bool:
        """Check if a message has already been processed."""
        cache_key = f"{user_id}:{message_id}"
        if cache_key in self._message_cache:
            logger.info(f"Duplicate message detected: {message_id} for user {user_id}")
            return True
        self._message_cache[cache_key] = int(time.time())
        return False
        
    def _clean_message_cache(self):
        """Remove messages older than 5 minutes from the cache."""
        current_time = int(time.time())
        expired_keys = [
            key for key, timestamp in self._message_cache.items()
            if current_time - timestamp > 300  # 5 minutes in seconds
        ]
        for key in expired_keys:
            del self._message_cache[key]
        
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
                analysis = self.sentiment.analyze_sentiment(message_text)
                logger.info(f"Sentiment analysis for user {user_id}: {analysis}")
                
                needs_support = (
                    analysis.get('emotional_state') == 'negative' or
                    analysis.get('energy_level') == 'low' or
                    analysis.get('support_needed') == 'high' or
                    'overwhelm' in analysis.get('key_emotions', []) or
                    'stress' in analysis.get('key_emotions', [])
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
                    f"I hear you're feeling overwhelmed and stressed, {name}. That's completely valid and it's good that you're expressing this. 🫂\n\n"
                    "Let's take a step back and focus on your wellbeing first. Would you like to:"
                )
                self.whatsapp.send_interactive_buttons(
                    user_id,
                    message,
                    [
                        {"id": "talk_feelings", "title": "Talk feelings"},
                        {"id": "small_task", "title": "Try small task"},
                        {"id": "self_care", "title": "Self-care day"}
                    ]
                )
                self.task.update_user_state(
                    user_id, 'AWAITING_SUPPORT_CHOICE', instance_id, context_updates
                )
            else:
                # Get today's tasks from weekly plan if available
                today = datetime.now().strftime('%A')
                tasks = self.task.get_weekly_tasks(user_id, instance_id, today)
                
                if tasks:
                    # Show today's tasks from weekly plan
                    task_list = "\n".join([f"{i}. {task['task']}" for i, task in enumerate(tasks, 1)])
                    message = (
                        f"Great energy, {name}! Here are your tasks for today:\n\n"
                        f"{task_list}\n\n"
                        "You can update your tasks using these commands:\n"
                        "• DONE [number] - Mark a task as complete\n"
                        "• PROGRESS [number] - Mark a task as in progress\n"
                        "• STUCK [number] - Let me know if you need help\n"
                        "• ADD [task] - Add a new task\n"
                        "• REMOVE [number] - Remove a task\n\n"
                        "Let's make today productive! 💪"
                    )
                    self.whatsapp.send_message(user_id, message)
                    self.task.update_user_state(
                        user_id, 'TASK_UPDATE', instance_id, context_updates
                    )
                else:
                    # Ask for tasks if none found in weekly plan
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
            
    def handle_daily_task_input(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle daily task input."""
        try:
            # Clean old cache entries
            self._clean_message_cache()
            
            # Check for duplicate message if it's an interactive message
            if isinstance(message_text, dict):
                message_id = message_text.get('message_id')
                if message_id and self._is_duplicate_message(message_id, user_id):
                    logger.info(f"Skipping duplicate message {message_id} for user {user_id}")
                    return
            
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
            
    def handle_support_choice(self, message_text: str, user_id: str, instance_id: str, context: dict) -> None:
        """Handle user's choice when they're feeling overwhelmed or need support."""
        try:
            # Get user info
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Handle button response
            if (isinstance(message_text, dict) and 
                message_text.get('type') == 'interactive' and 
                message_text.get('interactive', {}).get('type') == 'button_reply'):
                
                button_id = message_text['interactive']['button_reply']['id']
                
                if button_id == 'self_care':
                    response = (
                        f"Taking a self-care day is a wise choice, {name}. 💙\n\n"
                        "Remember, rest is productive too. It helps you recharge and come back stronger.\n\n"
                        "Would you like some gentle self-care suggestions for today?"
                    )
                    self.task.update_user_state(user_id, 'SELF_CARE_DAY', instance_id)
                    
                elif button_id == 'talk_feelings':
                    response = (
                        f"I'm here to listen, {name}. Sometimes just talking about what's on your mind can help.\n\n"
                        "What's been weighing on you?"
                    )
                    self.task.update_user_state(user_id, 'THERAPEUTIC_CONVERSATION', instance_id)
                    
                elif button_id == 'small_task':
                    response = (
                        f"That's a great approach, {name}! Small steps can make a big difference.\n\n"
                        "What's one tiny task you feel you could manage today? It could be as simple as making your bed or drinking a glass of water."
                    )
                    self.task.update_user_state(user_id, 'SMALL_TASK_INPUT', instance_id)
                    
                self.whatsapp.send_message(user_id, response)
                
            else:
                # Default response if not a button interaction
                self.whatsapp.send_interactive_buttons(
                    user_id,
                    f"I understand you're feeling overwhelmed, {name}. Let's handle this together. What would help you most right now?",
                    [
                        {"id": "self_care", "title": "Take a self-care day"},
                        {"id": "talk_feelings", "title": "Talk about feelings"},
                        {"id": "small_task", "title": "Pick a small task"}
                    ]
                )
                
        except Exception as e:
            logger.error(f"Error handling support choice: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I'm having trouble processing your choice. Could you try selecting an option again?"
            )

    def handle_small_task_input(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle small task input when user is feeling overwhelmed."""
        try:
            logger.info(f"Processing small task input for user {user_id}")
            
            # Get user info
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Store the task
            task_data = {
                'task': message_text,
                'status': 'pending',
                'created_at': int(time.time()),
                'type': 'small_task'
            }
            
            try:
                self.task.store_daily_tasks(user_id, [task_data], instance_id)
                
                # Generate empathetic response
                response = (
                    "That's perfect - getting enough rest is so important, especially when things feel overwhelming. 💜\n\n"
                    "I've noted this as your focus for today. Remember, it's completely okay to take things slow and "
                    "prioritize your wellbeing. I'll check in with you later to see how you're doing.\n\n"
                    "Is there anything else you need support with?"
                )
                
                # Send response and update state
                self.whatsapp.send_message(user_id, response)
                
                # Update context with the task
                context_updates = {
                    'daily_tasks': [task_data],
                    'last_task_update': int(time.time())
                }
                self.task.update_user_state(user_id, 'DAILY_CHECK_IN', instance_id, context_updates)
                
            except Exception as e:
                logger.error(f"Error storing small task: {str(e)}")
                self.whatsapp.send_message(
                    user_id,
                    "I'm having trouble saving your task. Could you try sharing it with me again?"
                )
                
        except Exception as e:
            logger.error(f"Error processing small task input: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble understanding your task. Could you try sharing it again?"
            )
            
    def handle_daily_reflection(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle daily reflection."""
        try:
            # Clean old cache entries
            self._clean_message_cache()
            
            # Check for duplicate message if it's an interactive message
            if isinstance(message_text, dict):
                message_id = message_text.get('message_id')
                if message_id and self._is_duplicate_message(message_id, user_id):
                    logger.info(f"Skipping duplicate message {message_id} for user {user_id}")
                    return
                    
        except Exception as e:
            logger.error(f"Error in daily reflection: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I encountered an error processing your reflection. Let's try again."
            ) 