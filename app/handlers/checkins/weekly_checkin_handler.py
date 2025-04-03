import logging
import time
from typing import Dict, Any
from app.models.user import User
from app.services.sentiment_service import SentimentService

logger = logging.getLogger(__name__)

class WeeklyCheckinHandler:
    """Handler for weekly check-in and reflection flow."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        
    def handle_weekly_reflection(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle weekly reflection flow."""
        try:
            # Get or create user
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Initialize context updates
            context_updates = {
                'last_check_in': int(time.time()),
                'check_in_type': 'weekly'
            }
            
            # Handle button responses
            if (isinstance(message_text, dict) and 
                message_text.get('type') == 'interactive' and 
                message_text.get('interactive', {}).get('type') == 'button_reply'):
                
                button_response = message_text['interactive']['button_reply']
                logger.info(f"Received button response: {button_response}")
                
                if button_response['id'] == 'weekly':
                    # User chose weekly planning
                    context_updates['planning_type'] = 'weekly'
                    response = (
                        "Let's plan your tasks for the upcoming week. Please reply with your tasks in this format:\n\n"
                        "Monday: Task 1, Task 2, Task 3\n"
                        "Tuesday: Task 1, Task 2, Task 3\n"
                        "Wednesday: Task 1, Task 2, Task 3\n"
                        "Thursday: Task 1, Task 2, Task 3\n"
                        "Friday: Task 1, Task 2, Task 3"
                    )
                    self.whatsapp.send_message(user_id, response)
                    self.task.update_user_state(user_id, 'WEEKLY_TASK_INPUT', instance_id, context_updates)
                    return
                    
                elif button_response['id'] == 'daily':
                    # User chose daily planning
                    context_updates['planning_type'] = 'daily'
                    response = (
                        f"Great choice! I'll be here every morning to help you set your daily tasks. "
                        "No pressure—just a little nudge to help you stay on track. "
                        "Looking forward to planning with you each day! 😊"
                    )
                    self.whatsapp.send_message(user_id, response)
                    self.task.update_user_state(user_id, 'DAILY_CHECK_IN', instance_id, context_updates)
                    return
            
            # Handle text message for sentiment analysis
            if isinstance(message_text, str):
                # Analyze sentiment
                analysis = self.sentiment.analyze_checkin_text(message_text)
                logger.info(f"Weekly reflection sentiment analysis for user {user_id}: {analysis}")
                
                # Store sentiment data
                context_updates['last_sentiment'] = analysis
                
                # Generate response based on sentiment
                emotional_state = analysis.get('emotional_state', 'neutral')
                energy_level = analysis.get('energy_level', 'medium')
                
                if emotional_state == 'negative':
                    response = (
                        f"I hear you, {name}. 💙 It's completely okay to not be feeling your best. "
                        "Let's take it day by day and focus on what feels manageable.\n\n"
                        "Would you like to:\n"
                        "1. Just talk through your feelings\n"
                        "2. Try focusing on one small task\n"
                        "3. Take a self-care day"
                    )
                    self.whatsapp.send_interactive_buttons(
                        user_id,
                        response,
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
                    response = (
                        f"That's fantastic, {name}! 🌟 I love your positive energy. "
                        "Let's make the most out of this week ahead!\n\n"
                        "How would you like to plan?"
                    )
                    self.whatsapp.send_interactive_buttons(
                        user_id,
                        response,
                        [
                            {"id": "weekly", "title": "Plan for the week"},
                            {"id": "daily", "title": "Day by day planning"}
                        ]
                    )
                    self.task.update_user_state(
                        user_id, 'AWAITING_PLANNING_CHOICE', instance_id, context_updates
                    )
            
        except Exception as e:
            logger.error(f"Error in weekly reflection: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I encountered an error processing your reflection. Let's try again - how was your week?"
            )
            
    def handle_weekly_task_input(self, user_id: str, message_text: str, instance_id: str, context: dict) -> None:
        """Handle weekly task input after reflection."""
        try:
            # Parse tasks from message
            tasks_by_day = {}
            current_day = None
            
            for line in message_text.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line starts with a day
                day_match = any(line.lower().startswith(day.lower()) for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])
                
                if day_match:
                    current_day = line.split(':')[0].strip().title()
                    tasks_by_day[current_day] = []
                elif current_day:
                    # Remove leading numbers and dots
                    task = line.lstrip('0123456789. ')
                    if task:
                        tasks_by_day[current_day].append({
                            'task': task,
                            'status': 'pending',
                            'created_at': int(time.time())
                        })
            
            if not tasks_by_day:
                self.whatsapp.send_message(
                    user_id,
                    "I couldn't identify any tasks in your message. Could you please list them again?\n\n"
                    "For example:\n"
                    "Monday: Review project, Send emails\n"
                    "Tuesday: Team meeting, Update docs\n"
                    "..."
                )
                return
            
            # Store tasks
            self.task.store_weekly_tasks(user_id, tasks_by_day, instance_id)
            
            # Send confirmation
            response = "Perfect! I've saved your tasks for the week. Here's what I've got:\n\n"
            for day, tasks in tasks_by_day.items():
                response += f"{day}:\n"
                for i, task in enumerate(tasks, 1):
                    response += f"{i}. {task['task']}\n"
                response += "\n"
            
            response += "I'll check in with you each morning to help you focus on that day's tasks! 🌟"
            
            self.whatsapp.send_message(user_id, response)
            
            # Update user state
            context_updates = {
                'last_task_update': int(time.time()),
                'total_weekly_tasks': sum(len(tasks) for tasks in tasks_by_day.values())
            }
            self.task.update_user_state(
                user_id, 'WEEKLY_REFLECTION', instance_id, context_updates
            )
            
        except Exception as e:
            logger.error(f"Error handling weekly task input: {str(e)}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble saving your tasks. Could you try listing them again?"
            ) 