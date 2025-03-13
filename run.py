from app import create_app
import schedule
import time
from app.services.whatsapp_service import WhatsAppService
from app.services.task_service import TaskService
from datetime import datetime
import os

app = create_app()
whatsapp_service = WhatsAppService()
task_service = TaskService()

def send_daily_reminders():
    """Send daily task reminders to all users."""
    # This would be implemented to fetch all active users and send reminders
    pass

def schedule_reminders():
    """Schedule daily reminders."""
    schedule.every().day.at("09:00").do(send_daily_reminders)
    schedule.every().day.at("21:00").do(send_daily_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Start the reminder scheduler in a separate thread
    import threading
    scheduler_thread = threading.Thread(target=schedule_reminders, daemon=True)
    scheduler_thread.start()
    
    # Start the Flask application
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000))) 