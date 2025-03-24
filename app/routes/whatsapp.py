from flask import Blueprint, request, jsonify
from app.services.whatsapp_service import WhatsAppService
from app.services.sentiment_service import SentimentService
from app.services.task_service import TaskService
from app.models.user import User
from firebase_admin import firestore
import os
import re
import time
from datetime import datetime, timedelta, timezone
import random
import logging

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
                        if message.get('type') == 'text':
                            user_id = message.get('from')
                            message_text = message.get('text', {}).get('body')
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
                            logger.info(f"Message text: {message_text}")
                            
                            try:
                                process_message(user_id, message_text, instance_id, instances[instance_id])
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

def generate_response(user: User, sentiment_data: dict) -> str:
    """Generate a response based on sentiment analysis."""
    name = user.name.split('_')[0] if '_' in user.name else user.name
    
    if sentiment_data.get('energy_level') == 'low':
        return (
            f"I hear you, {name}. It sounds like your energy is a bit low today, "
            "and that's completely okay. 💙\n\n"
            "Would you like to:\n"
            "1. Just rest and pick this up later?\n"
            "2. Break down your tasks into smaller, more manageable steps?\n"
            "3. Focus on just one simple task for now?\n\n"
            "You can reply with the number that feels right, or we can just chat about how you're feeling."
        )
    
    # Add more response types based on other sentiment patterns
    return None

def process_message(user_id: str, message_text: str, instance_id: str, services: dict):
    """Process an incoming message from a user."""
    logger.info(f"Processing message from user {user_id} in instance {instance_id}")
    
    try:
        # Get user's current state
        user_state_data = services['task'].get_user_state(user_id, instance_id)
        current_state = user_state_data.get('state')
        last_state_update = user_state_data.get('last_state_update')
        
        if isinstance(last_state_update, str):
            try:
                last_state_update = datetime.fromisoformat(last_state_update.replace('Z', '+00:00'))
            except ValueError:
                last_state_update = datetime.now(timezone.utc)
        elif last_state_update is None:
            last_state_update = datetime.now(timezone.utc)
        
        # Get or create user
        user = User.get_or_create(user_id, instance_id)
        if not user:
            logger.error(f"Failed to get/create user {user_id}")
            return
        
        # Handle weekly reflection (Sunday check-in)
        if current_state == 'WEEKLY_REFLECTION':
            # Analyze sentiment to understand emotional state
            analysis = services['sentiment'].analyze_weekly_checkin(message_text)
            logger.info(f"Weekly check-in analysis: {analysis}")
            
            # Generate response and determine planning type
            response_data = services['sentiment'].generate_weekly_response(analysis, user.name)
            response_message = response_data['message']
            planning_type = response_data['planning_type']
            
            # Update user's planning type if determined
            if planning_type:
                user.update_planning_schedule(planning_type)
                logger.info(f"Updated user {user_id} planning type to {planning_type}")
                
                # Update user state based on planning type
                if planning_type == 'daily':
                    services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
                elif planning_type == 'weekly':
                    services['task'].update_user_state(user_id, 'WEEKLY_TASK_SELECTION', instance_id)
            else:
                # If no planning type determined, we're asking for clarification
                services['task'].update_user_state(user_id, 'WEEKLY_REFLECTION', instance_id)
            
            # Send response
            services['whatsapp'].send_message(user_id, response_message)
            logger.info(f"Sent weekly check-in response to user {user_id}")
            
        else:
            # Handle other message types (daily check-ins, task updates, etc.)
            # ... existing code for other states ...
            pass
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise

# For backward compatibility, redirect instance-specific routes to the main webhook
@bp.route('/<instance_id>', methods=['GET'])
def verify_instance_webhook(instance_id: str):
    """Redirect to main webhook verification"""
    return verify_webhook()

@bp.route('/<instance_id>', methods=['POST'])
def instance_webhook(instance_id: str):
    """Redirect to main webhook handler"""
    return webhook()

