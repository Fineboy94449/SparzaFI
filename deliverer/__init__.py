"""
SparzaFi Deliverer Blueprint
Handles deliverer dashboard, delivery management, tracking, and earnings
"""

from flask import Blueprint

# Create the deliverer blueprint
deliverer_bp = Blueprint('deliverer', __name__, template_folder='templates')

# Import routes after blueprint creation
from . import routes