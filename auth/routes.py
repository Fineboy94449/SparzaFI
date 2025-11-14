from flask import Blueprint, render_template, redirect, url_for, session, request, abort, jsonify
from flask import current_app as app, g
import secrets
import jwt
import uuid
from datetime import datetime, timedelta

# Firebase imports
from firebase_db import get_user_service

# Shared utilities (will be migrated to Firebase)
from shared.utils import (
    login_required, hash_password, check_password,
    generate_referral_code, send_verification_email
)

auth_bp = Blueprint('auth', __name__, template_folder='templates')

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