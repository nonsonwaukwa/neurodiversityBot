from flask import Flask, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize Firebase
    cred_path = os.getenv('FIREBASE_CREDENTIALS')
    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Warning: Failed to initialize Firebase: {e}")
            print("Please make sure you have valid Firebase credentials in config/firebase-credentials.json")
    else:
        print("Warning: Firebase credentials not found.")
        print("Please add your Firebase service account key to config/firebase-credentials.json")
        print("and make sure FIREBASE_CREDENTIALS is set correctly in .env")

    # Register blueprints
    try:
        from app.routes import whatsapp, tasks, analytics
        app.register_blueprint(whatsapp.bp)
        app.register_blueprint(tasks.bp)
        app.register_blueprint(analytics.bp)
    except Exception as e:
        print(f"Warning: Failed to register blueprints: {e}")

    # Add root route
    @app.route('/')
    def index():
        return jsonify({
            'status': 'success',
            'message': 'Welcome to Odinma AI Accountability System',
            'endpoints': {
                'health': '/health',
                'webhook': '/webhook',
                'tasks': '/api/tasks',
                'analytics': '/api/analytics'
            }
        })

    # Add health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })

    return app 