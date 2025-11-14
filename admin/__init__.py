"""
SparzaFi Admin Blueprint
Handles admin dashboard, user management, moderation, and analytics
"""

from flask import Blueprint

# Create the admin blueprint
admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Import routes after blueprint creation
from . import routes
