import os
from typing import Dict, Any
import requests

class SentimentService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = 'https://api.deepseek.com/v1/chat/completions'
        
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze the sentiment of the given text."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Analyze the sentiment of the following text and provide:
1. Overall sentiment (positive, negative, or neutral)
2. Energy level (high, medium, low)
3. Stress level (high, medium, low)
4. Key emotions detected

Text: {text}

Please provide the analysis in JSON format."""

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': 'You are a sentiment analysis expert.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            # Parse the JSON response from the model
            try:
                import json
                analysis = json.loads(result['choices'][0]['message']['content'])
                return analysis
            except:
                return {
                    'sentiment': 'neutral',
                    'energy_level': 'medium',
                    'stress_level': 'medium',
                    'emotions': []
                }
        else:
            return {
                'sentiment': 'neutral',
                'energy_level': 'medium',
                'stress_level': 'medium',
                'emotions': []
            }

    def get_task_recommendation(self, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Get task recommendations based on sentiment analysis."""
        energy_level = sentiment.get('energy_level', 'medium')
        stress_level = sentiment.get('stress_level', 'medium')
        
        recommendations = {
            'high_energy': {
                'task_count': 4,
                'message': "You're feeling energetic! Would you like to add an extra task to your list?"
            },
            'medium_energy': {
                'task_count': 3,
                'message': "You're in a good state! Let's stick with three tasks for today."
            },
            'low_energy': {
                'task_count': 1,
                'message': "I notice you might be feeling low on energy. Let's focus on one important task today."
            }
        }
        
        if stress_level == 'high':
            return {
                'task_count': 1,
                'message': "I sense you're feeling stressed. Let's focus on self-care and one manageable task today."
            }
        
        return recommendations.get(energy_level, recommendations['medium_energy']) 