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
    logger.info(f"Message text: {message_text}")
    
    try:
        # Start typing indicator before processing
        services['whatsapp'].start_typing(user_id)
        
        # Get user's current state and context
        user_state_data = services['task'].get_user_state(user_id, instance_id)
        current_state = user_state_data.get('state')
        context = user_state_data.get('context', {})
        logger.info(f"Current user state: {current_state}")
        logger.info(f"Current context: {context}")
        
        # Get pending check-ins
        pending_checkins = context.get('pending_checkins', [])
        current_checkin = context.get('current_checkin_source')
        logger.info(f"Pending check-ins: {pending_checkins}")
        logger.info(f"Current check-in source: {current_checkin}")
        
        # Get or create user
        user = User.get_or_create(user_id, instance_id)
        if not user:
            logger.error(f"Failed to get/create user {user_id}")
            services['whatsapp'].stop_typing(user_id)
            return

        # For interactive messages, pass the entire message object
        if isinstance(message_text, dict) and message_text.get('type') == 'interactive':
            if current_state == 'WEEKLY_REFLECTION' or current_state == 'AWAITING_PLANNING_CHOICE':
                logger.info("Processing interactive response for weekly reflection")
                handle_weekly_reflection(user_id, message_text, instance_id, services, context)
                return
            # Add more interactive message handling for other states as needed
            return

        # Check for override commands first (these work in any state)
        command_match = re.match(r'^(DONE|PROGRESS|STUCK)\s+(\d+)$', message_text.upper())
        if command_match:
            logger.info(f"Detected task command: {command_match.group(0)}")
            response = handle_task_command(user_id, command_match, instance_id, services)
            services['whatsapp'].send_message(user_id, response)
            return

        # Handle based on current state first
        if current_state == 'WEEKLY_REFLECTION':
            logger.info("Processing weekly reflection based on state")
            handle_weekly_reflection(user_id, message_text, instance_id, services, context)
            return
        elif current_state == 'WEEKLY_TASK_INPUT':
            logger.info("Processing weekly task input based on state")
            handle_weekly_task_input(user_id, message_text, instance_id, services, context)
            return
        elif current_state == 'DAILY_CHECK_IN':
            logger.info("Processing daily check-in based on state")
            handle_daily_checkin(user_id, message_text, instance_id, services, context)
            return
        elif current_state == 'MIDDAY_CHECK_IN':
            logger.info("Processing midday check-in based on state")
            handle_midday_checkin(user_id, message_text, instance_id, services, context)
            return
        elif current_state == 'END_DAY_CHECK_IN':
            logger.info("Processing end-day check-in based on state")
            handle_end_day_checkin(user_id, message_text, instance_id, services, context)
            return

        # If no active state, check pending check-ins
        if pending_checkins:
            # Sort check-ins by time added
            sorted_checkins = sorted(pending_checkins, key=lambda x: x['added_at'])
            oldest_checkin = sorted_checkins[0]['type']
            logger.info(f"Processing oldest pending check-in: {oldest_checkin}")
            
            # If we're already in a check-in flow, continue with it
            if current_checkin:
                checkin_type = current_checkin
                logger.info(f"Continuing with current check-in: {checkin_type}")
            else:
                # Start with the oldest pending check-in
                checkin_type = oldest_checkin
                logger.info(f"Starting new check-in: {checkin_type}")
                # Update the current check-in source
                services['task'].update_user_state(
                    user_id,
                    current_state,
                    instance_id,
                    {'current_checkin_source': checkin_type}
                )

            # Handle the check-in based on type
            if checkin_type == services['task'].CHECK_IN_TYPES['WEEKLY']:
                logger.info("Handling weekly reflection from pending check-in")
                handle_weekly_reflection(user_id, message_text, instance_id, services, context)
                services['task'].resolve_checkin(user_id, checkin_type, instance_id)
                logger.info("Weekly reflection completed and resolved")
                
            elif checkin_type == services['task'].CHECK_IN_TYPES['DAILY']:
                logger.info("Handling daily check-in from pending check-in")
                handle_daily_checkin(user_id, message_text, instance_id, services, context)
                services['task'].resolve_checkin(user_id, checkin_type, instance_id)
                logger.info("Daily check-in completed and resolved")
                
            elif checkin_type == services['task'].CHECK_IN_TYPES['MIDDAY']:
                logger.info("Handling midday check-in from pending check-in")
                handle_midday_checkin(user_id, message_text, instance_id, services, context)
                services['task'].resolve_checkin(user_id, checkin_type, instance_id)
                logger.info("Midday check-in completed and resolved")
                
            elif checkin_type == services['task'].CHECK_IN_TYPES['END_DAY']:
                logger.info("Handling end-day check-in from pending check-in")
                handle_end_day_checkin(user_id, message_text, instance_id, services, context)
                services['task'].resolve_checkin(user_id, checkin_type, instance_id)
                logger.info("End-day check-in completed and resolved")
            
            # Clear current check-in source after handling
            logger.info("Clearing current check-in source")
            services['task'].update_user_state(
                user_id,
                current_state,
                instance_id,
                {'current_checkin_source': None}
            )
            
        else:
            logger.info("No active state or pending check-ins found")
            # No pending check-ins or active state, handle as general message
            response = (
                "I see you have no pending check-ins at the moment. "
                "You can always use commands like:\n"
                "• DONE [number] - Mark a task as completed\n"
                "• PROGRESS [number] - Update task progress\n"
                "• STUCK [number] - Get help with a task\n"
                "• TASKS - See your current tasks"
            )
            services['whatsapp'].send_message(user_id, response)
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        services['whatsapp'].stop_typing(user_id)
        raise

