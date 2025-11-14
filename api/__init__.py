"""
SparzaFi API Blueprint
RESTful API for fintech operations, mobile apps, and third-party integrations
"""

from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes after blueprint creation to avoid circular imports
from . import routes
