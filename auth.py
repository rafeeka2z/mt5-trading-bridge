#!/usr/bin/env python3
"""
Authentication system for MT5 Trading Bridge
Protects sensitive trading credentials from unauthorized access
"""

import hashlib
import secrets
import os
from functools import wraps
from flask import session, request, redirect, url_for, flash, render_template, jsonify
from datetime import datetime, timedelta

class AuthManager:
    """Manages user authentication and session security"""
    
    def __init__(self, app=None):
        self.app = app
        self.session_timeout = 24 * 60 * 60  # 24 hours in seconds
        
    def init_app(self, app):
        """Initialize authentication with Flask app"""
        self.app = app
        
        # Set secure session configuration
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.permanent_session_lifetime = timedelta(hours=24)
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt for secure storage"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256 for password hashing
        pwd_hash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt.encode('utf-8'), 
                                      100000)  # 100,000 iterations
        
        return pwd_hash.hex(), salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        try:
            pwd_hash, _ = self.hash_password(password, salt)
            return pwd_hash == stored_hash
        except Exception:
            return False
    
    def get_admin_credentials(self):
        """Get admin credentials from environment or defaults"""
        # Try to get from environment first (production)
        admin_user = os.environ.get('ADMIN_USERNAME', 'ramshad')
        admin_pass = os.environ.get('ADMIN_PASSWORD', 'Trading@123')
        
        return admin_user, admin_pass
    
    def is_authenticated(self) -> bool:
        """Check if current session is authenticated"""
        if 'authenticated' not in session:
            return False
        
        # Check session timeout
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > timedelta(seconds=self.session_timeout):
                session.clear()
                return False
        
        return session.get('authenticated', False)
    
    def login_user(self, username: str, password: str) -> bool:
        """Authenticate user and create session"""
        admin_user, admin_pass = self.get_admin_credentials()
        
        # Simple credential check (can be enhanced with database)
        if username == admin_user and password == admin_pass:
            session.permanent = True
            session['authenticated'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            session['csrf_token'] = secrets.token_hex(32)
            return True
        
        return False
    
    def logout_user(self):
        """Clear user session"""
        session.clear()
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token for forms"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        return session.get('csrf_token') == token

# Global auth manager instance
auth_manager = AuthManager()

def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_manager.is_authenticated():
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Store the attempted URL for redirect after login
            session['next_url'] = request.url
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_manager.is_authenticated():
            return redirect(url_for('login'))
        
        # Additional admin checks can be added here
        return f(*args, **kwargs)
    return decorated_function