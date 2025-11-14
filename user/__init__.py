"""
SparzaFi User Blueprint
Handles user profiles, wallet, settings, and referrals
"""

from flask import Blueprint

# Create the user blueprint
user_bp = Blueprint('user', __name__, template_folder='templates')

# Import routes after blueprint creation
from . import routes