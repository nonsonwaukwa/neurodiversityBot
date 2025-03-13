from flask import Blueprint, jsonify
from app.services.task_service import TaskService

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')
task_service = TaskService()

@bp.route('/', methods=['GET'])
def get_analytics():
    return jsonify({
        'status': 'success',
        'message': 'Analytics endpoint is working'
    })

@bp.route('/<user_id>', methods=['GET'])
def get_user_analytics(user_id):
    metrics = task_service.get_user_metrics(user_id)
    return jsonify({
        'status': 'success',
        'metrics': metrics
    }) 