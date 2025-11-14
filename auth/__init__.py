"""
SparzaFi Authentication Blueprint
Handles user registration, login, logout, and KYC verification
"""

# Import blueprint from routes module
from .routes import auth_bp

__all__ = ['auth_bp']