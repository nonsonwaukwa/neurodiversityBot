from datetime import datetime, timedelta
from app.services.firebase import db

class User:
    def __init__(self, user_id, name, account_index=0):
        self.user_id = user_id
        self.name = name
        self.account_index = account_index
        self.planning_schedule = 'daily'  # 'daily' or 'weekly'
        self.weekly_tasks = []  # For users on weekly schedule
        self.last_weekly_checkin = None
        self.last_week_sentiment = None

    @staticmethod
    def get_all():
        """Get all users from the database"""
        users = []
        for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
            users_ref = db.collection('instances').document(instance_id).collection('users')
            for user_doc in users_ref.stream():
                user_data = user_doc.to_dict()
                user = User(
                    user_id=user_doc.id,
                    name=user_data.get('name', ''),
                    account_index=0 if instance_id == 'instance1' else 1
                )
                user.planning_schedule = user_data.get('planning_schedule', 'daily')
                user.weekly_tasks = user_data.get('weekly_tasks', [])
                user.last_weekly_checkin = user_data.get('last_weekly_checkin')
                user.last_week_sentiment = user_data.get('last_week_sentiment')
                users.append(user)
        return users

    def get_last_week_sentiment(self):
        """Get the user's sentiment data from last week"""
        return self.last_week_sentiment

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
        instance_id = 'instance1' if self.account_index == 0 else 'instance2'
        user_ref = db.collection('instances').document(instance_id).collection('users').document(self.user_id)
        user_ref.set({
            'name': self.name,
            'planning_schedule': self.planning_schedule,
            'weekly_tasks': self.weekly_tasks,
            'last_weekly_checkin': self.last_weekly_checkin,
            'last_week_sentiment': self.last_week_sentiment,
            'updated_at': datetime.now().isoformat()
        }, merge=True)

    def update_weekly_checkin(self, sentiment_data):
        """Update the user's weekly check-in data"""
        self.last_weekly_checkin = datetime.now().isoformat()
        self.last_week_sentiment = sentiment_data
        self.save() 
 