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

    def analyze_daily_checkin(self, text: str) -> dict:
        """
        Analyze sentiment for daily check-in responses.
        
        Args:
            text: The user's response text
            
        Returns:
            dict: Analysis results including emotional_state and energy_level
        """
        try:
            logger.info(f"Analyzing daily check-in text: {text}")
            
            prompt = (
                "Analyze the following daily check-in response and determine:\n"
                "1. The user's emotional state (positive, neutral, or overwhelmed)\n"
                "2. Their energy level (high, medium, or low)\n"
                "3. Key emotions expressed\n"
                "4. Whether they need extra support\n\n"
                f"Response: {text}\n\n"
                "Respond in JSON format with these fields:\n"
                "{\n"
                '  "emotional_state": "positive/neutral/overwhelmed",\n'
                '  "energy_level": "high/medium/low",\n'
                '  "emotions": ["emotion1", "emotion2"],\n'
                '  "needs_support": true/false\n'
                "}"
            )
            
            response = self._call_api(prompt)
            
            # Clean the response to handle markdown code blocks
            cleaned_response = self._clean_api_response(response)
            
            # Parse the JSON response
            result = json.loads(cleaned_response)
            
            logger.info(f"Sentiment analysis result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing daily check-in: {str(e)}")
            # Default to neutral if analysis fails
            return {
                "emotional_state": "neutral",
                "energy_level": "medium",
                "emotions": ["unknown"],
                "needs_support": False
            }
            
    def _clean_api_response(self, response: str) -> str:
        """Clean the API response by removing markdown code blocks and extra whitespace."""
        # Remove markdown code blocks
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        return response 

    def generate_daily_response(self, user, sentiment_data):
        """Generate appropriate response based on daily check-in sentiment."""
        try:
            emotional_state = sentiment_data.get('emotional_state', 'neutral')
            energy_level = sentiment_data.get('energy_level', 'medium')
            support_needed = sentiment_data.get('support_needed', 'medium')
            key_emotions = sentiment_data.get('key_emotions', [])
            
            # Get user's name
            name = user.name.split('_')[0] if '_' in user.name else user.name
            
            # Base message parts
            message_parts = []
            
            # Add emotional acknowledgment
            if emotional_state == 'positive':
                message_parts.append(
                    f"I'm glad you're feeling positive, {name}! 🌟\n\n"
                    "That's great energy to start the day with. "
                    "Would you like to share what's contributing to your positive mood?"
                )
            elif emotional_state == 'neutral':
                message_parts.append(
                    f"Thanks for sharing, {name}. A neutral state can be a good foundation.\n\n"
                    "Would you like to talk about what you're looking forward to today?"
                )
            else:  # overwhelmed
                message_parts.append(
                    f"I hear you, {name}. It's okay to feel overwhelmed.\n\n"
                    "Would you like to:\n"
                    "1. Focus on one small task\n"
                    "2. Take a self-care day\n"
                    "3. Break down what's feeling overwhelming"
                )
            
            # Add energy level acknowledgment
            if energy_level == 'low':
                message_parts.append(
                    "\nI notice your energy might be low. Remember, it's okay to take things at your own pace. "
                    "Would you like to start with something small?"
                )
            elif energy_level == 'high':
                message_parts.append(
                    "\nYou seem to have good energy! Would you like to plan out your tasks for today?"
                )
            
            # Add support options
            if support_needed == 'high':
                message_parts.append(
                    "\nI'm here to support you. Would you like to:\n"
                    "1. Talk about what's on your mind\n"
                    "2. Get help breaking down tasks\n"
                    "3. Take a moment for self-care"
                )
            
            # Add task planning based on emotional state
            if emotional_state in ['positive', 'neutral']:
                message_parts.append(
                    "\nWould you like to plan your tasks for today? "
                    "You can list them or we can break them down together."
                )
            
            # Combine all parts
            response = "\n".join(message_parts)
            
            # Update user's emotional state
            user.emotional_state = emotional_state
            user.energy_level = energy_level
            
            # Store sentiment data
            user.context['last_sentiment'] = sentiment_data
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating daily response: {str(e)}", exc_info=True)
            return (
                f"Thanks for sharing, {name}. How would you like to proceed with your day?\n\n"
                "1. Plan your tasks\n"
                "2. Take a moment for self-care\n"
                "3. Break down what's on your mind"
            ) 