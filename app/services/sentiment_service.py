import os
from typing import Dict, Any
import requests
import random
import json

class SentimentService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = 'https://api.deepseek.com/v1/chat/completions'
        
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
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Analyze this weekly check-in response and determine the appropriate planning type:

Text: {text}

Please analyze for:
1. Overall emotional state (overwhelmed/burnt out vs. okay/neutral/good)
2. Energy level (high, medium, low)
3. Stress level (high, medium, low)
4. Key emotions
5. Need for immediate support

For neurodivergent individuals, consider that:
- Brief responses might indicate overwhelm rather than disinterest
- "Okay" might mean actually okay or might be masking difficulty
- Direct communication about struggles is valuable
- Variable punctuation/capitalization may express emotion

Please provide the analysis in JSON format with these fields:
{{
  "emotional_state": "overwhelmed/okay",
  "energy_level": "high/medium/low",
  "stress_level": "high/medium/low",
  "emotions": ["emotion1", "emotion2"],
  "needs_support": true/false,
  "planning_type": "daily/weekly",
  "confidence_score": 0.0-1.0
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
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                try:
                    analysis = json.loads(result['choices'][0]['message']['content'])
                    return analysis
                except:
                    print(f"Failed to parse weekly check-in analysis: {result['choices'][0]['message']['content']}")
                    return self._get_default_weekly_analysis()
            else:
                print(f"API error ({response.status_code}): {response.text}")
                return self._get_default_weekly_analysis()
        except Exception as e:
            print(f"Exception in weekly check-in analysis: {str(e)}")
            return self._get_default_weekly_analysis()

    def _get_default_weekly_analysis(self) -> Dict[str, Any]:
        """Return a default weekly check-in analysis."""
        return {
            'emotional_state': 'okay',
            'energy_level': 'medium',
            'stress_level': 'medium',
            'emotions': ['neutral'],
            'needs_support': False,
            'planning_type': 'weekly',
            'confidence_score': 0.5
        }

    def generate_weekly_response(self, analysis: Dict[str, Any], user_name: str) -> Dict[str, Any]:
        """Generate appropriate response based on weekly check-in analysis."""
        emotional_state = analysis.get('emotional_state', 'okay')
        confidence = analysis.get('confidence_score', 0.5)
        
        if confidence < 0.7:
            # Low confidence - use fallback response
            return {
                'message': (
                    f"Thanks for sharing, {user_name}. I want to make sure I understand how you're feeling. "
                    "Could you tell me a bit more about your current state? You can send a voice note or text - "
                    "whatever feels easier. 💭"
                ),
                'planning_type': None  # Need more information
            }
        
        if emotional_state == 'overwhelmed':
            return {
                'message': (
                    f"I hear you're feeling overwhelmed right now, {user_name}. That's completely valid. "
                    "Would you like to:\n"
                    "1. Talk about what's feeling overwhelming? I'm here to listen and help break things down\n"
                    "2. Take some time alone to rest and recharge? I'll check in tomorrow morning\n\n"
                    "Remember, Sunday is a rest day, and it's okay to take time for yourself. 💙"
                ),
                'planning_type': 'daily'
            }
        else:
            return {
                'message': (
                    f"Thanks for sharing, {user_name}! Let's plan out your week. "
                    "What are 2-3 things you'd like to work towards each day (Monday to Friday)?\n\n"
                    "For example:\n"
                    "Monday: Read for 15 minutes, Take a walk\n"
                    "Tuesday: Organize workspace, Reply to emails\n"
                    "Wednesday: Exercise, Meal prep\n"
                    "Thursday: Journal, Study\n"
                    "Friday: Clean room, Call friend\n\n"
                    "Just list your tasks for each day, and we'll organize them together. 🌟"
                ),
                'planning_type': 'weekly'
            } 