def handle_check_in(user_id: str, message_text: str, instance_id: str, services: dict) -> str:
    """Handle user's check-in response"""
    # Check for task status updates
    status_match = re.match(r'(DONE|PROGRESS|STUCK)\s+(\d+)', message_text.upper())
    if status_match:
        status_type = status_match.group(1)
        task_num_str = status_match.group(2)
        
        try:
            task_num = int(task_num_str) - 1  # Convert to 0-based index
            
            # Get current tasks to validate task number
            tasks = services['task'].get_daily_tasks(user_id, instance_id)
            if task_num < 0 or task_num >= len(tasks):
                return f"Hmm, I don't see task #{task_num_str} on your list. Want to try again or type 'TASKS' to see your current list?"
            
            # Get the task name for personalized response
            task_name = tasks[task_num]['task']
            
            status_map = {
                'DONE': 'completed',
                'PROGRESS': 'in_progress',
                'STUCK': 'stuck'
            }
            
            services['task'].update_task_status(user_id, task_num, status_map[status_type], instance_id)
            
            if status_type == 'DONE':
                # Vary responses to avoid repetition
                responses = [
                    f"🎉 Yes! You completed '{task_name}'! That's a genuine win - how did it feel to finish that one?",
                    f"✨ Amazing job finishing '{task_name}'! What helped you get this done today?",
                    f"💪 '{task_name}' → DONE! That's awesome progress. Would you like to take a moment to celebrate?"
                ]
                return random.choice(responses)
            elif status_type == 'PROGRESS':
                responses = [
                    f"👍 Thanks for letting me know you're working on '{task_name}'. Taking those first steps can be the hardest part!",
                    f"🔄 Got it - '{task_name}' is in progress. Remember, consistent effort matters more than perfect execution.",
                    f"⏳ '{task_name}' in progress - that's great! Is there anything that would make this task flow better for you?"
                ]
                return random.choice(responses)
            else:  # STUCK
                return (
                    f"I hear you're feeling stuck with '{task_name}'. That happens to everyone, especially with complicated or less interesting tasks.\n\n"
                    f"Would you like to:\n"
                    f"1. Break this down into smaller steps?\n"
                    f"2. Talk about what specific part feels challenging?\n"
                    f"3. Get some motivation or a different approach?\n"
                    f"4. Set this aside for now and come back to it later?"
                )
        except ValueError:
            return "I didn't quite catch which task number you meant. Could you try again with something like 'DONE 1' or 'STUCK 2'?"
    
    # If we get here, it's a general message during CHECK_IN state
    # Analyze sentiment to provide an empathetic response
    sentiment = services['sentiment'].analyze_sentiment(message_text)
    
    # Get current tasks
    tasks = services['task'].get_daily_tasks(user_id, instance_id)
    completed = sum(1 for task in tasks if task.get('status') == 'completed')
    
    # Create a contextual response based on progress and sentiment
    if not tasks:
        return "We haven't set any tasks for today yet. Would you like to share what you'd like to focus on?"
    
    # Format task list with status indicators
    task_list = '\n'.join([
        f"{i+1}. {'✅' if task['status'] == 'completed' else '⭐'} {task['task']}" 
        for i, task in enumerate(tasks)
    ])
    
    # Varied responses based on progress
    if completed == 0:
        if sentiment.get('sentiment') == 'negative':
            return (
                f"I hear things might be tough right now. That's okay - some days are harder than others.\n\n"
                f"Here are your tasks when you're ready:\n\n{task_list}\n\n"
                f"Even small progress counts. Is there something specific making today challenging?"
            )
        else:
            return (
                f"Here's what we're focusing on today:\n\n{task_list}\n\n"
                f"How's it going so far? Remember, you can update me anytime with 'DONE', 'PROGRESS', or 'STUCK'."
            )
    elif completed == len(tasks):
        return (
            f"🎊 Wow! You've completed all your tasks!\n\n{task_list}\n\n"
            f"That's seriously impressive. How are you feeling about what you've accomplished? Would you like to set any new goals or take some well-deserved rest?"
        )
    else:
        return (
            f"Here's where things stand:\n\n{task_list}\n\n"
            f"You've completed {completed}/{len(tasks)} tasks - that's progress to be proud of! How are you feeling about the rest? Anything I can help with?"
        ) 