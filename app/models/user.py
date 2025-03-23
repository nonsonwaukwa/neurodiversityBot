from datetime import datetime, timedelta
from app.services.firebase import db

class User:
    def __init__(self, user_id, name, account_index=1):
        self.user_id = user_id
        self.name = name
        self.account_index = account_index
        self.planning_schedule = 'daily'  # 'daily' or 'weekly'
        self.weekly_tasks = []  # For users on weekly schedule
        self.last_weekly_checkin = None
        self.last_week_sentiment = None
        self.state = None

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
            return user
        else:
            # Create new user
            user = User(
                user_id=user_id,
                name=user_id,  # Use user_id as name initially
                account_index=account_index
            )
            user.save()
            return user

    def get_last_week_sentiment(self):
        """Get the user's sentiment data from last week"""
        return self.last_week_sentiment

    def update_user_state(self, new_state):
        """Update the user's state in the database"""
        instance_id = f'instance{self.account_index}'
        user_ref = db.collection('instances').document(instance_id).collection('users').document(self.user_id)
        user_ref.update({
            'state': new_state,
            'last_state_update': datetime.now()
        })
        self.state = new_state

    def update_planning_schedule(self, schedule):
        """Update the user's planning schedule"""
        self.planning_schedule = schedule
        self.save()

    def set_weekly_tasks(self, tasks):
        """Set weekly tasks for users on weekly schedule"""
        self.weekly_tasks = tasks
        self.save()

    def save(self):
        """Save user data to the database"""
        instance_id = f'instance{self.account_index}'
        user_ref = db.collection('instances').document(instance_id).collection('users').document(self.user_id)
        user_ref.set({
            'name': self.name,
            'planning_schedule': self.planning_schedule,
            'weekly_tasks': self.weekly_tasks,
            'last_weekly_checkin': self.last_weekly_checkin,
            'last_week_sentiment': self.last_week_sentiment,
            'state': self.state,
            'updated_at': datetime.now().isoformat()
        }, merge=True)

    def update_weekly_checkin(self, sentiment_data):
        """Update the user's weekly check-in data"""
        self.last_weekly_checkin = datetime.now().isoformat()
        self.last_week_sentiment = sentiment_data
        self.save() 
 