def handle_task_command(user_id: str, command_match: re.Match, instance_id: str, services: dict) -> str:
    """Handle task-related commands (DONE/PROGRESS/STUCK)."""
    command_type = command_match.group(1)
    task_num = int(command_match.group(2)) - 1  # Convert to 0-based index
    
    tasks = services['task'].get_daily_tasks(user_id, instance_id)
    if task_num < 0 or task_num >= len(tasks):
        return f"I don't see task #{task_num + 1} on your list. Type 'TASKS' to see your current tasks."
    
    task = tasks[task_num]
    status_map = {'DONE': 'completed', 'PROGRESS': 'in_progress', 'STUCK': 'stuck'}
    services['task'].update_task_status(user_id, task_num, status_map[command_type], instance_id)
    
    if command_type == 'DONE':
        return f"🎉 Great job completing '{task['task']}'! How do you feel about this accomplishment?"
    elif command_type == 'PROGRESS':
        return f"👍 Thanks for letting me know you're working on '{task['task']}'. How's it going?"
    else:  # STUCK
        return (
            f"I hear you're stuck with '{task['task']}'. That's completely okay.\n\n"
            f"Would you like to:\n"
            f"1. Break this into smaller steps?\n"
            f"2. Talk about what's challenging?\n"
            f"3. Get some alternative approaches?\n"
            f"4. Set it aside for now?"
        )

def handle_weekly_reflection(user_id: str, message_text: str, instance_id: str, services: dict, context: dict):
    """Handle weekly reflection flow."""
    try:
        logger.info(f"Starting weekly reflection handler for user {user_id}")
        logger.info(f"Message text: {message_text}")
        logger.info(f"Current context: {context}")
        
        # Get user
        user = User.get_or_create(user_id, instance_id)
        if not user:
            logger.error(f"Failed to get/create user {user_id}")
            services['whatsapp'].send_message(
                user_id,
                "I'm having trouble accessing your information. Could you try again in a moment?"
            )
            return
            
        # Get user's name
        name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
        logger.info(f"Processing for user: {name}")
            
        # Check if this is a response to planning selection
        # Handle both button responses and text responses
        if (isinstance(message_text, dict) and 
            message_text.get('type') == 'interactive' and 
            message_text.get('interactive', {}).get('type') == 'button_reply'):
            
            button_response = message_text['interactive']['button_reply']
            logger.info(f"Received button response: {button_response}")
            
            if button_response['id'] == 'weekly':
                handle_planning_selection('PLAN FOR THE WEEK', user_id, instance_id, services, context)
            elif button_response['id'] == 'daily':
                handle_planning_selection('DAY BY DAY PLANNING', user_id, instance_id, services, context)
            return
        elif message_text.upper() in ['PLAN FOR THE WEEK', 'DAY BY DAY PLANNING']:
            handle_planning_selection(message_text.upper(), user_id, instance_id, services, context)
            return
            
        # Analyze sentiment and determine planning type
        logger.info("Calling sentiment analysis service")
        analysis = services['sentiment'].analyze_weekly_checkin(message_text)
        logger.info(f"Weekly check-in analysis result: {analysis}")
        
        # Update context with analysis results
        context_updates = {
            'emotional_state': analysis.get('emotional_state'),
            'energy_level': analysis.get('energy_level'),
            'support_needed': analysis.get('support_needed'),
            'key_emotions': analysis.get('key_emotions', []),
            'recommended_approach': analysis.get('recommended_approach'),
            'last_weekly_checkin': int(time.time())
        }
        logger.info(f"Context updates: {context_updates}")
        
        # Generate response based on sentiment
        logger.info(f"Generating response for user {name}")
        
        emotional_state = analysis.get('emotional_state', 'neutral')
        energy_level = analysis.get('energy_level', 'medium')
        logger.info(f"Building response for emotional_state: {emotional_state}, energy_level: {energy_level}")
        
        if emotional_state == 'negative':
            response = (
                f"I hear you, {name}. 💙 It's completely okay to not be feeling your best. "
                "Let's take it day by day and focus on what feels manageable.\n\n"
                "I'll check in with you tomorrow morning to help plan your day. "
                "For now, is there anything specific you'd like to talk about?"
            )
            new_state = 'DAILY_CHECK_IN'
            context_updates['planning_type'] = 'daily'
            services['whatsapp'].send_message(user_id, response)
            
        else:  # positive or neutral
            response = (
                f"That's fantastic, {name}! 🌟 I love your positive energy. "
                "Let's make the most out of this week ahead!\n\n"
                "How would you like to plan?"
            )
            # Send interactive buttons for planning selection
            try:
                services['whatsapp'].send_interactive_buttons(
                    user_id,
                    response,
                    [
                        {"id": "weekly", "title": "Plan for the week"},
                        {"id": "daily", "title": "Day by day planning"}
                    ]
                )
                new_state = 'AWAITING_PLANNING_CHOICE'
                context_updates['planning_type'] = 'pending_selection'
            except Exception as e:
                logger.error(f"Failed to send interactive buttons: {e}")
                # Fallback to regular message with options
                fallback_response = (
                    f"{response}\n\n"
                    "1. Plan for the week\n"
                    "2. Day by day planning"
                )
                services['whatsapp'].send_message(user_id, fallback_response)
                new_state = 'AWAITING_PLANNING_CHOICE'
                context_updates['planning_type'] = 'pending_selection'
        
        # Update user state
        logger.info(f"Updating user state to: {new_state}")
        services['task'].update_user_state(
            user_id, new_state, instance_id, context_updates
        )
        logger.info("Weekly reflection handler completed successfully")
            
    except Exception as e:
        logger.error(f"Error handling weekly reflection for user {user_id}: {e}")
        services['whatsapp'].send_message(
            user_id,
            "I'm having trouble processing your response right now. Could you try sharing your thoughts again?"
        )

