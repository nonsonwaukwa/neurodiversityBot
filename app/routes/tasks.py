from flask import Blueprint, jsonify, request
from app.services.task_service import TaskService

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')
task_service = TaskService()

@bp.route('/', methods=['GET'])
def get_tasks():
    return jsonify({
        'status': 'success',
        'message': 'Tasks endpoint is working'
    })

@bp.route('/<user_id>', methods=['GET'])
def get_user_tasks(user_id):
    tasks = task_service.get_daily_tasks(user_id)
    return jsonify({
        'status': 'success',
        'tasks': tasks
    }) 