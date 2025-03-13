from flask import Blueprint, request, jsonify
from app.services.whatsapp_service import WhatsAppService
from app.services.sentiment_service import SentimentService
from app.services.task_service import TaskService
import os
import re

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
        # Check if this is a WhatsApp message
        if data and 'entry' in data and data['entry']:
            entry = data['entry'][0]
            if 'changes' in entry and entry['changes']:
                change = entry['changes'][0]
                if 'value' in change and 'messages' in change['value']:
                    # Extract message details
                    value = change['value']
                    message = value['messages'][0]
                    user_id = message['from']
                    message_text = message['text']['body']
                    
                    # Determine which instance this message belongs to
                    recipient_id = value.get('metadata', {}).get('phone_number_id')
                    instance_id = get_instance_from_phone_number(recipient_id)
                    
                    # Get services for this instance
                    services = instances[instance_id]
                    
                    print(f"Processing message for instance {instance_id}")
                    
                    # Process the message based on user's state
                    response = process_message(user_id, message_text, instance_id, services)
                    
                    # Send response back to user
                    services['whatsapp'].send_message(user_id, response)
                    
                    # Log the conversation
                    services['task'].log_conversation(user_id, message_text, response, instance_id)
                    
                    return jsonify({'status': 'success'}), 200

        return jsonify({'status': 'no_message'}), 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
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
        return (
            "👋 Welcome to Odinma AI Accountability System!\n\n"
            "I'm your AI accountability partner. I'll help you:\n"
            "✅ Set and track daily tasks\n"
            "📊 Monitor your progress\n"
            "🎯 Stay motivated\n\n"
            "Let's start! What tasks would you like to accomplish today? "
            "(List up to 3 tasks)"
        )
    
    # If user is setting tasks
    elif user_state == 'TASK_SELECTION':
        # Analyze sentiment to adjust task load
        sentiment = services['sentiment'].analyze_sentiment(message_text)
        recommendation = services['sentiment'].get_task_recommendation(sentiment)
        
        # Parse tasks from message
        tasks = [task.strip() for task in message_text.split('\n') if task.strip()]
        
        # Save tasks
        services['task'].save_tasks(user_id, tasks, instance_id)
        
        return (
            f"Great! I've recorded your tasks. Based on your energy levels, "
            f"{recommendation['message']}\n\n"
            "I'll check in with you later to see how you're doing!"
        )
    
    # If user is checking in
    elif user_state == 'CHECK_IN':
        return handle_check_in(user_id, message_text, instance_id, services)
    
    # Default response
    return (
        "I'm not sure what you'd like to do. You can:\n"
        "1. Set new tasks for today\n"
        "2. Check in on your progress\n"
        "3. View your task history\n"
        "What would you like to do?"
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