def handle_planning_selection(selection: str, user_id: str, instance_id: str, services: dict, context: dict):
    """Handle user's planning type selection."""
    try:
        user = User.get_or_create(user_id, instance_id)
        if not user:
            logger.error(f"Failed to get/create user {user_id}")
            return
            
        name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
        
        if selection == 'PLAN FOR THE WEEK':
            response = (
                "Let's plan your tasks for the upcoming week. Please reply with your tasks in this format:\n\n"
                "Monday: Task 1, Task 2, Task 3\n"
                "Tuesday: Task 1, Task 2, Task 3\n"
                "Wednesday: Task 1, Task 2, Task 3\n"
                "Thursday: Task 1, Task 2, Task 3\n"
                "Friday: Task 1, Task 2, Task 3"
            )
            new_state = 'WEEKLY_TASK_INPUT'
            planning_type = 'weekly'
        else:  # DAY BY DAY PLANNING
            response = (
                f"Great choice! I'll be here every morning to help you set your daily tasks. "
                "No pressure—just a little nudge to help you stay on track. "
                "Looking forward to planning with you each day! 😊"
            )
            new_state = 'DAILY_CHECK_IN'
            planning_type = 'daily'
            
        services['whatsapp'].send_message(user_id, response)
        
        # Update user state and planning type
        context_updates = {
            'planning_type': planning_type,
            'last_planning_selection': int(time.time())
        }
        
        services['task'].update_user_state(
            user_id, new_state, instance_id, context_updates
        )
        
    except Exception as e:
        logger.error(f"Error handling planning selection for user {user_id}: {e}")
        # Default to daily planning on error
        services['whatsapp'].send_message(
            user_id,
            "I had trouble processing your selection. Let's go with day by day planning to keep things simple."
        )
        services['task'].update_user_state(
            user_id, 'DAILY_CHECK_IN', instance_id, {'planning_type': 'daily'}
        )

