from datetime import datetime, timedelta, timezone
import time
from app.services.firebase import db
from firebase_admin import firestore

class User:
    def __init__(self, user_id, name, account_index=1):
        self.user_id = user_id
        self.name = name
        self.account_index = account_index
        self.planning_schedule = 'daily'  # 'daily' or 'weekly'
        self.weekly_tasks = []  # For users on weekly schedule
        self.last_weekly_checkin = None  # Unix timestamp
        self.last_week_sentiment = None
        self.state = None
        self.last_state_update = None  # Unix timestamp

    @staticmethod
    def get_all():
        """Get all users from the database"""
        users = []
        for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
            users_ref = db.collection('instances').document(instance_id).collection('users')
            for user_doc in users_ref.stream():
                user_data = user_doc.to_dict()
                # Extract the instance number from instance_id (e.g., 'instance1' -> 1)
                account_index = int(instance_id.replace('instance', ''))
                user = User(
                    user_id=user_doc.id,
                    name=user_data.get('name', ''),
                    account_index=account_index
                )
                user.planning_schedule = user_data.get('planning_schedule', 'daily')
                user.weekly_tasks = user_data.get('weekly_tasks', [])
                user.last_weekly_checkin = user_data.get('last_weekly_checkin')
                user.last_week_sentiment = user_data.get('last_week_sentiment')
                user.state = user_data.get('state')
                user.last_state_update = user_data.get('last_state_update')
                users.append(user)
        return users

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

    def update_user_state(self, new_state: str = None, force_timestamp_update: bool = False):
        """Update the user's state and last_state_update timestamp using a transaction."""
        @firestore.transactional
        def update_state_in_transaction(transaction, user_ref):
            snapshot = user_ref.get(transaction=transaction)
            if not snapshot.exists:
                return
            
            update_data = {}
            if new_state is not None:
                self.state = new_state
                update_data['state'] = new_state
            
            if new_state is not None or force_timestamp_update:
                current_time = int(time.time())
                self.last_state_update = current_time
                update_data['last_state_update'] = current_time
            
            if update_data:
                transaction.update(user_ref, update_data)
        
        # Start transaction
        transaction = db.transaction()
        user_ref = db.collection('instances').document(f'instance{self.account_index}').collection('users').document(self.user_id)
        update_state_in_transaction(transaction, user_ref)

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
 