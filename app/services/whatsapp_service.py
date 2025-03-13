import os
import requests
from typing import Dict, Any
import json

class WhatsAppService:
    def __init__(self, instance_id: str = 'default'):
        self.instance_id = instance_id
        self.api_version = 'v17.0'
        self.phone_number_id = os.getenv(f'WHATSAPP_PHONE_NUMBER_ID_{instance_id.upper()}', 
                                       os.getenv('WHATSAPP_PHONE_NUMBER_ID'))
        self.access_token = os.getenv(f'WHATSAPP_TOKEN_{instance_id.upper()}',
                                    os.getenv('WHATSAPP_TOKEN'))
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

    def send_task_reminder(self, to: str, tasks: list) -> Dict[str, Any]:
        """Send a task reminder message."""
        task_list = '\n'.join(f'- {task["task"]} ({task["status"]})' for task in tasks)
        
        message = (
            f"📝 Here are your tasks for today:\n\n"
            f"{task_list}\n\n"
            f"How are you progressing? Reply with:\n"
            f"✅ DONE [task number] - to mark a task as complete\n"
            f"🔄 PROGRESS [task number] - to mark as in progress\n"
            f"❌ STUCK [task number] - if you need help"
        )
        
        return self.send_message(to, message)

    def send_daily_summary(self, to: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Send a daily summary of task completion."""
        completion_rate = metrics.get('completion_rate', 0)
        completed_tasks = metrics.get('completed_tasks', 0)
        total_tasks = metrics.get('total_tasks', 0)
        
        message = (
            f"📊 Your Daily Summary:\n\n"
            f"Tasks Completed: {completed_tasks}/{total_tasks}\n"
            f"Completion Rate: {completion_rate:.1f}%\n\n"
            f"Keep up the great work! 💪"
        )
        
        return self.send_message(to, message) 