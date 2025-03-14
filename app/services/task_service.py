from firebase_admin import firestore
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import time

# In-memory fallback storage
memory_storage = {
    'users': {},
    'task_history': []
}

class TaskService:
    def __init__(self):
        try:
            self.db = firestore.client()
            self.use_firestore = True
            print("Using Firestore for data storage")
        except Exception as e:
            self.use_firestore = False
            print(f"Warning: Firestore unavailable - {str(e)}")
            print("Using in-memory storage as fallback (data will be lost on restart)")
        
    def get_user_state(self, user_id: str, instance_id: str = 'default') -> str:
        """Get the current state of the user in the system."""
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if not user_doc.exists:
                    return 'SETUP'
                    
                user_data = user_doc.to_dict()
                return user_data.get('state', 'SETUP')
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return 'SETUP'
                return memory_storage['users'][instance_key].get('state', 'SETUP')
        except Exception as e:
            print(f"Error getting user state: {str(e)}")
            return 'SETUP'
        
    def create_user(self, user_id: str, instance_id: str = 'default', phone_number: str = None) -> None:
        """Create a new user in the system."""
        user_data = {
            'created_at': datetime.now(),
            'state': 'SETUP',
            'tasks': [],
            'last_interaction': datetime.now(),
            'phone_number': phone_number,
            'instance': instance_id,  # Changed from instance_id to instance to match unified collection
            'conversation_history': [],
            'metrics': {
                'total_tasks': 0,
                'completed_tasks': 0,
                'completion_rate': 0
            }
        }
        
        try:
            if self.use_firestore:
                # Save to instance-specific collection
                instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                instance_user_ref.set(user_data)
                
                # Save to unified collection
                unified_user_ref = self.db.collection('users').document(user_id)
                unified_user_ref.set(user_data)
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                memory_storage['users'][instance_key] = user_data
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            # Fallback to in-memory storage
            instance_key = f"{instance_id}:{user_id}"
            memory_storage['users'][instance_key] = user_data
        
    def update_user_state(self, user_id: str, state: str, instance_id: str = 'default') -> None:
        """Update the user's current state."""
        update_data = {
            'state': state,
            'last_interaction': datetime.now()
        }
        
        try:
            if self.use_firestore:
                # Update instance-specific collection
                instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                instance_user_ref.update(update_data)
                
                # Update unified collection
                unified_user_ref = self.db.collection('users').document(user_id)
                unified_user_ref.update(update_data)
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key in memory_storage['users']:
                    memory_storage['users'][instance_key]['state'] = state
                    memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
        except Exception as e:
            print(f"Error updating user state: {str(e)}")
            # Fallback to in-memory storage
            instance_key = f"{instance_id}:{user_id}"
            if instance_key not in memory_storage['users']:
                self.create_user(user_id, instance_id, None)
            memory_storage['users'][instance_key]['state'] = state
            memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
        
    def save_tasks(self, user_id: str, tasks: List[str], instance_id: str = 'default') -> None:
        """Save the user's tasks for the day."""
        # Format tasks with status
        formatted_tasks = [{'task': task, 'status': 'pending'} for task in tasks]
        
        update_data = {
            'tasks': formatted_tasks,
            'state': 'CHECK_IN',
            'last_interaction': datetime.now()
        }
        
        try:
            if self.use_firestore:
                # Update instance-specific collection
                instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                instance_user_ref.update(update_data)
                
                # Update unified collection
                unified_user_ref = self.db.collection('users').document(user_id)
                unified_user_ref.update(update_data)
                
                # Create a task history entry
                history_ref = self.db.collection('instances').document(instance_id).collection('task_history')
                history_ref.add({
                    'user_id': user_id,
                    'tasks': formatted_tasks,
                    'date': datetime.now(),
                    'instance_id': instance_id
                })
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    self.create_user(user_id, instance_id, None)
                
                memory_storage['users'][instance_key]['tasks'] = formatted_tasks
                memory_storage['users'][instance_key]['state'] = 'CHECK_IN'
                memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
                
                # Add to task history
                memory_storage['task_history'].append({
                    'user_id': user_id,
                    'tasks': formatted_tasks,
                    'date': datetime.now(),
                    'instance_id': instance_id
                })
        except Exception as e:
            print(f"Error saving tasks: {str(e)}")
            # Fallback to in-memory storage
            instance_key = f"{instance_id}:{user_id}"
            if instance_key not in memory_storage['users']:
                self.create_user(user_id, instance_id, None)
            
            memory_storage['users'][instance_key]['tasks'] = formatted_tasks
            memory_storage['users'][instance_key]['state'] = 'CHECK_IN'
            memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
            
            # Add to task history
            memory_storage['task_history'].append({
                'user_id': user_id,
                'tasks': formatted_tasks,
                'date': datetime.now(),
                'instance_id': instance_id
            })
        
    def update_task_status(self, user_id: str, task_index: int, status: str, instance_id: str = 'default') -> None:
        """Update the status of a specific task."""
        try:
            if self.use_firestore:
                # Get current user data from instance-specific collection
                instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = instance_user_ref.get()
                
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
                    
                    update_data = {
                        'tasks': tasks,
                        'last_interaction': datetime.now(),
                        'metrics': metrics
                    }
                    
                    # Update both collections
                    instance_user_ref.update(update_data)
                    unified_user_ref = self.db.collection('users').document(user_id)
                    unified_user_ref.update(update_data)
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return
                
                tasks = memory_storage['users'][instance_key].get('tasks', [])
                if 0 <= task_index < len(tasks):
                    tasks[task_index]['status'] = status
                    
                    # Update metrics
                    metrics = memory_storage['users'][instance_key].get('metrics', {})
                    if status == 'completed':
                        metrics['completed_tasks'] = metrics.get('completed_tasks', 0) + 1
                        metrics['completion_rate'] = (metrics['completed_tasks'] / metrics['total_tasks']) * 100 if metrics['total_tasks'] > 0 else 0
                    
                    memory_storage['users'][instance_key]['tasks'] = tasks
                    memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
                    memory_storage['users'][instance_key]['metrics'] = metrics
        except Exception as e:
            print(f"Error updating task status: {str(e)}")
            
    def log_conversation(self, user_id: str, message: str, response: str, instance_id: str = 'default') -> None:
        """Log conversation history for the user."""
        try:
            if self.use_firestore:
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
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return
                
                if 'conversation_history' not in memory_storage['users'][instance_key]:
                    memory_storage['users'][instance_key]['conversation_history'] = []
                
                memory_storage['users'][instance_key]['conversation_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'message': message,
                    'response': response
                })
                
                # Keep only last 50 conversations
                if len(memory_storage['users'][instance_key]['conversation_history']) > 50:
                    memory_storage['users'][instance_key]['conversation_history'] = memory_storage['users'][instance_key]['conversation_history'][-50:]
                
                memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
        except Exception as e:
            print(f"Error logging conversation: {str(e)}")
            # Continue without logging if there's an error
                
    def get_user_metrics(self, user_id: str, instance_id: str = 'default') -> Dict[str, Any]:
        """Get user's task completion metrics."""
        default_metrics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'in_progress_tasks': 0,
            'stuck_tasks': 0,
            'completion_rate': 0
        }
        
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if not user_doc.exists:
                    return default_metrics
                    
                user_data = user_doc.to_dict()
                return user_data.get('metrics', default_metrics)
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return default_metrics
                
                return memory_storage['users'][instance_key].get('metrics', default_metrics)
        except Exception as e:
            print(f"Error getting user metrics: {str(e)}")
            return default_metrics
        
    def get_daily_tasks(self, user_id: str, instance_id: str = 'default') -> List[Dict[str, Any]]:
        """Get the user's tasks for the current day."""
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if not user_doc.exists:
                    return []
                    
                user_data = user_doc.to_dict()
                return user_data.get('tasks', [])
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return []
                
                return memory_storage['users'][instance_key].get('tasks', [])
        except Exception as e:
            print(f"Error getting daily tasks: {str(e)}")
            return [] 