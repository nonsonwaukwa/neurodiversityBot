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
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        # Check Firebase connection
        try:
            from firebase_admin import db
            # Try to access a test reference
            ref = db.reference('health_check')
            ref.set({'last_check': datetime.now().isoformat()})
            health_status['services']['firebase'] = 'healthy'
        except Exception as e:
            health_status['services']['firebase'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check WhatsApp service configuration
        try:
            instance1_token = os.getenv('WHATSAPP_TOKEN_INSTANCE1') or os.getenv('WHATSAPP_ACCESS_TOKEN_1')
            instance2_token = os.getenv('WHATSAPP_TOKEN_INSTANCE2') or os.getenv('WHATSAPP_ACCESS_TOKEN_2')
            
            if not instance1_token or not instance2_token:
                raise ValueError("Missing WhatsApp tokens")
                
            health_status['services']['whatsapp'] = 'healthy'
        except Exception as e:
            health_status['services']['whatsapp'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Set response code based on overall status
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return jsonify(health_status), status_code

    return app 