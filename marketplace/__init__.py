"""
SparzaFi Marketplace Blueprint
Handles main feed, product browsing, cart, and checkout
"""

from flask import Blueprint

# Create the marketplace blueprint
marketplace_bp = Blueprint('marketplace', __name__, template_folder='templates')

# Import routes after blueprint creation
from . import routes