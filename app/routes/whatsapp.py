from flask import Blueprint, request, jsonify
from app.services.whatsapp_service import WhatsAppService
from app.services.sentiment_service import SentimentService
from app.services.task_service import TaskService
from app.models.user import User
from app.utils.validation import parse_task_input, validate_task_input
from firebase_admin import firestore
import os
import re
import time
from datetime import datetime, timedelta, timezone
import random
import logging
import json
from app.models.checkin import CheckIn
from app.handlers.checkins import DailyCheckinHandler, WeeklyCheckinHandler, MiddayCheckinHandler
from app.handlers.support_handler import SupportHandler
from app.handlers.task_handler import TaskHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('whatsapp', __name__, url_prefix='/webhook')

# Initialize services for each instance
instances = {}
for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
    instances[instance_id] = {
        'whatsapp': WhatsAppService(instance_id),
        'sentiment': SentimentService(),
        'task': TaskService()
    }

# Initialize Firestore
db = firestore.client()

# Phone number to instance mapping
phone_number_mapping = {
    # Instance 1 phone numbers
    os.getenv('WHATSAPP_PHONE_NUMBER_ID_INSTANCE1'): 'instance1',
    
    # Instance 2 phone numbers
    os.getenv('WHATSAPP_PHONE_NUMBER_ID_INSTANCE2'): 'instance2',
}

# Message deduplication cache
# Structure: {'message_id': {'timestamp': unix_time, 'processed': True/False}}
message_cache = {}

# Clean message cache every 5 minutes
def clean_message_cache():
    """Remove messages older than 30 minutes from the cache"""
    current_time = time.time()
    expired_ids = []
    
    for msg_id, data in message_cache.items():
        # If message is older than 30 minutes, mark for removal
        if current_time - data['timestamp'] > 1800:  # 30 minutes in seconds
            expired_ids.append(msg_id)
    
    # Remove expired messages
    for msg_id in expired_ids:
        del message_cache[msg_id]
    
    print(f"Cleaned message cache. Removed {len(expired_ids)} expired messages. Current cache size: {len(message_cache)}")

def get_instance_from_phone_number(phone_number: str) -> str:
    """Determine which instance a phone number belongs to."""
    # First, check if we have an explicit mapping
    instance = phone_number_mapping.get(phone_number)
    if instance:
        return instance
        
    # Fallback to instance1 if not found
    print(f"Warning: No instance mapping found for phone number {phone_number}. Using instance1.")
    return 'instance1'

