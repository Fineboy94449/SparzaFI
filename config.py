"""
SparzaFi Platform Configuration
Core settings for Firebase Firestore database
"""

import os
import secrets
from datetime import timedelta

# ==================== APPLICATION CONFIGURATION ====================

class Config:
    """Base configuration"""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    PASSWORD_SALT = os.environ.get('PASSWORD_SALT', 'sparzafi_salt_2025')

    # Firebase Configuration (Required - replaces SQLite)
    FIREBASE_SERVICE_ACCOUNT = os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'firebase-service-account.json')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    
    # Session
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API Keys
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'your-google-maps-key')
    
    # Email Configuration (for future implementation)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@sparzafi.com')
    
    # Platform Settings
    PLATFORM_NAME = os.environ.get('PLATFORM_NAME', "SparzaFi")
    PLATFORM_TAGLINE = "Community Marketplace & Fintech Ecosystem"
    COMMISSION_RATE = float(os.environ.get('COMMISSION_RATE', 0.065))  # 6.5%
    DELIVERER_FEE_RATE = float(os.environ.get('DELIVERER_FEE_RATE', 0.10))  # 10%
    VAT_RATE = float(os.environ.get('VAT_RATE', 0.15))  # 15%

    # Delivery Route Pricing Limits
    MIN_BASE_FEE = float(os.environ.get('MIN_BASE_FEE', 5.0))
    MAX_BASE_FEE = float(os.environ.get('MAX_BASE_FEE', 100.0))
    DEFAULT_BASE_FEE = float(os.environ.get('DEFAULT_BASE_FEE', 15.0))
    MIN_PRICE_PER_KM = float(os.environ.get('MIN_PRICE_PER_KM', 3.0))
    MAX_PRICE_PER_KM = float(os.environ.get('MAX_PRICE_PER_KM', 50.0))
    DEFAULT_PRICE_PER_KM = float(os.environ.get('DEFAULT_PRICE_PER_KM', 8.0))
    DELIVERER_PLATFORM_FEE_RATE = float(os.environ.get('DELIVERER_PLATFORM_FEE_RATE', 0.15))  # 15% platform fee from deliverer earnings
    
    # Fintech Configuration
    TOKEN_NAME = os.environ.get('TOKEN_NAME', "Sparza Token")
    TOKEN_SYMBOL = os.environ.get('TOKEN_SYMBOL', "SPZ")
    INITIAL_TOKEN_BALANCE = float(os.environ.get('INITIAL_TOKEN_BALANCE', 1500.0))
    SPZ_TO_RAND_RATE = float(os.environ.get('SPZ_TO_RAND_RATE', 1.0))  # 1 SPZ = R1.00
    REFERRAL_BONUS_SPZ = float(os.environ.get('REFERRAL_BONUS_SPZ', 5.0))
    LOYALTY_POINTS_PER_RAND = float(os.environ.get('LOYALTY_POINTS_PER_RAND', 0.01))  # 1 point per R1 spent
    
    # File Upload
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'pdf'}
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')

    # Pagination
    PRODUCTS_PER_PAGE = int(os.environ.get('PRODUCTS_PER_PAGE', 20))
    TRANSACTIONS_PER_PAGE = int(os.environ.get('TRANSACTIONS_PER_PAGE', 50))
    MESSAGES_PER_PAGE = int(os.environ.get('MESSAGES_PER_PAGE', 20))

    # Delivery Status Descriptions
    DELIVERY_STATUSES = {
        'PENDING': 'Order placed - Awaiting confirmation',
        'CONFIRMED': 'Order confirmed - Preparing for delivery',
        'READY_FOR_PICKUP': 'Package ready for pickup',
        'PICKED_UP': 'Package picked up by deliverer',
        'IN_TRANSIT': 'Package in transit to destination',
        'DELIVERED': 'Package delivered to recipient',
        'COMPLETED': 'Order completed successfully',
        'CANCELLED': 'Order cancelled',
        'REFUNDED': 'Order refunded'
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# ==================== FIREBASE COLLECTIONS REFERENCE ====================
# SparzaFI uses Firebase Firestore with the following collections:
#
# Collections:
#   - users: User accounts and profiles
#   - sellers: Seller profiles and settings
#   - products: Product catalog
#   - orders: Order data with embedded items
#   - deliveries: Delivery tracking with real-time location
#   - notifications: User notifications
#   - messages: Chat messages
#   - conversations: Chat conversations
#   - reviews: Product and seller reviews
#   - transactions: Token transactions (SPZ)
#   - withdrawals: Withdrawal requests
#   - delivery_routes: Deliverer route pricing
#
# See firebase_service.py for service layer implementations
# See FIREBASE_INTEGRATION_GUIDE.md for detailed documentation

# Note: SQLite schema has been removed - using Firebase Firestore exclusively
# For legacy reference, see: git history or DATABASE_MIGRATION_ANALYSIS.md


# End of configuration file
# Firebase Firestore is used as the database - no SQL schema needed
# See firebase_service.py for database operations
