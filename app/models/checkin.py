from datetime import datetime
from app.services.firebase import db

class CheckIn:
    TYPE_MORNING = 'morning'
    TYPE_MIDDAY = 'midday'
    TYPE_EVENING = 'evening'
    TYPE_WEEKLY = 'weekly'

    def __init__(self, user_id, timestamp=None, sentiment=None, energy_level=None, stress_level=None, emotions=None):
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now()
        self.sentiment = sentiment
        self.energy_level = energy_level
        self.stress_level = stress_level
        self.emotions = emotions or []

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'sentiment': self.sentiment,
            'energy_level': self.energy_level,
            'stress_level': self.stress_level,
            'emotions': self.emotions
        }

    @staticmethod
    def from_dict(data):
        return CheckIn(
            user_id=data.get('user_id'),
            timestamp=data.get('timestamp'),
            sentiment=data.get('sentiment'),
            energy_level=data.get('energy_level'),
            stress_level=data.get('stress_level'),
            emotions=data.get('emotions', [])
        )

    def save(self):
        checkin_ref = db.collection('checkins').document()
        checkin_ref.set(self.to_dict())
        return checkin_ref.id

    @staticmethod
    def get_user_checkins(user_id, limit=10):
        checkins = []
        query = db.collection('checkins').where('user_id', '==', user_id).order_by('timestamp', direction='desc').limit(limit)
        for doc in query.stream():
            checkins.append(CheckIn.from_dict(doc.to_dict()))
        return checkins

    @staticmethod
    def create(user_id, message, check_in_type):
        """Create a new check-in record in Firebase"""
        check_in = CheckIn(
            user_id=user_id,
            timestamp=datetime.now(),
            sentiment=None,  # These will be updated later
            energy_level=None,
            stress_level=None,
            emotions=[]
        )
        check_in.save()
        return check_in 