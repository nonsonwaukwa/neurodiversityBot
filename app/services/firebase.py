import os
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

# Get the absolute path to the project root
project_root = Path(__file__).parent.parent.parent

# Get Firebase credentials path from environment variable
cred_path = os.getenv('FIREBASE_CREDENTIALS')
if not cred_path:
    raise ValueError("FIREBASE_CREDENTIALS environment variable is not set")

# Convert relative path to absolute path if needed
if not os.path.isabs(cred_path):
    cred_path = os.path.join(project_root, cred_path)

if not os.path.exists(cred_path):
    raise ValueError(f"Firebase credentials file not found at: {cred_path}")

try:
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    
    # Get Firestore client
    db = firestore.client()
except Exception as e:
    raise ValueError(f"Failed to initialize Firebase: {str(e)}") 
