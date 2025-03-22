from flask import Blueprint, request, jsonify
from app.services.whatsapp_service import WhatsAppService
from app.services.sentiment_service import SentimentService
from app.services.task_service import TaskService
import os
import re
import time
from datetime import datetime, timedelta
import random

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
    
    # Handle weekly reflection (Sunday check-in)
    if user_state == 'WEEKLY_REFLECTION':
        # Analyze sentiment to understand emotional state
        sentiment = services['sentiment'].analyze_sentiment(message_text)
        
        # Store sentiment data
        user = User(user_id, services['task'].get_user_name(user_id, instance_id))
        user.update_weekly_checkin(sentiment)
        
        # Determine planning schedule based on sentiment
        stress_level = sentiment.get('stress_level', 'medium')
        energy_level = sentiment.get('energy_level', 'medium')
        emotions = sentiment.get('emotions', [])
        
        # Check if the response contains enough reflection
        has_reflection = len(message_text.split()) > 10  # Basic check for a meaningful response
        
        if not has_reflection:
            return (
                "I want to make sure I understand how you're feeling about the week ahead. "
                "Could you share a bit more about your current state? "
                "You can send a voice note or text - whatever feels easier. 💭"
            )

        # Automatically determine planning approach based on sentiment
        is_overwhelmed = (
            stress_level == 'high' or 
            energy_level == 'low' or 
            any(emotion in ['overwhelmed', 'stressed', 'exhausted', 'anxious', 'burnt out'] for emotion in emotions)
        )

        if is_overwhelmed:
            # Switch to daily planning for overwhelmed users
            user.update_planning_schedule('daily')
            services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
            return (
                "I hear that things are feeling quite heavy right now. Let's take it one day at a time - "
                "that's often the most supportive approach when we're feeling overwhelmed. 💝\n\n"
                "I'll check in with you each morning to see how you're feeling, and we can focus on whatever "
                "feels manageable that day - even if it's just basic self-care.\n\n"
                "For now, how are you feeling about today? No pressure to do anything - just checking in. 💭"
            )
        else:
            # Set up weekly planning for users who are okay or neutral
            user.update_planning_schedule('weekly')
            services['task'].update_user_state(user_id, 'WEEKLY_TASK_SELECTION', instance_id)
            return (
                "Thanks for sharing! Based on what you've shared, it seems like you're in a good space "
                "to think about the week ahead. 🌱\n\n"
                "What are 2-3 main things you'd like to work towards this week? They can be as small as you need.\n\n"
                "Remember, these are flexible guidelines - we can always adjust them based on how you're feeling each day."
            )
    
    # Handle weekly check-in response (after reflection)
    elif user_state == 'WEEKLY_CHECK_IN':
        # Check for planning preference
        preference = message_text.strip().lower()
        
        if '1' in preference or 'day' in preference or 'daily' in preference:
            # User prefers daily planning
            user = User(user_id, services['task'].get_user_name(user_id, instance_id))
            user.update_planning_schedule('daily')
            services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
            return (
                "We'll take it day by day - sometimes that's the most compassionate approach. 💚\n\n"
                "I'll check in with you each morning to see how you're feeling and what feels manageable.\n\n"
                "For now, how are you feeling about today? No pressure to do anything - just checking in. 💭"
            )
        elif '2' in preference or 'week' in preference or 'goal' in preference:
            # User wants to set weekly goals
            user = User(user_id, services['task'].get_user_name(user_id, instance_id))
            user.update_planning_schedule('weekly')
            services['task'].update_user_state(user_id, 'WEEKLY_TASK_SELECTION', instance_id)
            return (
                "Let's set some gentle goals for the week! 🌱\n\n"
                "What are 2-3 things you'd like to work towards? They can be as small as you need.\n\n"
                "Remember, these are flexible guidelines, not strict rules. We can adjust them anytime based on how you're feeling."
            )
        elif '3' in preference or 'rest' in preference or 'care' in preference:
            # User needs rest and self-care
            user = User(user_id, services['task'].get_user_name(user_id, instance_id))
            user.update_planning_schedule('daily')
            services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
            return (
                "Taking time for rest and self-care is so important. 💝\n\n"
                "I'll check in gently each day, but there's no pressure to do anything you don't feel up to.\n\n"
                "For now, how are you feeling? And is there anything small I can support you with today? 💭"
            )
        else:
            return (
                "I want to make sure I understand your preference for this week. Could you let me know if you'd prefer:\n\n"
                "1. Daily check-ins (taking it day by day)\n"
                "2. Setting some weekly goals\n"
                "3. Focusing on rest and self-care\n\n"
                "Just reply with the number or type that feels right for you. 💭"
            )
    
    # Handle weekly task selection
    elif user_state == 'WEEKLY_TASK_SELECTION':
        # Parse tasks from message
        tasks = [task.strip() for task in message_text.split('\n') if task.strip()]
        
        if not tasks:
            return (
                "I don't see any specific tasks there. Would you like to share what you're hoping to focus on this week? "
                "Even small things count - like 'drink more water' or 'take short walks'. 💫"
            )
        
        # Store weekly tasks
        user = User(user_id, services['task'].get_user_name(user_id, instance_id))
        user.set_weekly_tasks(tasks[:3])  # Limit to 3 main tasks
        
        # Format task list
        task_list = '\n'.join([f"{i+1}. {task}" for i, task in enumerate(tasks[:3])])
        
        services['task'].update_user_state(user_id, 'CHECK_IN', instance_id)
        return (
            f"Perfect! Here are your focus areas for this week:\n\n{task_list}\n\n"
            "I'll check in with you each day to see how you're doing with these. "
            "Remember, it's okay if some days you can only do a little bit - progress isn't linear! "
            "We can always adjust these based on your energy and capacity.\n\n"
            "How are you feeling about getting started with these? 💭"
        )
    
    # If new user, create profile and send welcome message
    if user_state == 'SETUP':
        services['task'].create_user(user_id, instance_id, user_id)  # Using user_id as phone number for now
        services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
        return (
            "👋 Hi there! I'm your friendly accountability partner. I'm here to help you navigate your day, celebrate your wins (big or small), and work through any challenges.\n\n"
            "I'm designed to be flexible and supportive, especially on those days when things feel a bit much.\n\n"
            "So before we jump into tasks... how are you feeling today? Energetic, tired, somewhere in between? No right answers here! 💭"
        )
    
    # Initial check-in to gauge emotional state
    elif user_state == 'INITIAL_CHECK_IN':
        # Analyze sentiment to understand emotional state
        sentiment = services['sentiment'].analyze_sentiment(message_text)
        
        # Check if the response contains enough information about their feelings
        emotions = sentiment.get('emotions', [])
        energy_level = sentiment.get('energy_level', None)
        has_feeling_info = (
            len(emotions) > 0 or 
            energy_level is not None or 
            any(keyword in message_text.lower() for keyword in [
                'feel', 'feeling', 'felt', 'tired', 'energetic', 'exhausted', 'good', 'bad',
                'okay', 'ok', 'meh', 'great', 'terrible', 'stressed', 'calm', 'anxious',
                'happy', 'sad', 'overwhelmed', 'fine', 'alright'
            ])
        )
        
        if not has_feeling_info:
            return (
                "I want to make sure I understand how you're feeling before we move forward. Could you tell me a bit more about your energy level or mood? "
                "For example, are you feeling energetic, tired, stressed, calm? There's no right answer - I just want to support you better! 💭"
            )
        
        # Store sentiment data for later reference
        try:
            user_ref = services['task'].db.collection('instances').document(instance_id).collection('users').document(user_id)
            user_ref.update({
                'current_sentiment': sentiment,
                'last_check_in': datetime.now().isoformat()
            })
        except Exception:
            print(f"Failed to store sentiment data for user {user_id}")
        
        # Personalized response based on sentiment
        energy_level = sentiment.get('energy_level', 'medium')
        stress_level = sentiment.get('stress_level', 'medium')
        
        services['task'].update_user_state(user_id, 'TASK_SELECTION', instance_id)
        
        if stress_level == 'high':
            return (
                "I hear you're feeling pretty stressed today. That's totally okay and completely valid. ❤️\n\n"
                "On days like this, let's keep things simple. What's one small thing you'd like to accomplish? "
                "Even tiny steps forward count as progress - especially when things feel overwhelming."
            )
        elif energy_level == 'low':
            return (
                "Sounds like your energy is a bit low today. Those days happen to all of us, and that's perfectly fine. 💙\n\n"
                "Let's be gentle with ourselves today. What's one or two things that would feel manageable? "
                "Remember, rest is productive too, and small steps still move you forward."
            )
        elif energy_level == 'high':
            return (
                "Wow, you're sounding energetic today! That's awesome! 🌟\n\n"
                "Since you're feeling good, what would you like to accomplish? Feel free to list a few tasks, "
                "and maybe even throw in something that's been on your back burner. Seems like a great day to make progress!"
            )
        else:  # medium energy
            return (
                "Thanks for sharing how you're feeling! 😊\n\n"
                "What are a couple of things you'd like to focus on today? No pressure - just whatever feels right for you. "
                "We can always adjust as the day goes on."
            )
    
    # If user is setting tasks
    elif user_state == 'TASK_SELECTION':
        # Check if user wants to reset or needs help
        if message_text.strip().upper() in ['HELP', 'RESET', 'RESTART']:
            return (
                "No problem at all! Sometimes starting fresh is exactly what we need. 🌱\n\n"
                "Just share what you'd like to accomplish today - one task per line. For example:\n\n"
                "Read for 15 minutes\n"
                "Take a short walk\n"
                "Reply to that important email\n\n"
                "Or if you're having a tough day, even something like 'drink enough water' is perfect. What feels doable today?"
            )
        
        # Analyze sentiment to adjust task load
        sentiment = services['sentiment'].analyze_sentiment(message_text)
        recommendation = services['sentiment'].get_task_recommendation(sentiment)
        
        # Parse tasks from message
        tasks = [task.strip() for task in message_text.split('\n') if task.strip()]
        
        # Check if we have tasks
        if not tasks:
            return (
                "I don't see any specific tasks there - and that's totally okay! Some days are like that. 💫\n\n"
                "Would you like to:\n"
                "1. Try again with some simpler tasks (even 'rest' counts!)\n"
                "2. Skip tasks for today and just check in later\n"
                "3. Talk about what might be making it hard to set tasks today?"
            )
        
        # Limit number of tasks based on recommendation
        max_tasks = recommendation['task_count']
        if len(tasks) > max_tasks:
            tasks = tasks[:max_tasks]
            if max_tasks == 1:
                extra_message = "I noticed you might be going through a lot today, so I've kept it to just one task to focus on. We can always add more later if you're feeling up to it!"
            else:
                extra_message = f"Based on how you're feeling, I've kept your list to {max_tasks} tasks so it feels manageable. Quality over quantity, right? 😊"
        else:
            if len(tasks) == 1:
                extra_message = "One clear focus for today - I like it! Sometimes that's all we need."
            else:
                extra_message = "That looks like a manageable list - nice job setting realistic goals!"
        
        # Save tasks
        services['task'].save_tasks(user_id, tasks, instance_id)
        
        # Update user state
        services['task'].update_user_state(user_id, 'CHECK_IN', instance_id)
        
        # Format task list for display
        task_list = '\n'.join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
        
        return (
            f"Got it! Here's what we're focusing on today:\n\n{task_list}\n\n"
            f"{extra_message}\n\n"
            f"{recommendation['message']}\n\n"
            "I'll check in with you later, but feel free to update me anytime by:\n"
            "• Typing 'DONE 1' when you complete something\n"
            "• 'PROGRESS 2' if you're working on it\n"
            "• 'STUCK 3' if you're finding something challenging\n"
            "• or just 'CHAT' if you need someone to talk to"
        )
    
    # If user is checking in
    elif user_state == 'CHECK_IN':
        # Check for commands
        if message_text.strip().upper() == 'NEW TASKS':
            services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
            return (
                "Let's start fresh! But first, how are you feeling right now? Has your energy shifted since earlier? "
                "Checking in helps me better support you. 💭"
            )
        elif message_text.strip().upper() == 'SUMMARY':
            # Get user metrics
            metrics = services['task'].get_user_metrics(user_id, instance_id)
            
            completion_rate = metrics.get('completion_rate', 0)
            completed_tasks = metrics.get('completed_tasks', 0)
            
            encouragement = "That's awesome progress!" if completion_rate > 70 else "Every step counts, even the small ones."
            
            return (
                f"📊 Here's your progress snapshot:\n\n"
                f"Tasks completed: {completed_tasks}\n"
                f"Completion rate: {completion_rate:.1f}%\n\n"
                f"{encouragement}\n\n"
                f"Remember, progress isn't always linear - especially for neurodivergent brains! Some days flow easier than others, and that's completely normal. What matters is you're showing up. 💫"
            )
        elif message_text.strip().upper() == 'HELP':
            return (
                "I'm here for you! Here's how we can chat:\n\n"
                "• 'DONE 1' - Celebrate completing task #1\n"
                "• 'PROGRESS 2' - Update that you're working on task #2\n"
                "• 'STUCK 3' - Let me know you're finding task #3 challenging\n"
                "• 'NEW TASKS' - Start fresh with different tasks\n"
                "• 'SUMMARY' - See your progress overview\n"
                "• 'TASKS' - Review your current tasks\n"
                "• 'CHAT' - Just talk without focusing on tasks\n\n"
                "What would help you most right now?"
            )
        elif message_text.strip().upper() == 'TASKS':
            # Get current tasks
            tasks = services['task'].get_daily_tasks(user_id, instance_id)
            if not tasks:
                return "Looks like we haven't set up any tasks yet today. No pressure at all - what would feel good to focus on right now?"
            
            # Format task list with emojis based on status
            task_lines = []
            for i, task in enumerate(tasks):
                status = task['status']
                if status == 'completed':
                    emoji = "✅"
                elif status == 'in_progress':
                    emoji = "🔄"
                elif status == 'stuck':
                    emoji = "❌"
                else:
                    emoji = "⭐"
                task_lines.append(f"{i+1}. {emoji} {task['task']}")
            
            task_list = '\n'.join(task_lines)
            
            return (
                f"Here's where things stand with your tasks:\n\n{task_list}\n\n"
                f"How's it going? Any wins to celebrate or challenges you're facing?"
            )
        elif message_text.strip().upper() == 'CHAT':
            return (
                "I'm all ears! What's on your mind? Whether it's about your tasks, how your day is going, or just needing a moment to vent - I'm here for it. No pressure to be productive right now."
            )
        
        return handle_check_in(user_id, message_text, instance_id, services)
    
    # Default response for unknown state
    services['task'].update_user_state(user_id, 'INITIAL_CHECK_IN', instance_id)
    return (
        "Let's take a moment to reconnect! How are you feeling right now? Energetic, tired, overwhelmed, excited? "
        "No judgment here - just checking in so I can better support you."
    )

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