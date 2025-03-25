from firebase_admin import firestore
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import json
import time
import logging

# In-memory fallback storage
memory_storage = {
    'users': {},
    'task_history': []
}

logger = logging.getLogger(__name__)

class TaskService:
    # State constants
    STATES = {
        'INITIAL': 'initial_state',
        'WEEKLY_REFLECTION': 'weekly_reflection',
        'WEEKLY_TASK_SELECTION': 'weekly_task_selection',
        'DAILY_CHECK_IN': 'daily_check_in',
        'DAILY_TASK_SELECTION': 'daily_task_selection',
        'MIDDAY_CHECK_IN': 'midday_check_in',
        'END_DAY_CHECK_IN': 'end_day_check_in',
        'TASK_UPDATE': 'task_update'
    }

    # Check-in types
    CHECK_IN_TYPES = {
        'WEEKLY': 'weekly_checkin',
        'DAILY': 'daily_checkin',
        'MIDDAY': 'midday_checkin',
        'END_DAY': 'end_day_checkin'
    }

    def __init__(self):
        try:
            self.db = firestore.client()
            self.use_firestore = True
            print("Using Firestore for data storage")
        except Exception as e:
            self.use_firestore = False
            print(f"Warning: Firestore unavailable - {str(e)}")
            print("Using in-memory storage as fallback (data will be lost on restart)")
        
    def get_user_state(self, user_id: str, instance_id: str) -> Dict[str, Any]:
        """Get the current state and context of the user in the system."""
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    return {
                        'state': user_data.get('state', 'INITIAL'),
                        'context': {
                            'flow_type': user_data.get('flow_type'),  # weekly/daily
                            'last_check_in': user_data.get('last_check_in'),
                            'last_task_update': user_data.get('last_task_update'),
                            'current_tasks': user_data.get('current_tasks', []),
                            'planning_type': user_data.get('planning_type'),
                            'emotional_state': user_data.get('emotional_state'),
                            'energy_level': user_data.get('energy_level'),
                            'pending_checkins': user_data.get('pending_checkins', []),
                            'current_checkin_source': user_data.get('current_checkin_source'),
                            'missed_checkins': user_data.get('missed_checkins', [])
                        },
                        'last_state_update': user_data.get('last_state_update')
                    }
                else:
                    # Initialize new user state with context
                    initial_state = {
                        'state': 'INITIAL',
                        'context': {
                            'flow_type': None,
                            'last_check_in': None,
                            'last_task_update': None,
                            'current_tasks': [],
                            'planning_type': None,
                            'emotional_state': None,
                            'energy_level': None,
                            'pending_checkins': [],
                            'current_checkin_source': None,
                            'missed_checkins': []
                        },
                        'last_state_update': int(time.time())
                    }
                    user_ref.set(initial_state)
                    return initial_state
            else:
                # In-memory fallback
                user_key = f"{instance_id}:{user_id}"
                return memory_storage['users'].get(user_key, {
                    'state': 'INITIAL',
                    'context': {
                        'flow_type': None,
                        'last_check_in': None,
                        'last_task_update': None,
                        'current_tasks': [],
                        'planning_type': None,
                        'emotional_state': None,
                        'energy_level': None,
                        'pending_checkins': [],
                        'current_checkin_source': None,
                        'missed_checkins': []
                    },
                    'last_state_update': int(time.time())
                })
                
        except Exception as e:
            print(f"Error getting user state: {str(e)}")
            return {
                'state': 'INITIAL',
                'context': {},
                'last_state_update': int(time.time())
            }

    def update_user_state(self, user_id: str, new_state: str, instance_id: str, context_updates: Dict = None):
        """Update user state and context using a transaction."""
        @firestore.transactional
        def update_in_transaction(transaction, user_ref):
            snapshot = user_ref.get(transaction=transaction)
            current_data = snapshot.to_dict() if snapshot.exists else {}
            
            # Prepare update data
            update_data = {
                'state': new_state,
                'last_state_update': int(time.time())
            }
            
            # Update context if provided
            if context_updates:
                current_context = current_data.get('context', {})
                current_context.update(context_updates)
                update_data['context'] = current_context
            
            transaction.set(user_ref, update_data, merge=True)
        
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                transaction = self.db.transaction()
                update_in_transaction(transaction, user_ref)
            else:
                # In-memory fallback
                user_key = f"{instance_id}:{user_id}"
                if user_key not in memory_storage['users']:
                    memory_storage['users'][user_key] = {}
                memory_storage['users'][user_key].update({
                    'state': new_state,
                    'last_state_update': int(time.time())
                })
                if context_updates:
                    current_context = memory_storage['users'][user_key].get('context', {})
                    current_context.update(context_updates)
                    memory_storage['users'][user_key]['context'] = current_context
        except Exception as e:
            print(f"Error updating user state: {str(e)}")
            raise
        
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
                
                # Add new conversation entry with Unix timestamp
                conversation_history.append({
                    'timestamp': int(time.time()),
                    'message': message,
                    'response': response
                })
                
                # Keep only last 50 conversations
                if len(conversation_history) > 50:
                    conversation_history = conversation_history[-50:]
                    
                user_ref.update({
                    'conversation_history': conversation_history,
                    'last_interaction': int(time.time())
                })
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return
                
                if 'conversation_history' not in memory_storage['users'][instance_key]:
                    memory_storage['users'][instance_key]['conversation_history'] = []
                
                memory_storage['users'][instance_key]['conversation_history'].append({
                    'timestamp': int(time.time()),
                    'message': message,
                    'response': response
                })
                
                # Keep only last 50 conversations
                if len(memory_storage['users'][instance_key]['conversation_history']) > 50:
                    memory_storage['users'][instance_key]['conversation_history'] = memory_storage['users'][instance_key]['conversation_history'][-50:]
                
                memory_storage['users'][instance_key]['last_interaction'] = int(time.time())
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
    
    def get_user_name(self, user_id: str, instance_id: str = 'default') -> str:
        """Get the user's name from their profile data."""
        try:
            if self.use_firestore:
                # Try instance-specific collection first
                instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = instance_user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    if user_data.get('name'):
                        return user_data['name']
                
                # Try unified collection as fallback
                unified_user_ref = self.db.collection('users').document(user_id)
                user_doc = unified_user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    return user_data.get('name', 'Friend')
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key in memory_storage['users']:
                    return memory_storage['users'][instance_key].get('name', 'Friend')
            
            return 'Friend'  # Default fallback if no name is found
        except Exception as e:
            print(f"Error getting user name: {str(e)}")
            return 'Friend'  # Default fallback on error

    def add_pending_checkin(self, user_id: str, checkin_type: str, instance_id: str):
        """Add a pending check-in to the user's context."""
        try:
            if checkin_type not in self.CHECK_IN_TYPES.values():
                raise ValueError(f"Invalid check-in type: {checkin_type}")

            @firestore.transactional
            def update_in_transaction(transaction, user_ref):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return
                
                user_data = snapshot.to_dict()
                pending_checkins = user_data.get('context', {}).get('pending_checkins', [])
                
                # Add new check-in if not already pending
                if checkin_type not in pending_checkins:
                    pending_checkins.append({
                        'type': checkin_type,
                        'added_at': int(time.time())
                    })
                
                transaction.update(user_ref, {
                    'context.pending_checkins': pending_checkins
                })

            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                transaction = self.db.transaction()
                update_in_transaction(transaction, user_ref)
        except Exception as e:
            logger.error(f"Error adding pending check-in: {str(e)}")
            raise

    def resolve_checkin(self, user_id: str, checkin_type: str, instance_id: str, was_missed: bool = False):
        """Mark a check-in as resolved or missed."""
        try:
            @firestore.transactional
            def update_in_transaction(transaction, user_ref):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return
                
                user_data = snapshot.to_dict()
                context = user_data.get('context', {})
                pending_checkins = context.get('pending_checkins', [])
                missed_checkins = context.get('missed_checkins', [])
                
                # Remove from pending
                pending_checkins = [c for c in pending_checkins if c['type'] != checkin_type]
                
                # Add to missed if applicable
                if was_missed:
                    missed_checkins.append({
                        'type': checkin_type,
                        'missed_at': int(time.time())
                    })
                
                transaction.update(user_ref, {
                    'context.pending_checkins': pending_checkins,
                    'context.missed_checkins': missed_checkins,
                    'context.last_check_in': int(time.time()) if not was_missed else None
                })

            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                transaction = self.db.transaction()
                update_in_transaction(transaction, user_ref)
        except Exception as e:
            logger.error(f"Error resolving check-in: {str(e)}")
            raise 