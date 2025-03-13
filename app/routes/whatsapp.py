from flask import Blueprint, request, jsonify
from app.services.whatsapp_service import WhatsAppService
from app.services.sentiment_service import SentimentService
from app.services.task_service import TaskService
import os
import re
import time
from datetime import datetime, timedelta

bp = Blueprint('whatsapp', __name__, url_prefix='/webhook')

# Initialize services for each instance
instances = {}
for instance_id in ['instance1', 'instance2']:  # Add more instances as needed
    instances[instance_id] = {
        'whatsapp': WhatsAppService(instance_id),
        'sentiment': SentimentService(),
        'task': TaskService()
    }

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
    """Handle incoming messages from all WhatsApp instances"""
    data = request.get_json()
    print(f"Received webhook data:", data)

    try:
        # Clean the message cache periodically
        if len(message_cache) > 100:  # If cache gets too large
            clean_message_cache()
            
        # Check if this is a WhatsApp message
        if data and 'entry' in data and data['entry']:
            entry = data['entry'][0]
            if 'changes' in entry and entry['changes']:
                change = entry['changes'][0]
                if 'value' in change and 'messages' in change['value']:
                    # Extract message details
                    value = change['value']
                    message = value['messages'][0]
                    message_id = message['id']
                    user_id = message['from']
                    
                    # Check message type
                    if 'text' in message and 'body' in message['text']:
                        message_text = message['text']['body']
                    elif 'image' in message:
                        # Handle image message
                        message_text = "[IMAGE] Image received. I can only process text messages at the moment."
                    elif 'audio' in message:
                        # Handle audio message
                        message_text = "[AUDIO] Audio received. I can only process text messages at the moment."
                    elif 'video' in message:
                        # Handle video message
                        message_text = "[VIDEO] Video received. I can only process text messages at the moment."
                    elif 'document' in message:
                        # Handle document message
                        message_text = "[DOCUMENT] Document received. I can only process text messages at the moment."
                    elif 'location' in message:
                        # Handle location message
                        message_text = "[LOCATION] Location received. I can only process text messages at the moment."
                    else:
                        # Unknown message type
                        message_text = "I received your message but couldn't understand the format. Please send text messages only."
                    
                    # Check for duplicate message
                    if message_id in message_cache:
                        print(f"Duplicate message {message_id} detected. Skipping processing.")
                        return jsonify({'status': 'duplicate_message_ignored'}), 200
                    
                    # Add message to cache
                    message_cache[message_id] = {
                        'timestamp': time.time(),
                        'processed': False
                    }
                    
                    # Determine which instance this message belongs to
                    recipient_id = value.get('metadata', {}).get('phone_number_id')
                    instance_id = get_instance_from_phone_number(recipient_id)
                    
                    # Check if instance exists
                    if instance_id not in instances:
                        print(f"Error: Instance {instance_id} not found. Using instance1 as fallback.")
                        instance_id = 'instance1'
                    
                    # Get services for this instance
                    services = instances[instance_id]
                    
                    print(f"Processing message {message_id} for instance {instance_id}")
                    
                    # Process the message based on user's state
                    response = process_message(user_id, message_text, instance_id, services)
                    
                    # Send response back to user
                    services['whatsapp'].send_message(user_id, response)
                    
                    # Log the conversation
                    services['task'].log_conversation(user_id, message_text, response, instance_id)
                    
                    # Mark message as processed
                    message_cache[message_id]['processed'] = True
                    
                    return jsonify({'status': 'success'}), 200
                else:
                    print("Webhook received but no messages found in the payload")
            else:
                print("Webhook received but no changes found in the entry")
        else:
            print("Webhook received but no entry found in the data")

        return jsonify({'status': 'no_message'}), 200

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# For backward compatibility, redirect instance-specific routes to the main webhook
@bp.route('/<instance_id>', methods=['GET'])
def verify_instance_webhook(instance_id: str):
    """Redirect to main webhook verification"""
    return verify_webhook()

@bp.route('/<instance_id>', methods=['POST'])
def instance_webhook(instance_id: str):
    """Redirect to main webhook handler"""
    return webhook()