def is_message_processed(message_id: str, instance_id: str) -> bool:
    """Check if a message has already been processed using Firebase."""
    try:
        doc_ref = db.collection('processed_messages').document(message_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking message status: {str(e)}")
        return False

def is_message_recent(timestamp: int) -> bool:
    """Check if a message is recent (within the last 6 hours)."""
    current_time = int(time.time())
    message_age = current_time - timestamp
    # Only process messages less than 6 hours old
    return message_age < 21600  # 6 hours in seconds

def mark_message_processed(message_id: str, instance_id: str, timestamp: int):
    """Mark a message as processed in Firebase."""
    try:
        doc_ref = db.collection('processed_messages').document(message_id)
        doc_ref.set({
            'instance_id': instance_id,
            'timestamp': timestamp,
            'processed_at': int(time.time())
        })
    except Exception as e:
        logger.error(f"Error marking message as processed: {str(e)}")

@bp.route('/', methods=['GET'])
def verify_webhook():
    """Handle webhook verification from WhatsApp for all instances"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Verify using the common token
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
    
    if mode and token and mode == 'subscribe' and token == verify_token:
        print(f"Webhook verified with token!")
        return challenge
    
    return jsonify({'error': 'Invalid verification token'}), 403

@bp.route('/', methods=['POST'])
def webhook():
    """Handle incoming webhook events from WhatsApp."""
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        
        if 'entry' not in data or not data['entry']:
            logger.warning("No valid entry in webhook data")
            return jsonify({'status': 'ok'})
            
        for entry in data['entry']:
            if 'changes' not in entry:
                continue
                
            for change in entry['changes']:
                if 'value' not in change:
                    continue
                    
                value = change['value']
                logger.info(f"Processing value: {value}")
                
                # Handle message events
                if 'messages' in value:
                    for message in value['messages']:
                        user_id = message.get('from')
                        message_id = message.get('id')
                        timestamp = int(message.get('timestamp', time.time()))
                        
                        # Skip old messages
                        if not is_message_recent(timestamp):
                            logger.info(f"Skipping old message {message_id} from timestamp {timestamp}")
                            continue
                        
                        # Check for message deduplication using Firebase
                        phone_number_id = value.get('metadata', {}).get('phone_number_id')
                        instance_id = get_instance_from_phone_number(phone_number_id)
                        
                        if is_message_processed(message_id, instance_id):
                            logger.info(f"Skipping duplicate message {message_id}")
                            continue
                        
                        logger.info(f"Processing message {message_id} for instance {instance_id}")
                        
                        # Handle different message types
                        if message.get('type') == 'text':
                            message_text = message.get('text', {}).get('body')
                            logger.info(f"Message text: {message_text}")
                        elif message.get('type') == 'interactive':
                            # Pass the entire interactive message object
                            message_text = message
                            logger.info(f"Interactive message: {message}")
                        else:
                            logger.warning(f"Unsupported message type: {message.get('type')}")
                            continue
                        
                        try:
                            handle_message(message_id, user_id, message_text, instance_id, instances[instance_id])
                            mark_message_processed(message_id, instance_id, timestamp)
                            logger.info(f"Successfully processed message {message_id}")
                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {str(e)}")
                            raise
                                
                elif 'statuses' in value:
                    # Only log recent status updates
                    for status in value['statuses']:
                        status_timestamp = int(status.get('timestamp', time.time()))
                        if is_message_recent(status_timestamp):
                            logger.info(f"Received status update: {status}")
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_instance_id(phone_number_id: str) -> str:
    """Map phone number ID to instance ID."""
    phone_number_mapping = {
        '556928390841439': 'instance1',
        '596255043571188': 'instance2'
    }
    return phone_number_mapping.get(phone_number_id)

def handle_message(message_id: str, user_id: str, message_text: str, instance_id: str, services: dict):
    """Handle incoming WhatsApp message."""
    try:
        # Initialize handlers
        daily_handler = DailyCheckinHandler(services['whatsapp'], services['task'], services['sentiment'])
        weekly_handler = WeeklyCheckinHandler(services['whatsapp'], services['task'], services['sentiment'])
        midday_handler = MiddayCheckinHandler(services['whatsapp'], services['task'], services['sentiment'], services['task'])
        support_handler = SupportHandler(services['whatsapp'], services['task'], services['sentiment'])
        
        # Get user's current state and context using daily handler
        context = daily_handler.get_user_context(user_id, instance_id)
        current_state = context.get('state', 'INITIAL')
        logger.info(f"User state: {current_state}, Planning type: {context.get('planning_type')}")
        
        try:
            # Handle interactive messages (button responses)
            if (isinstance(message_text, dict) and 
                message_text.get('type') == 'interactive' and 
                message_text.get('interactive', {}).get('type') == 'button_reply'):
                
                button_response = message_text['interactive']['button_reply']
                logger.info(f"Processing button response: {button_response} for state: {current_state}")
                
                # Route button responses based on state
                if current_state == 'AWAITING_PLANNING_CHOICE':
                    weekly_handler.handle_weekly_reflection(user_id, message_text, instance_id, context)
                    return
                elif current_state == 'AWAITING_SUPPORT_CHOICE':
                    logger.info("Routing to daily handler for support choice")
                    daily_handler.handle_support_choice(message_text, user_id, instance_id, context)
                    return
                elif current_state == 'MIDDAY_CHECK_IN':
                    logger.info("Routing to midday handler for button response")
                    midday_handler.handle_midday_button_response(user_id, message_text, instance_id, context)
                    return
            
            # Handle text message states
            if current_state == 'DAILY_TASK_INPUT':
                logger.info(f"Processing daily task input: {message_text}")
                daily_handler.handle_daily_task_input(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'SMALL_TASK_INPUT':
                logger.info(f"Processing small task input: {message_text}")
                daily_handler.handle_small_task_input(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'THERAPEUTIC_CONVERSATION':
                support_handler.handle_therapeutic_conversation(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'SELF_CARE_DAY':
                support_handler.handle_self_care_day(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'WEEKLY_TASK_INPUT':
                weekly_handler.handle_weekly_task_input(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'MIDDAY_CHECK_IN':
                midday_handler.handle_midday_checkin(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'WEEKLY_REFLECTION':
                weekly_handler.handle_weekly_reflection(user_id, message_text, instance_id, context)
                return
            
            if current_state == 'TASK_UPDATE':
                # Check if this is a task status update command
                if isinstance(message_text, str) and re.match(r'^(DONE|PROGRESS|STUCK)\s+(\d+)$', message_text.strip().upper()):
                    response = midday_handler.handle_check_in(user_id, message_text, instance_id)
                    services['whatsapp'].send_message(user_id, response)
                    return
                # If not a task command, handle as regular midday check-in
                midday_handler.handle_midday_checkin(user_id, message_text, instance_id, context)
                return
            
            # Default to daily check-in for unhandled states
            daily_handler.handle_daily_checkin(user_id, message_text, instance_id, context)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            services['whatsapp'].send_message(
                user_id,
                "I'm not sure how to help with that. Would you like to:\n"
                "• Check your tasks\n"
                "• Start fresh with a new check-in\n"
                "• Get some support"
            )
            
        logger.info(f"Successfully processed message {message_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
        try:
            services['whatsapp'].send_message(
                user_id,
                "I encountered an error. Let's start fresh - how are you feeling today?"
            )
        except Exception as send_error:
            logger.error(f"Error sending error message: {str(send_error)}", exc_info=True)

# For backward compatibility, redirect instance-specific routes to the main webhook
@bp.route('/<instance_id>', methods=['GET'])
def verify_instance_webhook(instance_id: str):
    """Redirect to main webhook verification"""
    return verify_webhook()

@bp.route('/<instance_id>', methods=['POST'])
def instance_webhook(instance_id: str):
    """Redirect to main webhook handler"""
    return webhook()