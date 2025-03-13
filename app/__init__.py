from flask import Flask, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials
import os
import json
import base64
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize Firebase with flexible credential handling
    try:
        # Option 1: Standard file path (local development)
        cred_path = os.getenv('FIREBASE_CREDENTIALS')
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized with credential file")
        
        # Option 2: JSON content as environment variable (Railway)
        elif os.getenv('FIREBASE_CREDENTIALS_JSON'):
            cred_json = json.loads(os.getenv('FIREBASE_CREDENTIALS_JSON'))
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized with JSON credentials")
        
        # Option 3: Base64 encoded JSON (Railway alternative)
        elif os.getenv('FIREBASE_CREDENTIALS_BASE64'):
            cred_json = json.loads(base64.b64decode(os.getenv('FIREBASE_CREDENTIALS_BASE64')))
            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized with base64 encoded credentials")
        
        else:
            print("Warning: Firebase credentials not found.")
            print("Please set one of: FIREBASE_CREDENTIALS, FIREBASE_CREDENTIALS_JSON, or FIREBASE_CREDENTIALS_BASE64")
    
    except Exception as e:
        print(f"Warning: Failed to initialize Firebase: {e}")

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