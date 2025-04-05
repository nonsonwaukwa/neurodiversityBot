import logging
import time
import re
import random
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
                    response = self.handle_check_in(user_id, message_text, instance_id)
                    self.whatsapp.send_message(user_id, response)
                    return
            
            # If not a task command, handle as general check-in
            response = self.handle_check_in(user_id, message_text, instance_id)
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

    def handle_check_in(self, user_id: str, message_text: str, instance_id: str) -> str:
        """Handle user's check-in response and task status updates."""
        # Extract text if message_text is a dict (interactive message)
        if isinstance(message_text, dict):
            message_text = message_text['interactive']['button_reply']['title']
        
        # Check for task status updates
        status_match = re.match(r'(DONE|PROGRESS|STUCK)\s+(\d+)', message_text.upper())
        if status_match:
            status_type = status_match.group(1)
            task_num_str = status_match.group(2)
            
            try:
                task_num = int(task_num_str) - 1  # Convert to 0-based index
                
                # Get current tasks to validate task number
                tasks = self.task.get_daily_tasks(user_id, instance_id)
                if task_num < 0 or task_num >= len(tasks):
                    return f"Hmm, I don't see task #{task_num_str} on your list. Want to try again or type 'TASKS' to see your current list?"
                
                # Get the task name for personalized response
                task_name = tasks[task_num]['task']
                
                status_map = {
                    'DONE': 'completed',
                    'PROGRESS': 'in_progress',
                    'STUCK': 'stuck'
                }
                
                self.task.update_task_status(user_id, task_num, status_map[status_type], instance_id)
                
                if status_type == 'DONE':
                    # Vary responses to avoid repetition
                    responses = [
                        f"🎉 Yes! You completed '{task_name}'! That's a genuine win - how did it feel to finish that one?",
                        f"✨ Amazing job finishing '{task_name}'! What helped you get this done today?",
                        f"💪 '{task_name}' → DONE! That's awesome progress. Would you like to take a moment to celebrate?"
                    ]
                    return random.choice(responses)
                elif status_type == 'PROGRESS':
                    responses = [
                        f"👍 Thanks for letting me know you're working on '{task_name}'. Taking those first steps can be the hardest part!",
                        f"🔄 Got it - '{task_name}' is in progress. Remember, consistent effort matters more than perfect execution.",
                        f"⏳ '{task_name}' in progress - that's great! Is there anything that would make this task flow better for you?"
                    ]
                    return random.choice(responses)
                else:  # STUCK
                    return (
                        f"I hear you're feeling stuck with '{task_name}'. That happens to everyone, especially with complicated or less interesting tasks.\n\n"
                        f"Would you like to:\n"
                        f"1. Break this down into smaller steps?\n"
                        f"2. Talk about what specific part feels challenging?\n"
                        f"3. Get some motivation or a different approach?\n"
                        f"4. Set this aside for now and come back to it later?"
                    )
            except ValueError:
                return "I didn't quite catch which task number you meant. Could you try again with something like 'DONE 1' or 'STUCK 2'?"
        
        # If we get here, it's a general message during CHECK_IN state
        # Analyze sentiment to provide an empathetic response
        sentiment = self.sentiment.analyze_sentiment(message_text)
        
        # Get current tasks
        tasks = self.task.get_daily_tasks(user_id, instance_id)
        completed = sum(1 for task in tasks if task.get('status') == 'completed')
        
        # Create a contextual response based on progress and sentiment
        if not tasks:
            return "We haven't set any tasks for today yet. Would you like to share what you'd like to focus on?"
        
        # Format task list with status indicators
        task_list = '\n'.join([
            f"{i+1}. {'✅' if task['status'] == 'completed' else '⭐'} {task['task']}" 
            for i, task in enumerate(tasks)
        ])
        
        # Varied responses based on progress
        if completed == 0:
            if sentiment.get('sentiment') == 'negative':
                return (
                    f"I hear things might be tough right now. That's okay - some days are harder than others.\n\n"
                    f"Here are your tasks when you're ready:\n\n{task_list}\n\n"
                    f"Even small progress counts. Is there something specific making today challenging?"
                )
            else:
                return (
                    f"Here's what we're focusing on today:\n\n{task_list}\n\n"
                    f"How's it going so far? Remember, you can update me anytime with 'DONE', 'PROGRESS', or 'STUCK'."
                )
        elif completed == len(tasks):
            return (
                f"🎊 Wow! You've completed all your tasks!\n\n{task_list}\n\n"
                f"That's seriously impressive. How are you feeling about what you've accomplished? Would you like to set any new goals or take some well-deserved rest?"
            )
        else:
            return (
                f"Here's where things stand:\n\n{task_list}\n\n"
                f"You've completed {completed}/{len(tasks)} tasks - that's progress to be proud of! How are you feeling about the rest? Anything I can help with?"
            )
            
    def handle_midday_button_response(self, user_id: str, button_data: dict, instance_id: str, context: dict):
        """Handle interactive button responses during midday check-in."""
        try:
            # Clean old cache entries
            self._clean_message_cache()
            
            # Check for duplicate message if it's an interactive message
            if isinstance(button_data, dict):
                message_id = button_data.get('id')
                if message_id and self._is_duplicate_message(message_id, user_id):
                    logger.info(f"Skipping duplicate message {message_id} for user {user_id}")
                    return
            
            logger.info(f"Processing midday button response for user {user_id}")
            
            # Extract button data from the correct structure
            button_id = button_data['interactive']['button_reply']['id']
            
            # Check if this is a confirmation response
            if button_id.startswith('confirm_'):
                # Extract the original command from the confirmation ID
                # Format: confirm_yes_done_1 or confirm_no_done_1
                _, response, command_type, task_num = button_id.split('_')
                task_num = int(task_num) - 1  # Convert to 0-based index
                
                if response == 'yes':
                    # Map command type to status
                    status_map = {
                        'DONE': 'completed',
                        'PROGRESS': 'in_progress',
                        'STUCK': 'stuck'
                    }
                    
                    # Update task status
                    self.task.update_task_status(user_id, task_num, status_map[command_type.upper()], instance_id)
                    
                    # Get the updated task list
                    tasks = self.task.get_daily_tasks(user_id, instance_id)
                    if task_num < 0 or task_num >= len(tasks):
                        response = f"Hmm, I don't see task #{task_num + 1} on your list. Want to try again or type 'TASKS' to see your current list?"
                    else:
                        task_name = tasks[task_num]['task']
                        if command_type.upper() == 'DONE':
                            responses = [
                                f"🎉 Yes! You completed '{task_name}'! That's a genuine win - how did it feel to finish that one?",
                                f"✨ Amazing job finishing '{task_name}'! What helped you get this done today?",
                                f"💪 '{task_name}' → DONE! That's awesome progress. Would you like to take a moment to celebrate?"
                            ]
                            response = random.choice(responses)
                        elif command_type.upper() == 'PROGRESS':
                            responses = [
                                f"👍 Thanks for letting me know you're working on '{task_name}'. Taking those first steps can be the hardest part!",
                                f"🔄 Got it - '{task_name}' is in progress. Remember, consistent effort matters more than perfect execution.",
                                f"⏳ '{task_name}' in progress - that's great! Is there anything that would make this task flow better for you?"
                            ]
                            response = random.choice(responses)
                        else:  # STUCK
                            response = (
                                f"I hear you're feeling stuck with '{task_name}'. That happens to everyone, especially with complicated or less interesting tasks.\n\n"
                                f"Would you like to:\n"
                                f"1. Break this down into smaller steps?\n"
                                f"2. Talk about what specific part feels challenging?\n"
                                f"3. Get some motivation or a different approach?\n"
                                f"4. Set this aside for now and come back to it later?"
                            )
                else:
                    response = "No problem! I'll keep the task status as it was."
                
                self.whatsapp.send_message(user_id, response)
            else:
                # This is a regular status update button
                # Extract task number from button ID (e.g., 'done_1', 'progress_2', 'stuck_3')
                task_num = int(button_id.split('_')[1]) - 1  # Convert to 0-based index
                command_type = button_id.split('_')[0].upper()
                
                # Get current task status
                tasks = self.task.get_daily_tasks(user_id, instance_id)
                if task_num < 0 or task_num >= len(tasks):
                    response = f"Hmm, I don't see task #{task_num + 1} on your list. Want to try again or type 'TASKS' to see your current list?"
                    self.whatsapp.send_message(user_id, response)
                    return
                
                current_task = tasks[task_num]
                if 'status' in current_task:
                    # Task already has a status, ask for confirmation
                    status_map = {
                        'completed': 'Done ✅',
                        'in_progress': 'In Progress 🔄',
                        'stuck': 'Stuck ❗',
                        'pending': 'Not Started'
                    }
                    current_status = status_map.get(current_task['status'], current_task['status'])
                    new_status = button_data['interactive']['button_reply']['title']
                    
                    message = (
                        f"This task is currently marked as {current_status}. "
                        f"Are you sure you want to change it to {new_status}?"
                    )
                    
                    buttons = [
                        {"id": f"confirm_yes_{command_type.lower()}_{task_num + 1}", "title": "Yes"},
                        {"id": f"confirm_no_{command_type.lower()}_{task_num + 1}", "title": "No"}
                    ]
                    
                    self.whatsapp.send_interactive_buttons(user_id, message, buttons)
                else:
                    # First time setting status, no confirmation needed
                    status_map = {
                        'DONE': 'completed',
                        'PROGRESS': 'in_progress',
                        'STUCK': 'stuck'
                    }
                    
                    # Update task status
                    self.task.update_task_status(user_id, task_num, status_map[command_type], instance_id)
                    
                    # Get the updated task list and generate response
                    tasks = self.task.get_daily_tasks(user_id, instance_id)
                    task_name = tasks[task_num]['task']
                    if command_type == 'DONE':
                        responses = [
                            f"🎉 Yes! You completed '{task_name}'! That's a genuine win - how did it feel to finish that one?",
                            f"✨ Amazing job finishing '{task_name}'! What helped you get this done today?",
                            f"💪 '{task_name}' → DONE! That's awesome progress. Would you like to take a moment to celebrate?"
                        ]
                        response = random.choice(responses)
                    elif command_type == 'PROGRESS':
                        responses = [
                            f"👍 Thanks for letting me know you're working on '{task_name}'. Taking those first steps can be the hardest part!",
                            f"🔄 Got it - '{task_name}' is in progress. Remember, consistent effort matters more than perfect execution.",
                            f"⏳ '{task_name}' in progress - that's great! Is there anything that would make this task flow better for you?"
                        ]
                        response = random.choice(responses)
                    else:  # STUCK
                        response = (
                            f"I hear you're feeling stuck with '{task_name}'. That happens to everyone, especially with complicated or less interesting tasks.\n\n"
                            f"Would you like to:\n"
                            f"1. Break this down into smaller steps?\n"
                            f"2. Talk about what specific part feels challenging?\n"
                            f"3. Get some motivation or a different approach?\n"
                            f"4. Set this aside for now and come back to it later?"
                        )
                    
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