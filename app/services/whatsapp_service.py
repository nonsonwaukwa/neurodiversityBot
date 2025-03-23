import os
import requests
from typing import Dict, Any
import json
import random

class WhatsAppService:
    def __init__(self, instance_id: str = 'default'):
        self.instance_id = instance_id
        self.api_version = 'v17.0'
        
        # Try both formats of environment variables
        self.phone_number_id = (
            os.getenv(f'WHATSAPP_PHONE_NUMBER_ID_{instance_id.upper()}') or  # WHATSAPP_PHONE_NUMBER_ID_INSTANCE1
            os.getenv(f'WHATSAPP_PHONE_NUMBER_ID_{instance_id[-1]}') or      # WHATSAPP_PHONE_NUMBER_ID_1
            os.getenv('WHATSAPP_PHONE_NUMBER_ID')                            # Fallback
        )
        
        self.access_token = (
            os.getenv(f'WHATSAPP_TOKEN_{instance_id.upper()}') or           # WHATSAPP_TOKEN_INSTANCE1
            os.getenv(f'WHATSAPP_ACCESS_TOKEN_{instance_id[-1]}') or        # WHATSAPP_ACCESS_TOKEN_1
            os.getenv('WHATSAPP_TOKEN')                                     # Fallback
        )
        
        if not self.phone_number_id or not self.access_token:
            raise ValueError(f"Missing WhatsApp credentials for instance {instance_id}")
            
        self.base_url = f'https://graph.facebook.com/{self.api_version}/{self.phone_number_id}'

    def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send a message to a WhatsApp user."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': message}
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/messages',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error sending message to {to}: {str(e)}")
            return {'error': str(e)}

    def send_template_message(self, to: str, template_name: str, language_code: str, components: list) -> Dict[str, Any]:
        """Send a template message to a WhatsApp user."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {
                    'code': language_code
                },
                'components': components
            }
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/messages',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error sending template message to {to}: {str(e)}")
            return {'error': str(e)}

    def send_task_reminder(self, to: str, tasks: list) -> str:
        """Generate a friendly task reminder message with supportive language."""
        # Check if there are any tasks
        if not tasks:
            return (
                "You don't have any tasks set up for today yet. That's completely okay!\n\n"
                "Would you like to set some small goals for today, or is today more of a rest day?"
            )
        
        # Count tasks by status
        statuses = {'pending': 0, 'in_progress': 0, 'completed': 0, 'stuck': 0}
        for task in tasks:
            statuses[task['status']] = statuses.get(task['status'], 0) + 1
        
        # Format task list with emoji indicators
        task_lines = []
        for i, task in enumerate(tasks):
            status = task['status']
            if status == 'completed':
                emoji = "✅"
            elif status == 'in_progress':
                emoji = "🔄"
            elif status == 'stuck':
                emoji = "❗"
            else:  # pending
                emoji = "⭐"
            task_lines.append(f"{i+1}. {emoji} {task['task']}")
        
        task_list = '\n'.join(task_lines)
        
        # Choose an appropriate opener based on progress
        if statuses['completed'] == len(tasks):
            opener = random.choice([
                "Wow! You've completed everything on your list! That's amazing! 🎉",
                "Look at you go! All tasks completed! That's seriously impressive. 🌟",
                "Everything done! Your brain has been working so hard today! 🏆"
            ])
        elif statuses['completed'] > 0:
            opener = random.choice([
                f"You've completed {statuses['completed']} task(s) so far - that's real progress! 💪",
                f"I see you've finished {statuses['completed']} task(s) - each one is a genuine win! ✨",
                f"{statuses['completed']} task(s) done! Your efforts definitely count. 🌈"
            ])
        elif statuses['in_progress'] > 0:
            opener = random.choice([
                "I see you're making progress - that first step is often the hardest part! 👏",
                "You've started working on things - that takes courage and initiative! 🌱",
                "Getting started is a win in itself - nice job beginning the process! 💫"
            ])
        else:
            opener = random.choice([
                "Here's what's on your plate today. Remember, even small steps count! 💭",
                "Here are your tasks whenever you're ready to begin. No rush! 🌈",
                "These are your goals for today. Remember to be kind to yourself as you work through them. 💙"
            ])
        
        # Choose an appropriate closer based on status
        if statuses['stuck'] > 0:
            closer = random.choice([
                "I notice you're feeling stuck on some tasks. That happens to everyone! Would it help to break them into smaller steps?",
                "Some tasks feel challenging right now, and that's completely normal. What support would help you most?",
                "Feeling stuck is part of the process sometimes. Would talking through the tough spots help?"
            ])
        else:
            closer = random.choice([
                "How are things going? Remember you can update me anytime with your progress or challenges.",
                "How's your energy level as you work on these? Remember to take breaks when needed.",
                "Remember, progress isn't always linear, especially for neurodivergent brains. Ups and downs are normal!",
                "Be proud of any movement forward, no matter how small it might seem!"
            ])
        
        # Assemble the full message
        return (
            f"{opener}\n\n"
            f"{task_list}\n\n"
            f"{closer}\n\n"
            f"You can respond with:\n"
            f"• 'DONE 1' - When you complete a task\n"
            f"• 'PROGRESS 2' - When you're working on something\n"
            f"• 'STUCK 3' - If you need help with a specific task\n"
            f"• 'CHAT' - Just to talk about how you're doing"
        )

    def send_daily_summary(self, to: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Send a daily summary of task completion with neurodivergent-friendly framing."""
        completion_rate = metrics.get('completion_rate', 0)
        completed_tasks = metrics.get('completed_tasks', 0)
        total_tasks = metrics.get('total_tasks', 0)
        
        # Choose appropriate messaging based on completion
        if completion_rate >= 80:
            praise = random.choice([
                "That's incredible progress! Your brain has been working hard today.",
                "Wow! What an amazingly productive day you've had!",
                "Look at all you've accomplished today! Your efforts have really paid off."
            ])
        elif completion_rate >= 50:
            praise = random.choice([
                "That's solid progress! Every completed task is a genuine win.",
                "You've made meaningful headway today. Well done!",
                "Good steady progress today. Each step forward counts!"
            ])
        else:
            praise = random.choice([
                "Every bit of progress matters, especially on challenging days.",
                "Remember that effort counts, even when completion feels hard.",
                "Some days are tougher than others, and that's completely okay."
            ])
            
        # Add a neurodivergent-friendly reflection
        reflection = random.choice([
            "Remember that progress isn't always linear, especially for neurodivergent brains. Tomorrow is a fresh start!",
            "For neurodivergent minds, some days flow better than others. Be gentle with yourself!",
            "Your worth isn't measured by your productivity. You're doing great just by showing up.",
            "Every brain works differently. Honor your unique rhythm and celebrate all progress, no matter how small."
        ])
        
        message = (
            f"📊 Your Day in Review:\n\n"
            f"Tasks completed: {completed_tasks}/{total_tasks}\n"
            f"Completion rate: {completion_rate:.1f}%\n\n"
            f"{praise}\n\n"
            f"{reflection}\n\n"
            f"What's one thing you feel good about from today?"
        )
        
        return self.send_message(to, message)

def get_whatsapp_service(instance_id: str = 'instance1') -> WhatsAppService:
    """Get a WhatsApp service instance for the given instance ID."""
    return WhatsAppService(instance_id) 