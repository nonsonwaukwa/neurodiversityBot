import os
from typing import Dict, Any
import requests
import random
import json
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

class SentimentService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = 'https://api.deepseek.com/v1/chat/completions'
        if not self.api_key:
            logger.error("DEEPSEEK_API_KEY not found in environment variables")
        
    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text and return emotional state."""
        try:
            # For now using basic analysis
            analysis = self._basic_word_analysis(text)
            
            # Parse the analysis into our expected format
            if isinstance(analysis, str):
                # Try to parse if it's a JSON string
                try:
                    analysis = json.loads(analysis)
                except:
                    pass
                    
            if isinstance(analysis, dict):
                # Map the sentiment analysis fields to our expected format
                return {
                    'emotional_state': analysis.get('sentiment', 'neutral'),
                    'energy_level': analysis.get('energy_level', 'medium'),
                    'support_needed': 'high' if analysis.get('stress_level') == 'high' else 'medium',
                    'key_emotions': analysis.get('emotions', ['neutral']),
                    'recommended_approach': 'supportive' if analysis.get('stress_level') == 'high' else 'flexible'
                }
            
            return self._get_default_sentiment()
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return self._get_default_sentiment()

    def _get_default_sentiment(self) -> Dict[str, Any]:
        """Return a default sentiment analysis with a balanced perspective."""
        default = {
            'emotional_state': 'neutral',
            'energy_level': 'medium',
            'support_needed': 'medium',
            'key_emotions': ['neutral'],
            'recommended_approach': 'flexible'
        }
        logger.info(f"Using default sentiment: {default}")
        return default

    def _basic_word_analysis(self, text: str) -> Dict[str, Any]:
        """Basic word-based sentiment analysis as fallback."""
        text = text.lower()
        
        # Simple word lists for basic analysis
        positive_words = {'great', 'good', 'happy', 'excited', 'wonderful', 'fantastic', 'amazing', 'love', 'excellent'}
        negative_words = {'bad', 'sad', 'tired', 'exhausted', 'overwhelmed', 'stressed', 'anxious', 'worried', 'frustrated'}
        high_energy_words = {'energetic', 'active', 'motivated', 'excited', 'ready', 'enthusiastic', 'pumped'}
        low_energy_words = {'tired', 'exhausted', 'drained', 'sleepy', 'fatigued', 'lazy', 'unmotivated'}
        
        # Count word occurrences
        pos_count = sum(1 for word in text.split() if word in positive_words)
        neg_count = sum(1 for word in text.split() if word in negative_words)
        high_energy_count = sum(1 for word in text.split() if word in high_energy_words)
        low_energy_count = sum(1 for word in text.split() if word in low_energy_words)
        
        # Determine emotional state
        if pos_count > neg_count:
            emotional_state = 'positive'
        elif neg_count > pos_count:
            emotional_state = 'negative'
        else:
            emotional_state = 'neutral'
            
        # Determine energy level
        if high_energy_count > low_energy_count:
            energy_level = 'high'
        elif low_energy_count > high_energy_count:
            energy_level = 'low'
        else:
            energy_level = 'medium'
            
        # Determine support needed based on negative indicators
        support_needed = 'high' if neg_count > 2 else ('medium' if neg_count > 0 else 'low')
        
        analysis = {
            'emotional_state': emotional_state,
            'energy_level': energy_level,
            'support_needed': support_needed,
            'key_emotions': [],  # Would need more sophisticated analysis for emotions
            'recommended_approach': 'flexible'
        }
        
        logger.info(f"Basic word analysis result: {analysis}")
        return analysis

    def get_task_recommendation(self, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Get task recommendations based on sentiment analysis, designed for neurodivergent individuals."""
        energy_level = sentiment.get('energy_level', 'medium')
        stress_level = sentiment.get('stress_level', 'medium')
        executive_function = sentiment.get('executive_function', 'managing')
        sensory_overwhelm = sentiment.get('sensory_overwhelm', False)
        
        # First handle special cases that should override other factors
        if sensory_overwhelm:
            return {
                'task_count': 1,
                'message': "I notice you might be experiencing some sensory overwhelm. Let's focus on just one gentle task today, and remember that rest is productive too.",
                'structure_level': 'high',
                'suggested_break_interval': 15  # minutes
            }
            
        if stress_level == 'high' and energy_level == 'low':
            return {
                'task_count': 1,
                'message': "It sounds like today might be challenging. Let's focus on just one small thing that could help you feel accomplished.",
                'structure_level': 'medium',
                'suggested_break_interval': 20  # minutes
            }
        
        # Handle executive function states
        if executive_function == 'struggling':
            task_messages = [
                "Breaking tasks into very small steps can help on days when focusing feels hard.",
                "When executive function is challenging, external structure can really help. Let's keep it simple today.",
                "Remember that done is better than perfect, especially on harder days."
            ]
            return {
                'task_count': 1 if energy_level == 'low' else 2,
                'message': random.choice(task_messages),
                'structure_level': 'high',
                'suggested_break_interval': 15  # minutes
            }
            
        # Now handle the standard energy level cases
        recommendations = {
            'high_energy': {
                'task_count': 4,
                'messages': [
                    "Your energy seems great today! This could be a good time to tackle something you've been putting off.",
                    "Looks like a high-energy day! Remember to channel that energy strategically rather than starting too many things at once.",
                    "Your energy feels strong today! Consider using the 'body doubling' technique (working alongside someone) to maintain momentum."
                ],
                'structure_level': 'low',
                'suggested_break_interval': 25  # minutes
            },
            'medium_energy': {
                'task_count': 3,
                'messages': [
                    "You seem to be in a balanced state today. That's a great place to be for steady progress.",
                    "Your energy feels steady. Remember to take short breaks between tasks to maintain that balance.",
                    "You're in a good zone for focused work. Consider using a timer to help maintain momentum without burnout."
                ],
                'structure_level': 'medium',
                'suggested_break_interval': 20  # minutes
            },
            'low_energy': {
                'task_count': 2,
                'messages': [
                    "Energy conservation is important on lower-energy days. Small wins matter a lot!",
                    "On days with less energy, doing even one small thing is meaningful progress.",
                    "Lower energy days are perfect for gentler tasks. Be kind to yourself today."
                ],
                'structure_level': 'high',
                'suggested_break_interval': 15  # minutes
            }
        }
        
        rec = recommendations.get(f"{energy_level}_energy", recommendations['medium_energy'])
        
        return {
            'task_count': rec['task_count'],
            'message': random.choice(rec['messages']),
            'structure_level': rec['structure_level'],
            'suggested_break_interval': rec['suggested_break_interval']
        }

    def analyze_weekly_checkin(self, text: str) -> Dict[str, Any]:
        """Analyze weekly check-in response and determine planning type."""
        logger.info(f"Analyzing weekly check-in text: {text}")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Analyze this weekly check-in response and determine the appropriate planning type:

Text: {text}

Please analyze for:
1. Overall emotional state (positive/negative/neutral)
2. Energy level (high/medium/low)
3. Planning preference (structured/flexible)
4. Key emotions expressed
5. Need for support level (high/medium/low)

Return the analysis in this exact JSON format:
{{
    "emotional_state": "positive/negative/neutral",
    "energy_level": "high/medium/low",
    "support_needed": "high/medium/low",
    "key_emotions": ["emotion1", "emotion2"],
    "recommended_approach": "structured/flexible/balanced"
}}"""

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are an expert in analyzing communication patterns and emotional states. You provide nuanced, non-judgmental analysis.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        }
        
        try:
            logger.info("Sending request to Deepseek API")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10  # Add timeout to prevent hanging
            )
            
            logger.info(f"Received response from Deepseek API: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Raw API response: {result}")
                # Parse the JSON response from the model
                try:
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Raw content: {content}")
                    # Extract JSON from the content (it might be wrapped in ```json ```)
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                    logger.info(f"Cleaned content: {content}")
                    analysis = json.loads(content)
                    logger.info(f"Parsed sentiment analysis: {analysis}")
                    return analysis
                except Exception as e:
                    logger.error(f"Failed to parse Deepseek response: {str(e)}")
                    return self._basic_word_analysis(text)
            else:
                logger.error(f"Deepseek API error ({response.status_code}): {response.text}")
                return self._basic_word_analysis(text)
        except Exception as e:
            logger.error(f"Exception in sentiment analysis: {str(e)}")
            return self._basic_word_analysis(text)

    def analyze_daily_checkin(self, text: str) -> Dict[str, Any]:
        """Analyze daily check-in response."""
        # Use the same analysis approach as weekly check-in
        return self.analyze_weekly_checkin(text)

    def generate_weekly_response(self, analysis: Dict[str, Any], user_name: str) -> Dict[str, str]:
        """Generate a response for the weekly check-in based on sentiment analysis."""
        emotional_state = analysis.get('emotional_state', 'okay')
        energy_level = analysis.get('energy_level', 'medium')
        needs_support = analysis.get('needs_support', False)
        emotions = analysis.get('emotions', [])
        
        # Handle exhaustion and overwhelm
        if 'exhausted' in emotions or energy_level == 'low' or emotional_state == 'overwhelmed':
            response = f"I hear you, {user_name}. Mental exhaustion is really tough, and it's completely valid to feel this way. Let's break things down into smaller, more manageable pieces. For this week, we'll focus on daily check-ins to provide more support and flexibility. How does that sound?"
            return {
                'message': response,
                'planning_type': 'daily'
            }
            
        # Handle moderate stress/fatigue
        elif 'tired' in emotions or energy_level == 'medium':
            response = f"Thanks for sharing how you're feeling, {user_name}. It sounds like you could use some extra support right now. Would you like to try daily check-ins this week? We can adjust the pace and tasks based on your energy levels each day."
            return {
                'message': response,
                'planning_type': 'daily'
            }
            
        # Handle okay/good state
        else:
            response = f"Thanks for checking in, {user_name}! It seems like you're in a good space to plan for the week ahead. Would you like to set up your weekly tasks now?"
            return {
                'message': response,
                'planning_type': 'weekly'
            }

    def generate_daily_response(self, user, sentiment_data):
        """Generate appropriate response based on daily check-in sentiment."""
        try:
            emotional_state = sentiment_data.get('emotional_state', 'neutral')
            energy_level = sentiment_data.get('energy_level', 'medium')
            key_emotions = sentiment_data.get('key_emotions', [])
            
            # Get user's name
            name = user.name.split('_')[0] if '_' in user.name else user.name
            
            # Handle overwhelmed/distressed state
            if emotional_state == 'overwhelmed' or any(emotion in key_emotions for emotion in ['distressed', 'burnout', 'exhausted']):
                message_parts = [
                    f"I hear you, {name}, and it's completely okay to feel this way. 💜\n\n",
                    "How would you like to proceed?",
                    "[Just talk] Talk about how you're feeling",
                    "[Self care] Take a self-care day",
                    "[Small task] Focus on one small, manageable task"
                ]
                response = "\n".join(message_parts)
                
                # Update user state for overwhelmed response
                user.context['daily_state'] = 'overwhelmed'
                return response
            
            # Handle positive or neutral state
            elif emotional_state in ['positive', 'neutral']:
                base_message = (
                    f"That's fantastic, {name}! 🌟" if energy_level == 'high' 
                    else f"Thanks for sharing, {name}. 💫"
                )
                
                message_parts = [
                    base_message,
                    "\nPlease share your 3 priorities for today in this format:",
                    "1. [Your first task]",
                    "2. [Your second task]",
                    "3. [Your third task]",
                    "\nOnce you've set your tasks, you can update them throughout the day using:",
                    "• DONE [number] - When you complete something",
                    "• PROGRESS [number] - When you start working on it",
                    "• STUCK [number] - If you need some support",
                    "\nI'll check in with you at midday to see how things are going! 🌟"
                ]
                
                response = "\n".join(message_parts)
                
                # Update user state for task planning
                user.context['daily_state'] = 'task_planning'
                return response
            
            # Update user's emotional state
            user.emotional_state = emotional_state
            user.energy_level = energy_level
            
            # Store sentiment data
            user.context['last_sentiment'] = sentiment_data
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating daily response: {str(e)}", exc_info=True)
            return (
                f"Thanks for sharing, {name}. How would you like to proceed?\n\n"
                "[Just talk] Let's talk about how you're feeling\n"
                "[Self care] Take some time for self-care\n"
                "[Tasks] Plan your day"
            ) 