def handle_weekly_task_input(user_id: str, message_text: str, instance_id: str, services: dict, context: dict):
    """Handle weekly task list input from user."""
    try:
        logger.info(f"Processing weekly task input for user {user_id}")
        logger.info(f"Task input: {message_text}")
        
        # Parse and validate the task input
        tasks_by_day, error_message = parse_task_input(message_text)
        
        if error_message:
            services['whatsapp'].send_message(
                user_id,
                f"{error_message}\n\n"
                "Please provide your tasks in this format:\n\n"
                "Monday: Task 1, Task 2, Task 3\n"
                "Tuesday: Task 1, Task 2, Task 3\n"
                "Wednesday: Task 1, Task 2, Task 3\n"
                "Thursday: Task 1, Task 2, Task 3\n"
                "Friday: Task 1, Task 2, Task 3"
            )
            return
            
        # Store tasks in Firebase
        try:
            services['task'].store_weekly_tasks(user_id, tasks_by_day, instance_id)
            
            # Count total tasks for encouragement message
            total_tasks = sum(len(tasks) for tasks in tasks_by_day.values())
            
            # Generate encouraging message based on task count
            if total_tasks > 15:
                encouragement = "That's an ambitious week ahead! Remember to pace yourself. 🌟"
            elif total_tasks > 10:
                encouragement = "Looks like a productive week ahead! You've got this! 💪"
            else:
                encouragement = "Nice and focused plan for the week! Quality over quantity! ✨"
            
            # Send confirmation message
            services['whatsapp'].send_message(
                user_id,
                f"Got it! Your weekly plan is all set. {encouragement}\n\n"
                "I'll check in with you each day to remind you of your tasks. "
            )
            
            # Update user state
            services['task'].update_user_state(
                user_id,
                'WEEKLY_PLANNING_COMPLETE',
                instance_id,
                {
                    'weekly_tasks': tasks_by_day,
                    'last_weekly_planning': int(time.time()),
                    'total_tasks': total_tasks
                }
            )
            
        except Exception as e:
            logger.error(f"Error storing weekly tasks: {e}")
            services['whatsapp'].send_message(
                user_id,
                "I had trouble saving your tasks. Could you try sending them again?"
            )
            
    except Exception as e:
        logger.error(f"Error processing weekly task input: {e}")
        services['whatsapp'].send_message(
            user_id,
            "I had trouble understanding your task list. Please make sure it follows the format:\n\n"
            "Monday: Task 1, Task 2, Task 3\n"
            "Tuesday: Task 1, Task 2, Task 3\n"
            "And so on..."
        )

def handle_daily_checkin(user_id: str, message_text: str, instance_id: str, services: dict, context: dict):
    """Handle daily check-in flow."""
    try:
        # Get user object
        user = User.get_or_create(user_id, instance_id)
        if not user:
            logger.error(f"Failed to get/create user {user_id}")
            services['whatsapp'].send_message(
                user_id,
                "I'm having trouble accessing your information. Could you try again in a moment?"
            )
            return
            
        # Analyze sentiment
        analysis = services['sentiment'].analyze_daily_checkin(message_text)
        logger.info(f"Daily check-in analysis for user {user_id}: {analysis}")
        
        # Update context
        context_updates = {
            'emotional_state': analysis.get('emotional_state'),
            'energy_level': analysis.get('energy_level'),
            'last_check_in': int(time.time())
        }
        
        # Generate appropriate response based on sentiment
        response = services['sentiment'].generate_daily_response(user, analysis)
        services['whatsapp'].send_message(user_id, response)
        
        # Update user state based on response content
        if "plan your tasks" in response.lower():
            new_state = User.STATE_DAILY_TASK_INPUT
        elif "self-care" in response.lower():
            new_state = User.STATE_SELF_CARE_DAY
        elif "break down" in response.lower():
            new_state = User.STATE_DAILY_TASK_BREAKDOWN
        else:
            new_state = User.STATE_DAILY_TASK_SELECTION
            
        # Update user state
        services['task'].update_user_state(
            user_id, new_state, instance_id, context_updates
        )
        
        logger.info(f"Updated user {user_id} state to {new_state}")
        
    except Exception as e:
        logger.error(f"Error handling daily check-in for user {user_id}: {str(e)}", exc_info=True)
        services['whatsapp'].send_message(
            user_id,
            "I'm having trouble processing your response right now. Could you try sharing your thoughts again?"
        )

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

def _process_daily_checkin(self, user, message_text):
    """Process daily check-in response."""
    try:
        # Analyze sentiment
        sentiment_data = sentiment_service.analyze_daily_checkin(message_text)
        logger.info(f"Sentiment analysis for user {user.user_id}: {sentiment_data}")
        
        # Generate response based on sentiment
        response = sentiment_service.generate_daily_response(user, sentiment_data)
        
        # Send response
        whatsapp_service = get_whatsapp_service(f'instance{user.account_index}')
        whatsapp_service.send_message(user.user_id, response)
        
        # Update user state based on response
        if "plan your tasks" in response.lower():
            user.update_user_state(User.STATE_DAILY_TASK_INPUT)
        elif "self-care" in response.lower():
            user.update_user_state(User.STATE_SELF_CARE_DAY)
        elif "break down" in response.lower():
            user.update_user_state(User.STATE_DAILY_TASK_BREAKDOWN)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing daily check-in: {str(e)}", exc_info=True)
        return False 