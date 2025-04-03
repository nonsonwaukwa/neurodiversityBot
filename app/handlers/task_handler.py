import logging
import re
import random
from typing import Dict, Any
from app.models.user import User

logger = logging.getLogger(__name__)

class TaskHandler:
    """Handler for task-related operations and commands."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        
    def handle_task_command(self, user_id: str, command_match: re.Match, instance_id: str) -> str:
        """Handle task-related commands (DONE/PROGRESS/STUCK)."""
        command_type = command_match.group(1)
        task_num = int(command_match.group(2)) - 1  # Convert to 0-based index
        
        tasks = self.task.get_daily_tasks(user_id, instance_id)
        if task_num < 0 or task_num >= len(tasks):
            return f"I don't see task #{task_num + 1} on your list. Type 'TASKS' to see your current tasks."
        
        task = tasks[task_num]
        status_map = {'DONE': 'completed', 'PROGRESS': 'in_progress', 'STUCK': 'stuck'}
        self.task.update_task_status(user_id, task_num, status_map[command_type], instance_id)
        
        if command_type == 'DONE':
            return f"🎉 Great job completing '{task['task']}'! How do you feel about this accomplishment?"
        elif command_type == 'PROGRESS':
            return f"👍 Thanks for letting me know you're working on '{task['task']}'. How's it going?"
        else:  # STUCK
            return (
                f"I hear you're stuck with '{task['task']}'. That's completely okay.\n\n"
                f"Would you like to:\n"
                f"1. Break this into smaller steps?\n"
                f"2. Talk about what's challenging?\n"
                f"3. Get some alternative approaches?\n"
                f"4. Set it aside for now?"
            )
            
    def handle_tasks_list(self, user_id: str, instance_id: str, context: dict) -> str:
        """Handle TASKS command to show current tasks."""
        tasks = self.task.get_daily_tasks(user_id, instance_id)
        if not tasks:
            if context.get('planning_type') == 'weekly':
                # Get today's tasks from weekly plan
                today = datetime.now().strftime('%A')
                tasks = self.task.get_weekly_tasks(user_id, instance_id, today)
                if tasks:
                    response = f"Here are your tasks for {today}:\n"
                    for i, task in enumerate(tasks, 1):
                        response += f"{i}. {task['task']}\n"
                else:
                    response = f"You haven't set any tasks for {today} yet."
            else:
                response = "You haven't set any tasks for today yet."
        else:
            response = "Here are your current tasks:\n"
            for i, task in enumerate(tasks, 1):
                response += f"{i}. {task['task']}\n"
                
        return response
        
    def handle_check_in(self, user_id: str, message_text: str, instance_id: str) -> str:
        """Handle user's check-in response."""
        # Check for task status updates
        status_match = re.match(r'(DONE|PROGRESS|STUCK)\s+(\d+)', message_text.upper())
        if status_match:
            return self.handle_task_command(user_id, status_match, instance_id)
        
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