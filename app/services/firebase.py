import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    # Get credentials from environment variable
    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if not cred_json:
        raise ValueError("FIREBASE_CREDENTIALS_JSON environment variable is not set")
    
    # Parse the JSON string into a dictionary
    try:
        cred_dict = json.loads(cred_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in FIREBASE_CREDENTIALS_JSON: {str(e)}")
    
    # Initialize Firebase with the credentials
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

# Get Firestore database instance
db = firestore.client() 
