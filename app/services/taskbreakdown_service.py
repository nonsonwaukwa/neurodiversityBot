import os
import logging
import requests
import json
from typing import Optional

logger = logging.getLogger(__name__)

class TaskBreakdownService:
    """Service for handling task breakdowns using DeepSeek API."""
    
    def __init__(self):
        """Initialize the DeepSeek service."""
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = 'https://api.deepseek.com/v1/chat/completions'
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not found in environment variables")
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response using DeepSeek API.
        
        Args:
            prompt: The task description to break down
            
        Returns:
            The generated response as a string
        """
        try:
            if not self.api_key:
                logger.error("No DeepSeek API key available")
                return self._get_default_breakdown()

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Create the full prompt with the task description
            full_prompt = f"""Please break down the following task into 3-5 smaller, actionable steps.
Each step should be specific, measurable, and achievable.
Task: {prompt}

Format the response as a numbered list of steps."""

            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': 'You are an expert in breaking down tasks into manageable steps, with special attention to neurodivergent-friendly approaches. Provide clear, actionable steps that are specific and achievable.'},
                    {'role': 'user', 'content': full_prompt}
                ],
                'temperature': 0.3
            }
            
            try:
                logger.info(f"Making DeepSeek API request to {self.base_url}")
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )
                logger.info(f"DeepSeek API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Successfully received DeepSeek API response")
                    try:
                        # Extract the content from the API response
                        content = result['choices'][0]['message']['content']
                        logger.info(f"Raw API response content: {content}")
                        return content
                        
                    except Exception as e:
                        logger.error(f"Failed to parse DeepSeek response: {content}")
                        logger.error(f"Parse error: {str(e)}")
                        raise  # Re-raise to trigger API retry
                else:
                    logger.error(f"DeepSeek API error ({response.status_code}): {response.text}")
                    raise Exception(f"API returned status code {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"DeepSeek API request failed: {str(e)}")
                raise  # Re-raise to trigger API retry
                
        except Exception as e:
            logger.error(f"All DeepSeek API attempts failed, falling back to default breakdown: {str(e)}")
            return self._get_default_breakdown()
    
    def _get_default_breakdown(self) -> str:
        """Return a default task breakdown when API is unavailable."""
        return """
        1. Identify the main components of the task
        2. Break down each component into smaller steps
        3. Prioritize the steps in order of importance
        4. Set specific timeframes for each step
        5. Create a checklist for tracking progress
        """ 