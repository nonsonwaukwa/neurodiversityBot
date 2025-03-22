from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.whatsapp import get_whatsapp_service
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def send_weekly_checkin():
    """Your existing weekly check-in code"""
    # Your provided code here 