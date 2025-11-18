from flask import Blueprint, render_template, redirect, url_for, session, request, abort, jsonify
from flask import current_app as app, g
import secrets
import jwt
import uuid
from datetime import datetime, timedelta
import os

# Firebase imports
from firebase_db import get_user_service

# Google OAuth imports
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

# Shared utilities (will be migrated to Firebase)
from shared.utils import (
    login_required, hash_password, check_password,
    generate_referral_code, send_verification_email
)

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/signup', methods=['GET', 'POST'])
def login():
    # ... (Login logic) ...
    if session.get('user'):
        # Redirect logic uses blueprint endpoints based on user type
        user = session.get('user')
        if user.get('user_type') == 'admin':
            return redirect(url_for('admin.admin_dashboard_enhanced'))
        elif user.get('user_type') == 'seller':
            return redirect(url_for('seller.seller_dashboard'))
        elif user.get('user_type') == 'deliverer':
            return redirect(url_for('deliverer.dashboard'))
        else:
            return redirect(url_for('marketplace.feed'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        referral_code = request.form.get('referral_code') # 13. Referral Rewards

        if not email or not password:
            return render_template('auth.html', error="Email and password are required")

        # Get Firebase user service
        user_service = get_user_service()
        user = user_service.get_by_email(email)

        if user:
            # Handle login for existing user
            if check_password(user['password_hash'], password):
                if not user.get('email_verified', False): # 22. Email Verification check
                    return render_template('auth.html', error="Account exists but email is not verified. Check your inbox.")

                session['user'] = user
                session.permanent = True
                # Redirect based on user type
                if user.get('user_type') == 'admin':
                    return redirect(url_for('admin.admin_dashboard_enhanced'))
                elif user.get('user_type') == 'seller':
                    return redirect(url_for('seller.seller_dashboard'))
                elif user.get('user_type') == 'deliverer':
                    return redirect(url_for('deliverer.dashboard'))
                else:
                    return redirect(url_for('marketplace.feed'))

            return render_template('auth.html', error="Invalid email or password")

        # --- New User Registration ---
        try:
            hashed_password = hash_password(password)
            user_referral_code = generate_referral_code(email)
            referred_by_id = None

            # Get Firebase user service
            user_service = get_user_service()

            # Check if referral code is valid
            if referral_code:
                from firebase_config import get_firestore_db
                from google.cloud.firestore_v1.base_query import FieldFilter

                db = get_firestore_db()
                referrer_query = db.collection('users').where(
                    filter=FieldFilter('referral_code', '==', referral_code)
                ).limit(1).stream()

                for ref_doc in referrer_query:
                    referred_by_id = ref_doc.id
                    break

            # Generate verification token
            verification_token = secrets.token_urlsafe(32)

            # Create new user in Firebase
            new_user_id = str(uuid.uuid4())
            user_data = {
                'email': email,
                'password_hash': hashed_password,
                'user_type': 'buyer',
                'referral_code': user_referral_code,
                'referred_by': referred_by_id,
                'spz_balance': app.config['INITIAL_TOKEN_BALANCE'],
                'email_verified': False,
                'phone_verified': False,
                'verification_token': verification_token,
                'full_name': '',
                'phone': '',
                'status': 'active',
                'kyc_status': 'pending'
            }

            user_service.create(user_data, doc_id=new_user_id)

            # Create referral record if applicable
            if referred_by_id:
                from firebase_config import get_firestore_db
                db = get_firestore_db()
                db.collection('referrals').add({
                    'referrer_id': referred_by_id,
                    'referred_id': new_user_id,
                    'created_at': datetime.utcnow().isoformat()
                })

            # Send verification email
            send_verification_email(email, verification_token)

            return render_template('auth.html', success="Account created. Check your email for verification link.")

        except Exception as e:
            # Check if it's a duplicate email error
            if "already exists" in str(e).lower():
                return render_template('auth.html', error="A user with that email already exists.")
            return render_template('auth.html', error=f"An error occurred during signup: {e}")

    return render_template('auth.html')

@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    """Verify user email with token"""
    try:
        from firebase_config import get_firestore_db
        from google.cloud.firestore_v1.base_query import FieldFilter

        db = get_firestore_db()

        # Find user with matching verification token
        users_query = db.collection('users').where(
            filter=FieldFilter('verification_token', '==', token)
        ).limit(1).stream()

        user_doc = None
        for doc in users_query:
            user_doc = doc
            break

        if user_doc:
            # Update user to mark email as verified
            user_doc.reference.update({
                'email_verified': True,
                'verification_token': None  # Clear the token
            })

            return render_template('auth.html', success="Email verified successfully! You can now login.")
        else:
            return render_template('auth.html', error="Invalid or expired verification token.")

    except Exception as e:
        return render_template('auth.html', error=f"Verification failed: {e}")

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('marketplace.feed'))

# --- Google OAuth Login ---
@auth_bp.route('/auth/google')
def google_login():
    """Initiate Google OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return render_template('auth.html',
            error="Google login is not configured. Please contact the administrator.")

    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for('auth.google_callback', _external=True)]
            }
        },
        scopes=['openid', 'email', 'profile']
    )

    flow.redirect_uri = url_for('auth.google_callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # Store state in session for CSRF protection
    session['oauth_state'] = state

    return redirect(authorization_url)

@auth_bp.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Verify state for CSRF protection
        if request.args.get('state') != session.get('oauth_state'):
            return render_template('auth.html',
                error="Invalid OAuth state. Please try again.")

        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [url_for('auth.google_callback', _external=True)]
                }
            },
            scopes=['openid', 'email', 'profile']
        )

        flow.redirect_uri = url_for('auth.google_callback', _external=True)

        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.url)

        # Get user info from ID token
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Extract user information
        google_id = id_info.get('sub')
        email = id_info.get('email')
        name = id_info.get('name', '')
        picture = id_info.get('picture', '')
        email_verified = id_info.get('email_verified', False)

        if not email:
            return render_template('auth.html',
                error="Could not retrieve email from Google. Please try again.")

        # Get or create user
        user_service = get_user_service()
        user = user_service.get_by_email(email)

        if user:
            # Existing user - log them in
            # Update Google info if not already set
            if not user.get('google_id'):
                user_service.update(user['id'], {
                    'google_id': google_id,
                    'profile_picture': picture,
                    'email_verified': True  # Google already verified
                })
                user['google_id'] = google_id
                user['profile_picture'] = picture

            session['user'] = user
            session.permanent = True

            # Redirect based on user type
            if user.get('user_type') == 'admin':
                return redirect(url_for('admin.admin_dashboard_enhanced'))
            elif user.get('user_type') == 'seller':
                return redirect(url_for('seller.seller_dashboard'))
            elif user.get('user_type') == 'deliverer':
                return redirect(url_for('deliverer.dashboard'))
            else:
                return redirect(url_for('marketplace.feed'))

        else:
            # New user - create account
            user_referral_code = generate_referral_code(email)

            new_user_id = str(uuid.uuid4())
            user_data = {
                'email': email,
                'google_id': google_id,
                'full_name': name,
                'profile_picture': picture,
                'password_hash': '',  # No password for Google auth users
                'user_type': 'buyer',  # Default to buyer
                'referral_code': user_referral_code,
                'referred_by': None,
                'spz_balance': app.config.get('INITIAL_TOKEN_BALANCE', 100),
                'email_verified': True,  # Google already verified email
                'phone_verified': False,
                'verification_token': None,
                'phone': '',
                'status': 'active',
                'kyc_status': 'pending',
                'token_balance': 0.0,
                'is_admin': False
            }

            user_service.create(user_data, doc_id=new_user_id)

            # Add id to user_data for session
            user_data['id'] = new_user_id

            # Log in the new user
            session['user'] = user_data
            session.permanent = True

            return redirect(url_for('marketplace.feed'))

    except Exception as e:
        app.logger.error(f"Google OAuth error: {e}")
        return render_template('auth.html',
            error=f"Google login failed: {str(e)}")

# --- JWT API (21) ---
@auth_bp.route('/api/jwt/token', methods=['POST'])
def get_jwt_token():
    """Generates a JWT for a valid user (for mobile/API access)"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Get Firebase user service
    user_service = get_user_service()
    user = user_service.get_by_email(email)

    if user and check_password(user['password_hash'], password):
        # Get JWT secret key from config (add it if not present)
        jwt_secret = app.config.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])

        payload = {
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return jsonify({'token': token, 'user_id': user['id']}), 200

    return jsonify({'msg': 'Bad username or password'}), 401