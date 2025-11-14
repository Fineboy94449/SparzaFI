"""
SparzaFi Seller Blueprint
Handles seller dashboard, product management, and sales tracking
"""

from flask import Blueprint

# Create the seller blueprint
seller_bp = Blueprint('seller', __name__, template_folder='templates')

# Import routes after blueprint creation
from . import routes
