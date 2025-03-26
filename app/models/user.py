from datetime import datetime, timedelta, timezone
import time
from app.services.firebase import db
from firebase_admin import firestore

class User:
    # Planning Types
    PLANNING_TYPE_WEEKLY = 'weekly'
    PLANNING_TYPE_DAILY = 'daily'
    
    # User States
    STATE_INITIAL = 'INITIAL'
    STATE_WEEKLY_REFLECTION = 'WEEKLY_REFLECTION'
    STATE_WEEKLY_TASK_INPUT = 'WEEKLY_TASK_INPUT'
    STATE_WEEKLY_PLANNING_COMPLETE = 'WEEKLY_PLANNING_COMPLETE'
    STATE_DAILY_CHECKIN = 'DAILY_CHECKIN'
    STATE_DAILY_TASK_INPUT = 'DAILY_TASK_INPUT'
    STATE_DAILY_TASK_BREAKDOWN = 'DAILY_TASK_BREAKDOWN'
    STATE_SELF_CARE_DAY = 'SELF_CARE_DAY'
    
    # Emotional States
    EMOTION_POSITIVE = 'positive'
    EMOTION_NEUTRAL = 'neutral'
    EMOTION_OVERWHELMED = 'overwhelmed'
    
    def __init__(self, user_id: str, name: str = None, account_index: int = 1):
        self.user_id = user_id
        self.name = name
        self.account_index = account_index
        self.state = None
        self.context = {
            'flow_type': None,
            'last_check_in': None,  # Timestamp of last check-in
            'last_task_update': None,
            'current_tasks': [],
            'planning_type': None,  # 'weekly' or 'daily'
            'emotional_state': None,
            'energy_level': None,
            'pending_checkins': [],
            'current_checkin_source': None,
            'missed_checkins': [],
            'weekly_tasks': {},  # Dictionary of tasks by day
            'daily_tasks': [],   # List of tasks for today
            'focus_task': None,  # Single task for overwhelmed days
            'task_breakdown': [], # Steps for broken down task
            'self_care_day': False,
            'last_weekly_planning': None,
            'daily_checkin_time': None,
            'midday_checkin_time': None,
            'endday_checkin_time': None
        }
        
    @property
    def last_checkin(self):
        """Get the timestamp of the last check-in."""
        return self.context.get('last_check_in')
    
    @last_checkin.setter
    def last_checkin(self, timestamp):
        """Set the timestamp of the last check-in."""
        self.context['last_check_in'] = timestamp
    
    @property
    def planning_type(self):
        """Get the user's planning type."""
        return self.context.get('planning_type')
    
    @planning_type.setter
    def planning_type(self, value):
        """Set the user's planning type."""
        if value not in [self.PLANNING_TYPE_WEEKLY, self.PLANNING_TYPE_DAILY]:
            raise ValueError("Planning type must be 'weekly' or 'daily'")
        self.context['planning_type'] = value
    
    @property
    def emotional_state(self):
        """Get the user's emotional state."""
        return self.context.get('emotional_state')
    
    @emotional_state.setter
    def emotional_state(self, value):
        """Set the user's emotional state."""
        self.context['emotional_state'] = value
    
    @property
    def is_overwhelmed(self):
        """Check if user is in an overwhelmed state."""
        return self.emotional_state == self.EMOTION_OVERWHELMED
    
    @property
    def daily_tasks(self):
        """Get user's daily tasks."""
        return self.context.get('daily_tasks', [])
    
    @daily_tasks.setter
    def daily_tasks(self, tasks):
        """Set user's daily tasks."""
        self.context['daily_tasks'] = tasks
    
    @property
    def focus_task(self):
        """Get user's focus task for overwhelmed days."""
        return self.context.get('focus_task')
    
    @focus_task.setter
    def focus_task(self, task):
        """Set user's focus task."""
        self.context['focus_task'] = task
    
    @property
    def task_breakdown(self):
        """Get breakdown steps for focus task."""
        return self.context.get('task_breakdown', [])
    
    @task_breakdown.setter
    def task_breakdown(self, steps):
        """Set breakdown steps for focus task."""
        self.context['task_breakdown'] = steps
    
    @property
    def is_self_care_day(self):
        """Check if user is having a self-care day."""
        return self.context.get('self_care_day', False)
    
    @is_self_care_day.setter
    def is_self_care_day(self, value):
        """Set self-care day status."""
        self.context['self_care_day'] = value
    
    def get_tasks_for_day(self, day):
        """Get tasks for a specific day from weekly plan."""
        return self.context.get('weekly_tasks', {}).get(day, [])
    
    def set_tasks_for_day(self, day, tasks):
        """Set tasks for a specific day in weekly plan."""
        if 'weekly_tasks' not in self.context:
            self.context['weekly_tasks'] = {}
        self.context['weekly_tasks'][day] = tasks
    
    def to_dict(self):
        """Convert user object to dictionary for Firebase storage."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'account_index': self.account_index,
            'state': self.state,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create a User instance from a dictionary."""
        if not data:
            return None
            
        user = cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            account_index=data.get('account_index', 1)
        )
        user.state = data.get('state')
        user.context = data.get('context', {
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
        })
        return user
        
    def needs_checkin(self, current_time) -> bool:
        """
        Determine if user needs a check-in based on their last check-in time.
        
        Args:
            current_time: Current timestamp to compare against
            
        Returns:
            bool: True if user needs a check-in, False otherwise
        """
        if not self.last_checkin:
            return True
            
        # If it's been more than 20 hours since last check-in
        time_since_last = current_time - self.last_checkin
        return time_since_last >= (20 * 3600)  # 20 hours in seconds

    @staticmethod
    def get_all():
        """Get all users from Firebase."""
        try:
            from firebase_admin import firestore
            db = firestore.client()
            users_ref = db.collection('users')
            users = []
            
            for doc in users_ref.stream():
                user_data = doc.to_dict()
                user_data['user_id'] = doc.id
                user = User.from_dict(user_data)
                if user:
                    users.append(user)
            
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_or_create(user_id: str, instance_id: str) -> 'User':
        """Get a user by ID or create if not exists."""
        account_index = int(instance_id.replace('instance', ''))
        user_ref = db.collection('instances').document(instance_id).collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user = User(
                user_id=user_id,
                name=user_data.get('name', ''),
                account_index=account_index
            )
            user.planning_schedule = user_data.get('planning_schedule', 'daily')
            user.weekly_tasks = user_data.get('weekly_tasks', [])
            user.last_weekly_checkin = user_data.get('last_weekly_checkin')
            user.last_week_sentiment = user_data.get('last_week_sentiment')
            user.state = user_data.get('state')
            user.last_state_update = user_data.get('last_state_update')
            return user
        else:
            # Create new user
            user = User(
                user_id=user_id,
                name=user_id,  # Use user_id as name initially
                account_index=account_index
            )
            user.save(instance_id)
            return user

    def get_last_week_sentiment(self):
        """Get the user's sentiment data from last week"""
        return self.last_week_sentiment

    def update_user_state(self, new_state: str):
        """Update user state and record the timestamp of the update."""
        try:
            from firebase_admin import firestore
            db = firestore.client()
            
            # Get the instance collection based on account_index
            instance_id = f'instance{self.account_index}'
            user_ref = db.collection('instances').document(instance_id).collection('users').document(self.user_id)
            
            # Update state and timestamp
            current_time = int(datetime.now().timestamp())
            user_ref.update({
                'state': new_state,
                'last_state_update': current_time
            })
            
            # Update local object
            self.state = new_state
            self.last_state_update = current_time
            
            logger.info(f"Updated state for user {self.user_id} to {new_state}")
            return True
        except Exception as e:
            logger.error(f"Failed to update state for user {self.user_id}: {str(e)}")
            return False

    def update_planning_schedule(self, schedule):
        """Update the user's planning schedule"""
        self.planning_schedule = schedule
        self.save(f'instance{self.account_index}')

    def set_weekly_tasks(self, tasks):
        """Set weekly tasks for users on weekly schedule"""
        self.weekly_tasks = tasks
        self.save(f'instance{self.account_index}')

    def save(self, instance_id: str):
        """Save user data to Firebase using a transaction."""
        @firestore.transactional
        def update_in_transaction(transaction, user_ref):
            # Read current data first
            snapshot = user_ref.get(transaction=transaction)
            current_data = snapshot.to_dict() if snapshot.exists else {}
            
            # Prepare new data
            new_data = {
                'name': self.name,
                'planning_schedule': self.planning_schedule,
                'weekly_tasks': self.weekly_tasks,
                'last_weekly_checkin': self.last_weekly_checkin,
                'last_week_sentiment': self.last_week_sentiment,
                'state': self.state,
                'last_state_update': self.last_state_update
            }
            
            # Only update fields that have changed
            update_data = {}
            for key, value in new_data.items():
                if key not in current_data or current_data[key] != value:
                    update_data[key] = value
            
            if update_data:
                transaction.set(user_ref, new_data, merge=True)
        
        # Start transaction
        transaction = db.transaction()
        user_ref = db.collection('instances').document(instance_id).collection('users').document(self.user_id)
        update_in_transaction(transaction, user_ref)

    def update_weekly_checkin(self, sentiment_data):
        """Update the user's weekly check-in data using a transaction."""
        @firestore.transactional
        def update_checkin_in_transaction(transaction, user_ref):
            current_time = int(time.time())
            self.last_weekly_checkin = current_time
            self.last_week_sentiment = sentiment_data
            
            transaction.update(user_ref, {
                'last_weekly_checkin': current_time,
                'last_week_sentiment': sentiment_data
            })
        
        # Start transaction
        transaction = db.transaction()
        user_ref = db.collection('instances').document(f'instance{self.account_index}').collection('users').document(self.user_id)
        update_checkin_in_transaction(transaction, user_ref) 
 