def process_message(user_id: str, message_text: str, instance_id: str, services: dict) -> str:
    """Process incoming message and return appropriate response"""
    
    # Get user's current state
    user_state = services['task'].get_user_state(user_id, instance_id)
    
    # If new user, create profile and send welcome message
    if user_state == 'SETUP':
        services['task'].create_user(user_id, instance_id, user_id)  # Using user_id as phone number for now
        services['task'].update_user_state(user_id, 'TASK_SELECTION', instance_id)
        return (
            "👋 Welcome to Odinma AI Accountability System!\n\n"
            "I'm your AI accountability partner. I'll help you:\n"
            "✅ Set and track daily tasks\n"
            "📊 Monitor your progress\n"
            "🎯 Stay motivated\n\n"
            "Let's start! What tasks would you like to accomplish today? "
            "(List up to 3 tasks, one per line)"
        )
    
    # If user is setting tasks
    elif user_state == 'TASK_SELECTION':
        # Check if user wants to reset or needs help
        if message_text.strip().upper() in ['HELP', 'RESET', 'RESTART']:
            return (
                "To set your tasks, simply list them one per line. For example:\n\n"
                "Complete project proposal\n"
                "Exercise for 30 minutes\n"
                "Read 20 pages of book\n\n"
                "What tasks would you like to accomplish today?"
            )
        
        # Analyze sentiment to adjust task load
        sentiment = services['sentiment'].analyze_sentiment(message_text)
        recommendation = services['sentiment'].get_task_recommendation(sentiment)
        
        # Parse tasks from message
        tasks = [task.strip() for task in message_text.split('\n') if task.strip()]
        
        # Check if we have tasks
        if not tasks:
            return (
                "I didn't detect any tasks in your message. Please list your tasks, one per line. For example:\n\n"
                "Complete project proposal\n"
                "Exercise for 30 minutes\n"
                "Read 20 pages of book"
            )
        
        # Limit number of tasks based on recommendation
        max_tasks = recommendation['task_count']
        if len(tasks) > max_tasks:
            tasks = tasks[:max_tasks]
            extra_message = f"I've limited your tasks to {max_tasks} based on your energy levels today."
        else:
            extra_message = ""
        
        # Save tasks
        services['task'].save_tasks(user_id, tasks, instance_id)
        
        # Update user state
        services['task'].update_user_state(user_id, 'CHECK_IN', instance_id)
        
        # Format task list for display
        task_list = '\n'.join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
        
        return (
            f"Great! I've recorded your tasks:\n\n{task_list}\n\n"
            f"{extra_message}\n\n"
            f"{recommendation['message']}\n\n"
            "I'll check in with you later to see how you're doing! "
            "You can update me anytime by typing:\n"
            "✅ DONE [task number] - to mark a task as complete\n"
            "🔄 PROGRESS [task number] - to mark as in progress\n"
            "❌ STUCK [task number] - if you need help"
        )
    
    # If user is checking in
    elif user_state == 'CHECK_IN':
        # Check for commands
        if message_text.strip().upper() == 'NEW TASKS':
            services['task'].update_user_state(user_id, 'TASK_SELECTION', instance_id)
            return (
                "Let's set new tasks for today! What would you like to accomplish? "
                "Please list your tasks, one per line."
            )
        elif message_text.strip().upper() == 'SUMMARY':
            # Get user metrics
            metrics = services['task'].get_user_metrics(user_id, instance_id)
            return (
                f"📊 Your Progress Summary:\n\n"
                f"Tasks Completed: {metrics.get('completed_tasks', 0)}/{metrics.get('total_tasks', 0)}\n"
                f"Completion Rate: {metrics.get('completion_rate', 0):.1f}%\n\n"
                f"Keep up the great work! 💪"
            )
        elif message_text.strip().upper() == 'HELP':
            return (
                "Here's how to use the Odinma AI Accountability System:\n\n"
                "✅ DONE [task number] - Mark a task as complete\n"
                "🔄 PROGRESS [task number] - Mark a task as in progress\n"
                "❌ STUCK [task number] - Indicate you need help with a task\n"
                "NEW TASKS - Start a new set of tasks\n"
                "SUMMARY - View your progress summary\n"
                "TASKS - View your current tasks\n\n"
                "How can I assist you today?"
            )
        elif message_text.strip().upper() == 'TASKS':
            # Get current tasks
            tasks = services['task'].get_daily_tasks(user_id, instance_id)
            if not tasks:
                return "You don't have any tasks set for today. Type NEW TASKS to set some!"
            
            # Format task list
            task_list = '\n'.join([f"{i+1}. {task['task']} - {task['status'].upper()}" for i, task in enumerate(tasks)])
            
            return (
                f"📝 Here are your current tasks:\n\n{task_list}\n\n"
                f"Update me on your progress using:\n"
                f"✅ DONE [task number]\n"
                f"🔄 PROGRESS [task number]\n"
                f"❌ STUCK [task number]"
            )
        
        return handle_check_in(user_id, message_text, instance_id, services)
    
    # Default response for unknown state
    services['task'].update_user_state(user_id, 'TASK_SELECTION', instance_id)
    return (
        "I'm not sure what you'd like to do. Let's start fresh!\n\n"
        "What tasks would you like to accomplish today? Please list them one per line."
    )

def handle_check_in(user_id: str, message_text: str, instance_id: str, services: dict) -> str:
    """Handle user's check-in response"""
    # Check for task status updates
    status_match = re.match(r'(DONE|PROGRESS|STUCK)\s+(\d+)', message_text.upper())
    if status_match:
        status_type = status_match.group(1)
        task_num = int(status_match.group(2)) - 1  # Convert to 0-based index
        
        status_map = {
            'DONE': 'completed',
            'PROGRESS': 'in_progress',
            'STUCK': 'stuck'
        }
        
        services['task'].update_task_status(user_id, task_num, status_map[status_type], instance_id)
        
        if status_type == 'DONE':
            return "🎉 Great job completing that task! Keep up the momentum!"
        elif status_type == 'PROGRESS':
            return "👍 Thanks for the update! Keep pushing forward!"
        else:  # STUCK
            return (
                "I understand you're feeling stuck. That's completely normal. "
                "Would you like to:\n"
                "1. Break down the task into smaller steps?\n"
                "2. Get some motivation?\n"
                "3. Skip this task for now?"
            )
    
    # Get current tasks and their status
    tasks = services['task'].get_daily_tasks(user_id, instance_id)
    return services['whatsapp'].send_task_reminder(user_id, tasks) 