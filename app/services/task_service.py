from firebase_admin import firestore
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

class TaskService:
    def __init__(self):
        self.db = firestore.client()
        
    def get_user_state(self, user_id: str, instance_id: str = 'default') -> str:
        """Get the current state of the user in the system."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return 'SETUP'
            
        user_data = user_doc.to_dict()
        return user_data.get('state', 'SETUP')
        
    def create_user(self, user_id: str, instance_id: str = 'default', phone_number: str = None) -> None:
        """Create a new user in the system."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_ref.set({
            'created_at': datetime.now(),
            'state': 'SETUP',
            'tasks': [],
            'last_interaction': datetime.now(),
            'phone_number': phone_number,
            'instance_id': instance_id,
            'conversation_history': [],
            'metrics': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'completion_rate': 0
            }
        })
        
    def update_user_state(self, user_id: str, state: str, instance_id: str = 'default') -> None:
        """Update the user's current state."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_ref.update({
            'state': state,
            'last_interaction': datetime.now()
        })
        
    def save_tasks(self, user_id: str, tasks: List[str], instance_id: str = 'default') -> None:
        """Save the user's tasks for the day."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        
        # Format tasks with status
        formatted_tasks = [{'task': task, 'status': 'pending'} for task in tasks]
        
        user_ref.update({
            'tasks': formatted_tasks,
            'state': 'CHECK_IN',
            'last_interaction': datetime.now()
        })
        
        # Create a task history entry
        history_ref = self.db.collection('instances').document(instance_id).collection('task_history')
        history_ref.add({
            'user_id': user_id,
            'tasks': formatted_tasks,
            'date': datetime.now(),
            'instance_id': instance_id
        })
        
    def update_task_status(self, user_id: str, task_index: int, status: str, instance_id: str = 'default') -> None:
        """Update the status of a specific task."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return
            
        user_data = user_doc.to_dict()
        tasks = user_data.get('tasks', [])
        
        if 0 <= task_index < len(tasks):
            tasks[task_index]['status'] = status
            
            # Update metrics
            metrics = user_data.get('metrics', {})
            if status == 'completed':
                metrics['completed_tasks'] = metrics.get('completed_tasks', 0) + 1
                metrics['completion_rate'] = (metrics['completed_tasks'] / metrics['total_tasks']) * 100 if metrics['total_tasks'] > 0 else 0
            
            user_ref.update({
                'tasks': tasks,
                'last_interaction': datetime.now(),
                'metrics': metrics
            })
            
    def log_conversation(self, user_id: str, message: str, response: str, instance_id: str = 'default') -> None:
        """Log conversation history for the user."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return
            
        user_data = user_doc.to_dict()
        conversation_history = user_data.get('conversation_history', [])
        
        # Add new conversation entry
        conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'response': response
        })
        
        # Keep only last 50 conversations
        if len(conversation_history) > 50:
            conversation_history = conversation_history[-50:]
            
        user_ref.update({
            'conversation_history': conversation_history,
            'last_interaction': datetime.now()
        })
            
    def get_user_metrics(self, user_id: str, instance_id: str = 'default') -> Dict[str, Any]:
        """Get user's task completion metrics."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'in_progress_tasks': 0,
                'stuck_tasks': 0,
                'completion_rate': 0
            }
            
        user_data = user_doc.to_dict()
        return user_data.get('metrics', {})
        
    def get_daily_tasks(self, user_id: str, instance_id: str = 'default') -> List[Dict[str, Any]]:
        """Get the user's tasks for the current day."""
        user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return []
            
        user_data = user_doc.to_dict()
        return user_data.get('tasks', []) 