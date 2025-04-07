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
    """Service for managing user tasks."""
    
    # Define all possible states
    STATES = {
        'INITIAL': 'INITIAL',
        'DAILY_CHECK_IN': 'DAILY_CHECK_IN',
        'DAILY_TASK_INPUT': 'DAILY_TASK_INPUT',
        'WEEKLY_REFLECTION': 'WEEKLY_REFLECTION',
        'WEEKLY_TASK_INPUT': 'WEEKLY_TASK_INPUT',
        'WEEKLY_PLANNING_COMPLETE': 'WEEKLY_PLANNING_COMPLETE',
        'AWAITING_PLANNING_CHOICE': 'AWAITING_PLANNING_CHOICE',
        'AWAITING_SUPPORT_CHOICE': 'AWAITING_SUPPORT_CHOICE',
        'EMOTIONAL_SUPPORT': 'EMOTIONAL_SUPPORT',
        'SELF_CARE_DAY': 'SELF_CARE_DAY',
        'SMALL_TASK_FOCUS': 'SMALL_TASK_FOCUS',
        'THERAPEUTIC_CONVERSATION': 'THERAPEUTIC_CONVERSATION',
        'TASK_UPDATE': 'TASK_UPDATE'
    }

    # Check-in types
    CHECK_IN_TYPES = {
        'WEEKLY': 'weekly_checkin',
        'DAILY': 'daily_checkin',
        'MIDDAY': 'midday_checkin',
        'END_DAY': 'end_day_checkin'
    }

    def __init__(self):
        """Initialize TaskService."""
        try:
            self.db = firestore.client()
            self.use_firestore = True
            self._setup_sync_listeners()
            print("Using Firestore for data storage")
        except Exception as e:
            self.use_firestore = False
            print(f"Warning: Firestore unavailable - {str(e)}")
            print("Using in-memory storage as fallback (data will be lost on restart)")
        
    def _setup_sync_listeners(self):
        """Set up real-time listeners for syncing between collections."""
        try:
            # Listen for changes in instance collections
            for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
                users_ref = self.db.collection('instances').document(instance_id).collection('users')
                
                def on_snapshot(col_snapshot, changes, read_time):
                    for change in changes:
                        if change.type.name == 'MODIFIED' or change.type.name == 'ADDED':
                            try:
                                user_id = change.document.id
                                user_data = change.document.to_dict()
                                
                                # Sync to unified collection
                                self._sync_to_unified(user_id, user_data, instance_id)
                                
                            except Exception as e:
                                logger.error(f"Error in sync listener for user {change.document.id}: {e}", exc_info=True)
                
                # Start listening
                users_ref.on_snapshot(on_snapshot)
                logger.info(f"Started sync listener for instance {instance_id}")
                
        except Exception as e:
            logger.error(f"Error setting up sync listeners: {e}", exc_info=True)

    def _sync_to_unified(self, user_id: str, user_data: dict, instance_id: str):
        """Sync user data to unified collection."""
        try:
            # Get current unified data
            unified_ref = self.db.collection('users').document(user_id)
            unified_doc = unified_ref.get()
            
            # Prepare data for sync
            sync_data = {
                'instance_id': instance_id,
                'last_sync': int(time.time()),
                'sync_status': 'synced'
            }
            
            # Add task-specific data
            if 'daily_tasks' in user_data:
                sync_data['daily_tasks'] = user_data['daily_tasks']
                # Store in daily_tasks subcollection
                daily_tasks_ref = unified_ref.collection('daily_tasks').document()
                daily_tasks_ref.set({
                    'tasks': user_data['daily_tasks'],
                    'created_at': int(time.time()),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'instance_id': instance_id,
                    'status': 'active'
                })
            
            if 'weekly_tasks' in user_data:
                sync_data['weekly_tasks'] = user_data['weekly_tasks']
                # Store in weekly_tasks subcollection
                weekly_tasks_ref = unified_ref.collection('weekly_tasks').document()
                weekly_tasks_ref.set({
                    'tasks': user_data['weekly_tasks'],
                    'created_at': int(time.time()),
                    'week_starting': self._get_week_start_timestamp(),
                    'instance_id': instance_id,
                    'status': 'active'
                })
            
            # Update unified collection
            if unified_doc.exists:
                unified_ref.update(sync_data)
            else:
                unified_ref.set(sync_data)
                
            logger.info(f"Successfully synced data for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error syncing to unified collection for user {user_id}: {e}", exc_info=True)
            # Mark sync as failed in instance collection
            try:
                instance_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                instance_ref.update({
                    'sync_status': 'failed',
                    'last_sync_error': str(e),
                    'last_sync_attempt': int(time.time())
                })
            except Exception as update_error:
                logger.error(f"Error marking sync failure: {update_error}", exc_info=True)

    def get_user_state(self, user_id: str, instance_id: str) -> Dict[str, Any]:
        """Get the current state and context of the user in the system."""
        try:
            if self.use_firestore:
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    context = user_data.get('context', {})
                    
                    # First check root level for planning_type
                    planning_type = user_data.get('planning_type')
                    logger.info(f"Root level planning_type for user {user_id}: {planning_type}")
                    
                    # If not at root, check context
                    if not planning_type:
                        planning_type = context.get('planning_type')
                        logger.info(f"Context level planning_type for user {user_id}: {planning_type}")
                    
                    # Log the final planning_type being used
                    logger.info(f"Using planning_type for user {user_id}: {planning_type}")
                    
                    return {
                        'state': user_data.get('state', 'INITIAL'),
                        'context': {
                            'flow_type': context.get('flow_type'),
                            'last_check_in': context.get('last_check_in'),
                            'last_task_update': context.get('last_task_update'),
                            'current_tasks': context.get('current_tasks', []),
                            'planning_type': planning_type,  # Use the planning_type we found
                            'emotional_state': context.get('emotional_state'),
                            'energy_level': context.get('energy_level'),
                            'pending_checkins': context.get('pending_checkins', []),
                            'current_checkin_source': context.get('current_checkin_source'),
                            'missed_checkins': context.get('missed_checkins', []),
                            'weekly_tasks': context.get('weekly_tasks', {}),
                            'daily_tasks': context.get('daily_tasks', []),
                            'focus_task': context.get('focus_task'),
                            'task_breakdown': context.get('task_breakdown', []),
                            'self_care_day': context.get('self_care_day', False),
                            'last_weekly_planning': context.get('last_weekly_planning'),
                            'daily_checkin_time': context.get('daily_checkin_time'),
                            'midday_checkin_time': context.get('midday_checkin_time'),
                            'endday_checkin_time': context.get('endday_checkin_time')
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
                            'missed_checkins': [],
                            'weekly_tasks': {},
                            'daily_tasks': [],
                            'focus_task': None,
                            'task_breakdown': [],
                            'self_care_day': False,
                            'last_weekly_planning': None,
                            'daily_checkin_time': None,
                            'midday_checkin_time': None,
                            'endday_checkin_time': None
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
                        'missed_checkins': [],
                        'weekly_tasks': {},
                        'daily_tasks': [],
                        'focus_task': None,
                        'task_breakdown': [],
                        'self_care_day': False,
                        'last_weekly_planning': None,
                        'daily_checkin_time': None,
                        'midday_checkin_time': None,
                        'endday_checkin_time': None
                    },
                    'last_state_update': int(time.time())
                })
                
        except Exception as e:
            logger.error(f"Error getting user state: {str(e)}")
            return {
                'state': 'INITIAL',
                'context': {},
                'last_state_update': int(time.time())
            }

    def update_user_state(self, user_id: str, new_state: str, instance_id: str, context_updates: dict = None) -> None:
        """Update user state and context in Firestore."""
        try:
            if not self.use_firestore:
                logger.warning("Firestore not available")
                return
            
            # Get current user state first
            current_state = self.get_user_state(user_id, instance_id)
            
            # Initialize updates dictionary
            updates = {
                'state': new_state,
                'last_state_update': int(time.time())
            }
            
            # Handle context updates
            if context_updates:
                # Check if planning_type is in context_updates
                planning_type = context_updates.get('planning_type')
                
                # If planning_type exists in context_updates, move it to root level
                if planning_type is not None:
                    updates['planning_type'] = planning_type
                    # Remove from context_updates to avoid duplication
                    context_updates.pop('planning_type')
                elif current_state and current_state.get('planning_type'):
                    # Preserve existing root-level planning_type if it exists
                    updates['planning_type'] = current_state['planning_type']
                elif current_state and current_state.get('context', {}).get('planning_type'):
                    # If planning_type is in context, move it to root level
                    updates['planning_type'] = current_state['context']['planning_type']
                
                # Update context
                if not current_state or 'context' not in current_state:
                    updates['context'] = context_updates
                else:
                    # Merge with existing context
                    merged_context = current_state['context'].copy()
                    merged_context.update(context_updates)
                    updates['context'] = merged_context
            
            # Log the final updates
            logger.info(f"Root level planning_type for user {user_id}: {updates.get('planning_type')}")
            logger.info(f"Context level planning_type for user {user_id}: {updates.get('context', {}).get('planning_type')}")
            logger.info(f"Using planning_type for user {user_id}: {updates.get('planning_type')}")
            
            # Update in Firestore
            instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
            instance_user_ref.set(updates, merge=True)
            
            logger.info(f"Updated state for user {user_id} to {new_state}")
            
        except Exception as e:
            logger.error(f"Error updating user state: {str(e)}", exc_info=True)
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
                
                # First check daily_tasks
                daily_tasks = user_data.get('daily_tasks', [])
                if daily_tasks and 0 <= task_index < len(daily_tasks):
                    daily_tasks[task_index]['status'] = status
                    update_data = {
                        'daily_tasks': daily_tasks,
                        'last_interaction': datetime.now()
                    }
                    instance_user_ref.update(update_data)
                    logger.info(f"Updated task status in daily_tasks for user {user_id}")
                    return
                
                # Then check weekly_tasks if planning type is weekly
                if user_data.get('planning_type') == 'weekly':
                    day_name = datetime.now().strftime('%A').lower()
                    weekly_tasks = user_data.get('weekly_tasks', {})
                    today_tasks = weekly_tasks.get(day_name, [])
                    if today_tasks and 0 <= task_index < len(today_tasks):
                        today_tasks[task_index]['status'] = status
                        weekly_tasks[day_name] = today_tasks
                        update_data = {
                            'weekly_tasks': weekly_tasks,
                            'last_interaction': datetime.now()
                        }
                        instance_user_ref.update(update_data)
                        logger.info(f"Updated task status in weekly_tasks for user {user_id}")
                        return
                
                # Finally check regular tasks
                tasks = user_data.get('tasks', [])
                if tasks and 0 <= task_index < len(tasks):
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
                    instance_user_ref.update(update_data)
                    logger.info(f"Updated task status in regular tasks for user {user_id}")
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return
                
                user_data = memory_storage['users'][instance_key]
                
                # First check daily_tasks
                daily_tasks = user_data.get('daily_tasks', [])
                if daily_tasks and 0 <= task_index < len(daily_tasks):
                    daily_tasks[task_index]['status'] = status
                    memory_storage['users'][instance_key]['daily_tasks'] = daily_tasks
                    memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
                    return
                
                # Then check weekly_tasks if planning type is weekly
                if user_data.get('planning_type') == 'weekly':
                    day_name = datetime.now().strftime('%A').lower()
                    weekly_tasks = user_data.get('weekly_tasks', {})
                    today_tasks = weekly_tasks.get(day_name, [])
                    if today_tasks and 0 <= task_index < len(today_tasks):
                        today_tasks[task_index]['status'] = status
                        weekly_tasks[day_name] = today_tasks
                        memory_storage['users'][instance_key]['weekly_tasks'] = weekly_tasks
                        memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
                        return
                
                # Finally check regular tasks
                tasks = user_data.get('tasks', [])
                if tasks and 0 <= task_index < len(tasks):
                    tasks[task_index]['status'] = status
                    
                    # Update metrics
                    metrics = user_data.get('metrics', {})
                    if status == 'completed':
                        metrics['completed_tasks'] = metrics.get('completed_tasks', 0) + 1
                        metrics['completion_rate'] = (metrics['completed_tasks'] / metrics['total_tasks']) * 100 if metrics['total_tasks'] > 0 else 0
                    
                    memory_storage['users'][instance_key]['tasks'] = tasks
                    memory_storage['users'][instance_key]['last_interaction'] = datetime.now()
                    memory_storage['users'][instance_key]['metrics'] = metrics
                    
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}", exc_info=True)
            raise

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
        
    def _get_tasks_from_data(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Helper method to get tasks from user data."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Layer 1: Check for focus task first
        focus_task = user_data.get('focus_task')
        if focus_task:
            created_at = focus_task.get('created_at')
            if created_at:
                task_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                if task_date == today:
                    logger.info(f"Found focus task for today: {focus_task}")
                    return [focus_task]  # Return only the focus task if it exists for today
        
        # Layer 2: Get tasks based on planning type
        planning_type = user_data.get('planning_type')
        logger.info(f"Getting daily tasks with planning type: {planning_type}")
        
        # First check daily_tasks field
        daily_tasks = user_data.get('daily_tasks', [])
        if daily_tasks:
            logger.info(f"Found {len(daily_tasks)} daily tasks")
            return daily_tasks
            
        # Then check weekly_tasks if planning type is weekly
        if planning_type == 'weekly':
            day_name = datetime.now().strftime('%A').lower()
            weekly_tasks = user_data.get('weekly_tasks', {})
            today_tasks = weekly_tasks.get(day_name, [])
            if today_tasks:
                logger.info(f"Found {len(today_tasks)} weekly tasks for {day_name}")
                return today_tasks
        
        # Finally check regular tasks field and filter by creation date
        tasks = user_data.get('tasks', [])
        today_tasks = []
        for task in tasks:
            # If task already has a status, include it
            if 'status' in task:
                today_tasks.append(task)
                continue
                
            # Otherwise check creation date
            created_at = task.get('created_at')
            if created_at:
                task_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
                if task_date == today:
                    today_tasks.append(task)
                    
        logger.info(f"Found {len(today_tasks)} tasks in regular tasks array")
        return today_tasks

    def get_daily_tasks(self, user_id: str, instance_id: str = 'default') -> List[Dict[str, Any]]:
        """Get the user's tasks for the current day."""
        try:
            if self.use_firestore:
                # First try instance-specific collection
                user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    daily_tasks = user_data.get('daily_tasks', [])
                    if daily_tasks:
                        logger.info(f"Found {len(daily_tasks)} tasks in instance collection")
                        return daily_tasks
                
                # If no tasks found in instance collection, try unified collection
                logger.info("No tasks found in instance collection, trying unified collection")
                tasks_ref = self.db.collection('users').document(user_id).collection('daily_tasks')
                query = tasks_ref.where('date', '==', datetime.now().strftime('%Y-%m-%d')).where('status', '==', 'active')
                
                docs = query.get()
                if docs:
                    for doc in docs:
                        task_data = doc.to_dict()
                        tasks = task_data.get('tasks', [])
                        if tasks:
                            logger.info(f"Found {len(tasks)} tasks in unified collection")
                            
                            # Sync back to instance collection
                            try:
                                user_ref.set({
                                    'daily_tasks': tasks,
                                    'last_sync': int(time.time()),
                                    'sync_status': 'synced'
                                }, merge=True)
                                logger.info("Successfully synced tasks back to instance collection")
                            except Exception as sync_error:
                                logger.error(f"Error syncing tasks back to instance collection: {sync_error}", exc_info=True)
                            
                            return tasks
                
                logger.info("No tasks found in either collection")
                return []
                
            else:
                # Fallback to in-memory storage
                instance_key = f"{instance_id}:{user_id}"
                if instance_key not in memory_storage['users']:
                    return []
                
                user_data = memory_storage['users'][instance_key]
                return self._get_tasks_from_data(user_data)
                
        except Exception as e:
            logger.error(f"Error getting daily tasks: {e}", exc_info=True)
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

    def store_weekly_tasks(self, user_id: str, tasks_by_day: dict, instance_id: str) -> None:
        """Store weekly tasks for a user."""
        try:
            logger.info(f"[STORE_WEEKLY] Starting to store weekly tasks for user {user_id}")
            
            # Tasks are already formatted with status, just store them as is
            logger.info(f"[STORE_WEEKLY] Formatted tasks: {tasks_by_day}")
            
            # Store in unified collection
            logger.info(f"[STORE_WEEKLY] Storing in unified collection /users/{user_id}/weekly_tasks/")
            user_ref = self.db.collection('users').document(user_id)
            weekly_tasks_ref = user_ref.collection('weekly_tasks').document()
            weekly_tasks_ref.set({
                'tasks': tasks_by_day,
                'created_at': int(time.time()),
                'week_starting': self._get_week_start_timestamp(),
                'instance_id': instance_id,
                'status': 'active'
            })
            logger.info(f"[STORE_WEEKLY] Successfully stored in unified collection")
            
            # Also store in instance-specific collection
            logger.info(f"[STORE_WEEKLY] Storing in instance collection /instances/{instance_id}/users/{user_id}")
            instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
            instance_user_ref.update({
                'weekly_tasks': tasks_by_day,
                'last_weekly_planning': int(time.time()),
                'planning_type': 'weekly'
            })
            logger.info(f"[STORE_WEEKLY] Successfully stored in instance collection")
            
            logger.info(f"[STORE_WEEKLY] Completed storing weekly tasks for user {user_id}")
            
        except Exception as e:
            logger.error(f"[STORE_WEEKLY] Error storing weekly tasks for user {user_id}: {e}", exc_info=True)
            raise

    def _get_week_start_timestamp(self) -> int:
        """Get the timestamp for the start of the current week (Monday)."""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(monday.timestamp())

    def get_weekly_tasks(self, user_id: str, instance_id: str, day: str) -> List[Dict[str, Any]]:
        """Get the user's tasks for a specific day from their weekly plan."""
        try:
            logger.info(f"[GET_WEEKLY] Starting to retrieve tasks for user {user_id} for {day}")
            
            if not self.use_firestore:
                logger.warning("[GET_WEEKLY] Firestore not available")
                return []
                
            # First try instance-specific collection
            logger.info(f"[GET_WEEKLY] Trying instance collection first: /instances/{instance_id}/users/{user_id}")
            instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
            user_doc = instance_user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                weekly_tasks = user_data.get('weekly_tasks', {})
                tasks = weekly_tasks.get(day, [])
                if tasks:
                    logger.info(f"[GET_WEEKLY] Found {len(tasks)} tasks in instance collection: {tasks}")
                    return tasks
                logger.info("[GET_WEEKLY] No tasks found in instance collection")
            else:
                logger.info("[GET_WEEKLY] User document not found in instance collection")
            
            # If no tasks found, try unified collection
            logger.info(f"[GET_WEEKLY] Trying unified collection: /users/{user_id}/weekly_tasks")
            user_ref = self.db.collection('users').document(user_id)
            weekly_tasks_ref = user_ref.collection('weekly_tasks')
            query = weekly_tasks_ref.where('status', '==', 'active').order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
            
            docs = query.get()
            if not docs:
                logger.info(f"[GET_WEEKLY] No active weekly plan found in unified collection")
                return []
                
            # Get the tasks for the specified day
            weekly_plan = docs[0].to_dict()
            tasks = weekly_plan.get('tasks', {}).get(day, [])
            logger.info(f"[GET_WEEKLY] Found tasks in unified collection: {tasks}")
            
            # If tasks found in unified but not in instance collection,
            # update the instance collection
            if tasks and not user_doc.exists:
                logger.info("[GET_WEEKLY] Syncing tasks from unified to instance collection")
                instance_user_ref.update({
                    'weekly_tasks': weekly_plan.get('tasks', {}),
                    'last_weekly_planning': weekly_plan.get('created_at'),
                    'planning_type': 'weekly'
                })
                logger.info("[GET_WEEKLY] Successfully synced tasks to instance collection")
            
            logger.info(f"[GET_WEEKLY] Returning {len(tasks)} tasks for {day}")
            return tasks
            
        except Exception as e:
            logger.error(f"[GET_WEEKLY] Error getting weekly tasks for user {user_id}: {e}", exc_info=True)
            return [] 

    def should_send_checkin(self, user_id: str, instance_id: str) -> bool:
        """Check if it's time to send a check-in message to the user."""
        try:
            # Get user's state
            user_state = self.get_user_state(user_id, instance_id)
            if not user_state:
                logger.info("No user state found, assuming check-in needed")
                return True
                
            # Get last check-in time
            last_checkin = user_state.get('context', {}).get('last_check_in')
            if last_checkin is None:
                logger.info("No last check-in time found, assuming check-in needed")
                return True
                
            current_time = int(time.time())
            
            # Check if it's been more than 6 hours since last check-in
            hours_since_checkin = (current_time - last_checkin) / 3600
            
            # Get planning type
            planning_type = user_state.get('context', {}).get('planning_type')
            logger.info(f"Planning type: {planning_type}, Hours since last check-in: {hours_since_checkin}")
            
            if planning_type == 'weekly':
                # For weekly planning, check if it's a new day
                last_checkin_date = datetime.fromtimestamp(last_checkin).date()
                current_date = datetime.now().date()
                should_checkin = current_date > last_checkin_date
                logger.info(f"Weekly planning: Last check-in date: {last_checkin_date}, Current date: {current_date}, Should check-in: {should_checkin}")
                return should_checkin
            else:
                # For daily planning or undefined, check if it's been more than 6 hours
                should_checkin = hours_since_checkin >= 6
                logger.info(f"Daily planning: Hours since check-in: {hours_since_checkin}, Should check-in: {should_checkin}")
                return should_checkin
                
        except Exception as e:
            logger.error(f"Error checking if should send check-in: {e}", exc_info=True)
            return False 

    def store_daily_tasks(self, user_id: str, tasks: List[Dict], instance_id: str) -> None:
        """Store daily tasks for a user."""
        try:
            logger.info(f"[STORE_DAILY] Starting to store daily tasks for user {user_id}")
            logger.info(f"[STORE_DAILY] Tasks to store: {tasks}")
            
            # First store in instance-specific collection
            logger.info(f"[STORE_DAILY] Storing in instance collection /instances/{instance_id}/users/{user_id}")
            instance_user_ref = self.db.collection('instances').document(instance_id).collection('users').document(user_id)
            
            # Get current user data to preserve other fields
            user_doc = instance_user_ref.get()
            current_data = user_doc.to_dict() if user_doc.exists else {}
            
            # Update with new tasks while preserving other fields
            update_data = {
                'daily_tasks': tasks,
                'last_daily_planning': int(time.time()),
                'last_interaction': datetime.now()
            }
            
            # Merge with existing data
            update_data.update({k: v for k, v in current_data.items() if k not in update_data})
            
            # Update instance collection
            instance_user_ref.set(update_data, merge=True)
            logger.info(f"[STORE_DAILY] Successfully stored in instance collection")
            
            # Then store in unified collection
            logger.info(f"[STORE_DAILY] Storing in unified collection /users/{user_id}/daily_tasks/")
            user_ref = self.db.collection('users').document(user_id)
            daily_tasks_ref = user_ref.collection('daily_tasks').document()
            
            # Store with additional metadata
            daily_tasks_ref.set({
                'tasks': tasks,
                'created_at': int(time.time()),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'instance_id': instance_id,
                'status': 'active',
                'sync_status': 'synced',
                'last_sync': int(time.time())
            })
            logger.info(f"[STORE_DAILY] Successfully stored in unified collection")
            
            logger.info(f"[STORE_DAILY] Completed storing daily tasks for user {user_id}")
            
        except Exception as e:
            logger.error(f"[STORE_DAILY] Error storing daily tasks for user {user_id}: {e}", exc_info=True)
            # If instance collection update failed, don't proceed with unified collection
            if 'instance_user_ref' not in locals() or not instance_user_ref.get().exists:
                raise
            
            # If instance update succeeded but unified failed, mark for sync
            try:
                instance_user_ref.update({
                    'sync_status': 'pending',
                    'last_sync_error': str(e),
                    'last_sync_attempt': int(time.time())
                })
            except Exception as sync_error:
                logger.error(f"[STORE_DAILY] Error marking sync status: {sync_error}", exc_info=True)
            raise 