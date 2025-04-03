import logging
import time
import random
from typing import Dict, Any
from app.models.user import User

logger = logging.getLogger(__name__)

class SupportHandler:
    """Handler for emotional support and therapeutic conversations."""
    
    def __init__(self, whatsapp_service, task_service, sentiment_service):
        self.whatsapp = whatsapp_service
        self.task = task_service
        self.sentiment = sentiment_service
        
    def handle_support_choice(self, choice: str, user_id: str, instance_id: str, context: dict):
        """Handle user's choice for emotional support."""
        try:
            logger.info(f"Processing support choice '{choice}' for user {user_id}")
            
            # Get user info
            user = User.get_or_create(user_id, instance_id)
            if not user:
                logger.error(f"Failed to get/create user {user_id}")
                return
                
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            if choice == 'just_talk':
                response = (
                    "I'm here to listen. Sometimes just talking about what's on your mind can help. "
                    "Tell me more about what you're experiencing."
                )
                new_state = 'THERAPEUTIC_CONVERSATION'
                context_updates = {
                    'support_choice': choice,
                    'support_started_at': int(time.time()),
                    'conversation_turns': 0,
                    'last_response_time': int(time.time()),
                    'emotional_state': context.get('emotional_state', 'overwhelmed')
                }
            elif choice == 'self_care':
                # Get user's energy level from context
                energy_level = context.get('energy_level', 'low')
                
                # Generate self-care suggestions based on energy level
                if energy_level == 'low':
                    suggestions = [
                        "Take a gentle walk outside",
                        "Listen to calming music",
                        "Do some light stretching",
                        "Take a warm bath",
                        "Read a comforting book"
                    ]
                elif energy_level == 'medium':
                    suggestions = [
                        "Try a new hobby",
                        "Call a friend",
                        "Cook a favorite meal",
                        "Do some creative writing",
                        "Take photos of things you love"
                    ]
                else:  # high energy
                    suggestions = [
                        "Try a new workout",
                        "Start a creative project",
                        "Organize your space",
                        "Learn something new",
                        "Plan a fun activity"
                    ]
                
                # Select 3 random suggestions
                selected_suggestions = random.sample(suggestions, 3)
                
                response = (
                    "Taking care of yourself is so important. Here are some gentle suggestions "
                    "that might help you feel better:\n\n"
                    f"• {selected_suggestions[0]}\n"
                    f"• {selected_suggestions[1]}\n"
                    f"• {selected_suggestions[2]}\n\n"
                    "Remember, there's no pressure to do any of these. Just pick what feels right for you. "
                    "I'll check in with you tomorrow to see how you're doing. 💜"
                )
                new_state = 'SELF_CARE_DAY'
                context_updates = {
                    'support_choice': choice,
                    'support_started_at': int(time.time()),
                    'self_care_suggestions': selected_suggestions
                }
            else:  # small_task
                response = (
                    "That's a great approach. Let's pick one small, manageable task to focus on. "
                    "What feels most doable right now?"
                )
                new_state = 'SMALL_TASK_FOCUS'
                context_updates = {
                    'support_choice': choice,
                    'support_started_at': int(time.time())
                }
            
            self.whatsapp.send_message(user_id, response)
            self.task.update_user_state(
                user_id,
                new_state,
                instance_id,
                context_updates
            )
            logger.info(f"Updated user state to {new_state} for support choice: {choice}")
            
        except Exception as e:
            logger.error(f"Error handling support choice: {e}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I had trouble processing your choice. Let's start with something simple - "
                "how are you feeling right now?"
            )
            
    def handle_therapeutic_conversation(self, user_id: str, message_text: str, instance_id: str, context: dict):
        """Handle ongoing therapeutic conversation."""
        try:
            logger.info(f"Processing therapeutic conversation for user {user_id}")
            
            # Get user's name
            user = User.get_or_create(user_id, instance_id)
            name = user.name.split('_')[0] if user.name and '_' in user.name else (user.name or "Friend")
            
            # Analyze the message for emotional content
            analysis = self.sentiment.analyze_daily_checkin(message_text)
            emotional_state = analysis.get('emotional_state')
            key_emotions = analysis.get('key_emotions', [])
            
            # Update conversation context
            conversation_turns = context.get('conversation_turns', 0) + 1
            last_response_time = int(time.time())
            
            # Generate therapeutic response based on emotional state and conversation progress
            if emotional_state in ['overwhelmed', 'burnt_out', 'distressed']:
                if conversation_turns < 3:
                    # Early in conversation - focus on listening and validation
                    response = (
                        f"I hear you, {name}. It sounds like you're going through a lot right now. "
                        "Would you like to tell me more about what's making you feel this way?"
                    )
                elif conversation_turns < 6:
                    # Middle of conversation - start exploring coping strategies
                    response = (
                        "That's really challenging. When you feel this way, what usually helps you "
                        "feel a bit better? Even small things count."
                    )
                else:
                    # Later in conversation - focus on action steps
                    response = (
                        "Thank you for sharing all of this with me. It takes courage to talk about "
                        "how you're feeling. Would you like to explore some small steps that might help "
                        "you feel better?"
                    )
            else:
                # User's emotional state has improved
                response = (
                    f"I'm glad you're feeling a bit better, {name}. Would you like to talk about "
                    "what helped you feel this way, or would you like to explore some tasks for today?"
                )
            
            # Check if we should end the therapeutic conversation
            should_end = (
                emotional_state not in ['overwhelmed', 'burnt_out', 'distressed'] or
                conversation_turns >= 10 or
                'task' in message_text.lower() or
                'work' in message_text.lower() or
                'plan' in message_text.lower()
            )
            
            if should_end:
                response = (
                    f"{response}\n\n"
                    "Would you like to:\n"
                    "1. Continue talking\n"
                    "2. Take a self-care break\n"
                    "3. Look at some tasks for today"
                )
                new_state = 'AWAITING_SUPPORT_CHOICE'
            else:
                new_state = 'THERAPEUTIC_CONVERSATION'
            
            # Update context
            context_updates = {
                'conversation_turns': conversation_turns,
                'last_response_time': last_response_time,
                'emotional_state': emotional_state,
                'key_emotions': key_emotions
            }
            
            self.whatsapp.send_message(user_id, response)
            self.task.update_user_state(
                user_id,
                new_state,
                instance_id,
                context_updates
            )
            
            logger.info(f"Updated therapeutic conversation state. Turns: {conversation_turns}, "
                       f"Emotional state: {emotional_state}, Should end: {should_end}")
            
        except Exception as e:
            logger.error(f"Error in therapeutic conversation: {e}", exc_info=True)
            self.whatsapp.send_message(
                user_id,
                "I'm here to listen. Would you like to continue talking about how you're feeling?"
            ) 