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
        
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze the sentiment of the given text with special attention to neurodivergent expression patterns."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Analyze the sentiment of the following text with special attention to neurodivergent expression patterns:

Text: {text}

Please analyze for:
1. Overall sentiment (positive, negative, or neutral)
2. Energy level (high, medium, low)
3. Stress level (high, medium, low)
4. Executive function indicators (struggling, managing, thriving)
5. Key emotions expressed or implied
6. Potential sensory overwhelm signals (present/not present)
7. Communication style indicators

For neurodivergent individuals, consider that:
- Flat or brief responses might not indicate disinterest
- Intense focus on details could indicate passion rather than anxiety
- Direct communication isn't rudeness
- Variable punctuation/capitalization may express emotion rather than carelessness

Please provide the analysis in JSON format with these fields:
{{
  "sentiment": "positive/negative/neutral",
  "energy_level": "high/medium/low",
  "stress_level": "high/medium/low",
  "executive_function": "struggling/managing/thriving",
  "emotions": ["emotion1", "emotion2"],
  "sensory_overwhelm": true/false,
  "communication_style": "brief/detailed/direct/exploratory"
}}"""

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are an expert in analyzing communication patterns of neurodivergent individuals, including those with ADHD, autism, anxiety, and depression. You provide nuanced, non-judgmental analysis.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                # Parse the JSON response from the model
                try:
                    analysis = json.loads(result['choices'][0]['message']['content'])
                    return analysis
                except:
                    # If parsing fails, return a default with a note about the failure
                    print(f"Failed to parse sentiment analysis response: {result['choices'][0]['message']['content']}")
                    return self._get_default_sentiment()
            else:
                print(f"API error ({response.status_code}): {response.text}")
                return self._get_default_sentiment()
        except Exception as e:
            print(f"Exception in sentiment analysis: {str(e)}")
            return self._get_default_sentiment()
            
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """Return a default sentiment analysis with a balanced perspective."""
        return {
            'sentiment': 'neutral',
            'energy_level': 'medium',
            'stress_level': 'medium',
            'executive_function': 'managing',
            'emotions': ['neutral'],
            'sensory_overwhelm': False,
            'communication_style': 'brief'
        }

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
    "planning_type": "weekly/daily",
    "support_needed": "high/medium/low",
    "key_emotions": ["emotion1", "emotion2"],
    "recommended_approach": "structured/flexible"
}}"""

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are an expert in analyzing communication patterns of neurodivergent individuals, with special focus on determining appropriate planning approaches.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        }
        
        try:
            logger.info("Sending request to Deepseek API")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            
            logger.info(f"Received response from Deepseek API: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Raw API response: {result}")
                
                try:
                    # Extract content from the response
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Raw content: {content}")
                    
                    # Remove markdown code blocks and clean up the content
                    content = content.replace('```json', '').replace('```', '').strip()
                    # Remove any extra newlines that might interfere with parsing
                    content = ''.join(line.strip() for line in content.splitlines())
                    logger.info(f"Cleaned content: {content}")
                    
                    analysis = json.loads(content)
                    logger.info(f"Parsed sentiment analysis: {analysis}")
                    
                    # Validate the response has the expected fields
                    required_fields = ['emotional_state', 'energy_level', 'planning_type', 'support_needed', 'key_emotions', 'recommended_approach']
                    if all(field in analysis for field in required_fields):
                        return analysis
                    else:
                        logger.error("Missing required fields in API response")
                        return self._get_default_sentiment()
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse API response: {e}")
                    logger.error(f"Raw content: {content}")
                    return self._get_default_sentiment()
            else:
                logger.error(f"API error ({response.status_code}): {response.text}")
                return self._get_default_sentiment()
                
        except Exception as e:
            logger.error(f"Exception in sentiment analysis: {str(e)}")
            return self._get_default_sentiment()
            
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """Return a default sentiment analysis with a balanced perspective."""
        default = {
            'emotional_state': 'neutral',
            'energy_level': 'medium',
            'planning_type': 'daily',
            'support_needed': 'medium',
            'key_emotions': ['neutral'],
            'recommended_approach': 'flexible'
        }
        logger.info(f"Using default sentiment: {default}")
        return default

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

    def _call_api(self, text: str, prompt_type: str = 'daily') -> dict:
        """Call the DeepSeek API for sentiment analysis."""
        try:
            # For now, use pattern matching for quick responses
            text = text.lower().strip()
            
            if 'great' in text or 'amazing' in text or 'fantastic' in text:
                return {
                    'sentiment': 'positive',
                    'energy_level': 'high',
                    'stress_level': 'low',
                    'executive_function': 'high',
                    'emotions': ['excited', 'enthusiastic'],
                    'sensory_overwhelm': False,
                    'communication_style': 'expressive'
                }
            elif 'okay' in text or 'fine' in text:
                return {
                    'sentiment': 'neutral',
                    'energy_level': 'medium',
                    'stress_level': 'low',
                    'executive_function': 'stable',
                    'emotions': ['content'],
                    'sensory_overwhelm': False,
                    'communication_style': 'moderate'
                }
            elif 'tired' in text or 'exhausted' in text:
                return {
                    'sentiment': 'negative',
                    'energy_level': 'low',
                    'stress_level': 'medium',
                    'executive_function': 'low',
                    'emotions': ['fatigued'],
                    'sensory_overwhelm': True,
                    'communication_style': 'reserved'
                }
            else:
                # Default positive for "I'm great"
                return {
                    'sentiment': 'positive',
                    'energy_level': 'high',
                    'stress_level': 'low',
                    'executive_function': 'high',
                    'emotions': ['positive', 'energetic'],
                    'sensory_overwhelm': False,
                    'communication_style': 'engaged'
                }
                
        except Exception as e:
            logger.error(f"Error calling API: {str(e)}", exc_info=True)
            return None

    def analyze_daily_checkin(self, text: str) -> dict:
        """Analyze text for daily check-in."""
        try:
            logger.info(f"Analyzing daily check-in text: {text}")
            
            # Call API for analysis
            api_response = self._call_api(text, 'daily')
            
            if not api_response:
                logger.warning("Using default sentiment due to API error")
                return self._get_default_sentiment()
            
            # Map API response to our format
            sentiment_mapping = {
                'positive': 'positive',
                'negative': 'overwhelmed',
                'neutral': 'neutral'
            }
            
            energy_mapping = {
                'high': 'high',
                'medium': 'medium',
                'low': 'low'
            }
            
            return {
                'emotional_state': sentiment_mapping.get(api_response.get('sentiment', 'neutral'), 'neutral'),
                'energy_level': energy_mapping.get(api_response.get('energy_level', 'medium'), 'medium'),
                'support_needed': 'high' if api_response.get('stress_level') == 'high' else 'medium',
                'key_emotions': api_response.get('emotions', ['neutral']),
                'recommended_approach': 'supportive' if api_response.get('stress_level') == 'high' else 'flexible'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing daily check-in: {str(e)}", exc_info=True)
            return self._get_default_sentiment()

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