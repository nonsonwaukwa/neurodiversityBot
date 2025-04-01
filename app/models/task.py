from datetime import datetime
import time
from typing import Dict, Any, List, Optional
from firebase_admin import firestore

class Task:
    """Model representing a task in the system."""
    
    # Task Status Constants
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_STUCK = 'stuck'
    
    def __init__(
        self,
        description: str,
        status: str = STATUS_PENDING,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        created_at: Optional[int] = None,
        due_date: Optional[str] = None
    ):
        """Initialize a task."""
        self.description = description
        self.status = status
        self.task_id = task_id
        self.user_id = user_id
        self.instance_id = instance_id
        self.created_at = created_at or int(time.time())
        self.due_date = due_date
        self.last_updated = int(time.time())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task instance from a dictionary."""
        return cls(
            description=data.get('task', '') or data.get('description', ''),
            status=data.get('status', cls.STATUS_PENDING),
            task_id=data.get('task_id'),
            user_id=data.get('user_id'),
            instance_id=data.get('instance_id'),
            created_at=data.get('created_at'),
            due_date=data.get('due_date')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for storage."""
        return {
            'task': self.description,  # Keep 'task' for backward compatibility
            'description': self.description,
            'status': self.status,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'instance_id': self.instance_id,
            'created_at': self.created_at,
            'due_date': self.due_date,
            'last_updated': self.last_updated
        }
    
    @staticmethod
    def get_tasks_for_date(user_id: str, date: datetime) -> List['Task']:
        """Get tasks for a specific date."""
        try:
            db = firestore.client()
            date_str = date.strftime('%Y-%m-%d')
            
            # Query unified collection first
            tasks_ref = db.collection('users').document(user_id).collection('daily_tasks')
            query = tasks_ref.where('date', '==', date_str).where('status', '==', 'active')
            
            tasks = []
            docs = query.get()
            for doc in docs:
                task_data = doc.to_dict()
                for task in task_data.get('tasks', []):
                    task['task_id'] = doc.id
                    tasks.append(Task.from_dict(task))
            
            return tasks
            
        except Exception as e:
            print(f"Error getting tasks for date: {e}")
            return []
    
    @staticmethod
    def get_tasks_for_day(user_id: str, instance_id: str, day: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific day from weekly plan."""
        try:
            db = firestore.client()
            
            # Try instance-specific collection first
            instance_user_ref = db.collection('instances').document(instance_id).collection('users').document(user_id)
            user_doc = instance_user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                weekly_tasks = user_data.get('weekly_tasks', {})
                return weekly_tasks.get(day, [])
            
            return []
            
        except Exception as e:
            print(f"Error getting tasks for day: {e}")
            return []
    
    @staticmethod
    def create_task(user_id: str, instance_id: str, description: str, due_date: Optional[str] = None) -> Optional['Task']:
        """Create a new task."""
        try:
            db = firestore.client()
            
            task = Task(
                description=description,
                user_id=user_id,
                instance_id=instance_id,
                due_date=due_date
            )
            
            # Add to daily tasks collection
            tasks_ref = db.collection('users').document(user_id).collection('daily_tasks')
            doc_ref = tasks_ref.document()
            doc_ref.set({
                'tasks': [task.to_dict()],
                'date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'active',
                'created_at': int(time.time())
            })
            
            task.task_id = doc_ref.id
            return task
            
        except Exception as e:
            print(f"Error creating task: {e}")
            return None
    
    def update_status(self, new_status: str) -> bool:
        """Update task status."""
        try:
            if new_status not in [self.STATUS_PENDING, self.STATUS_IN_PROGRESS, 
                                self.STATUS_COMPLETED, self.STATUS_STUCK]:
                raise ValueError(f"Invalid status: {new_status}")
            
            db = firestore.client()
            self.status = new_status
            self.last_updated = int(time.time())
            
            # Update in daily tasks collection if task_id exists
            if self.task_id:
                tasks_ref = db.collection('users').document(self.user_id).collection('daily_tasks').document(self.task_id)
                doc = tasks_ref.get()
                if doc.exists:
                    tasks_data = doc.to_dict()
                    tasks = tasks_data.get('tasks', [])
                    for task in tasks:
                        if task.get('description') == self.description:
                            task['status'] = new_status
                            task['last_updated'] = self.last_updated
                    tasks_ref.update({'tasks': tasks})
            
            return True
            
        except Exception as e:
            print(f"Error updating task status: {e}")
            return False
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == self.STATUS_COMPLETED
    
    @property
    def is_in_progress(self) -> bool:
        """Check if task is in progress."""
        return self.status == self.STATUS_IN_PROGRESS
    
    @property
    def is_stuck(self) -> bool:
        """Check if task is stuck."""
        return self.status == self.STATUS_STUCK
    
    def __str__(self) -> str:
        """String representation of the task."""
        return f"Task({self.description}, status={self.status})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the task."""
        return f"Task(id={self.task_id}, description={self.description}, status={self.status})" 