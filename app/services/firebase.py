import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path

# Initialize Firebase Admin SDK
cred_path = os.path.join(Path(__file__).parent.parent.parent, 'config', 'neurodiversitybot-firebase-adminsdk-fbsvc-e442ab6d6a.json')
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# Get Firestore database instance
db = firestore.client() 