"""
Chat Blueprint - Real-time messaging between users
"""
from flask import Blueprint

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

from . import routes
