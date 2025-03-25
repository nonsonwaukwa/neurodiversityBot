"""Validation utilities for task input and other data."""
import re
from typing import Dict, List, Tuple, Optional

def validate_task_input(tasks_by_day: dict) -> Tuple[bool, Optional[str]]:
    """Validate the task input format and content.
    
    Args:
        tasks_by_day (dict): Dictionary mapping days to lists of tasks
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        If input is valid, returns (True, None)
        If input is invalid, returns (False, error_message)
    """
    if not isinstance(tasks_by_day, dict):
        return False, "Invalid task format. Please use the template provided."
        
    # Valid days check
    valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'}
    for day in tasks_by_day:
        if day not in valid_days:
            return False, f"Invalid day '{day}'. Please use Monday through Friday."
    
    # Check if all weekdays are present
    missing_days = valid_days - set(tasks_by_day.keys())
    if missing_days:
        return False, f"Missing tasks for: {', '.join(sorted(missing_days))}"
    
    for day, tasks in tasks_by_day.items():
        # Type check
        if not isinstance(tasks, list):
            return False, f"Tasks for {day} should be a list."
            
        # Number of tasks check
        if len(tasks) > 10:
            return False, f"Too many tasks for {day}. Please limit to 10 tasks per day."
            
        # Task content validation
        for task in tasks:
            if not isinstance(task, str):
                return False, f"Invalid task in {day}. Tasks must be text."
                
            if len(task.strip()) == 0:
                return False, f"Empty task found in {day}. Please remove empty tasks."
                
            if len(task) > 200:
                return False, f"Task too long in {day}: '{task[:50]}...'. Please keep tasks under 200 characters."
                
            # Check for potentially harmful content
            if re.search(r'[<>{}]', task):
                return False, f"Invalid characters found in task for {day}. Please use only letters, numbers, and basic punctuation."
    
    return True, None

def parse_task_input(message_text: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
    """Parse the task input message and validate its format.
    
    Args:
        message_text (str): The raw message text from the user
        
    Returns:
        Tuple[Dict[str, List[str]], Optional[str]]: (tasks_by_day, error_message)
        If parsing succeeds, returns (tasks_dict, None)
        If parsing fails, returns (empty_dict, error_message)
    """
    tasks_by_day = {}
    
    try:
        # Split into lines and process each line
        lines = [line.strip() for line in message_text.split('\n') if line.strip()]
        
        for line in lines:
            # Match day and tasks
            day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday):\s*(.+)$', line, re.IGNORECASE)
            if not day_match:
                continue
                
            day = day_match.group(1).capitalize()
            tasks_text = day_match.group(2)
            
            # Split tasks by comma and clean them
            tasks = [task.strip() for task in tasks_text.split(',')]
            tasks = [task for task in tasks if task]  # Remove empty tasks
            
            tasks_by_day[day] = tasks
        
        # Validate the parsed tasks
        is_valid, error_message = validate_task_input(tasks_by_day)
        if not is_valid:
            return {}, error_message
            
        return tasks_by_day, None
        
    except Exception as e:
        return {}, "I had trouble understanding your task list. Please make sure it follows the format shown above." 