"""
Firebase Configuration for SparzaFI
Handles Firebase Admin SDK initialization and connection management
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
import json

class FirebaseConfig:
    """Firebase configuration and initialization"""

    _initialized = False
    _db = None
    _storage_bucket = None

    @classmethod
    def initialize(cls, service_account_path=None):
        """
        Initialize Firebase Admin SDK

        Args:
            service_account_path: Path to Firebase service account JSON file
                                 Defaults to FIREBASE_SERVICE_ACCOUNT env var
        """
        if cls._initialized:
            return

        # Get service account path
        if service_account_path is None:
            service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT')

        if not service_account_path:
            raise ValueError(
                "Firebase service account path not provided. "
                "Set FIREBASE_SERVICE_ACCOUNT environment variable or pass service_account_path"
            )

        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Service account file not found: {service_account_path}")

        try:
            # Initialize Firebase Admin
            cred = credentials.Certificate(service_account_path)

            # Get storage bucket from service account or environment
            with open(service_account_path, 'r') as f:
                service_account_data = json.load(f)
                project_id = service_account_data.get('project_id')

            storage_bucket = os.environ.get('FIREBASE_STORAGE_BUCKET', f"{project_id}.appspot.com")

            firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket
            })

            cls._initialized = True
            print(f"✓ Firebase initialized successfully (Project: {project_id})")

        except Exception as e:
            print(f"✗ Firebase initialization failed: {e}")
            raise

    @classmethod
    def get_db(cls):
        """Get Firestore database instance"""
        if not cls._initialized:
            cls.initialize()

        if cls._db is None:
            cls._db = firestore.client()

        return cls._db

    @classmethod
    def get_storage(cls):
        """Get Firebase Storage bucket"""
        if not cls._initialized:
            cls.initialize()

        if cls._storage_bucket is None:
            cls._storage_bucket = storage.bucket()

        return cls._storage_bucket

    @classmethod
    def is_initialized(cls):
        """Check if Firebase is initialized"""
        return cls._initialized


# Convenience functions
def get_firestore_db():
    """Get Firestore database client"""
    return FirebaseConfig.get_db()


def get_storage_bucket():
    """Get Firebase Storage bucket"""
    return FirebaseConfig.get_storage()


def initialize_firebase(service_account_path=None):
    """Initialize Firebase (convenience function)"""
    FirebaseConfig.initialize(service_account_path)
