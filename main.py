import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "webhook-bridge-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///webhook_bridge.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Minimal models
class TradingConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mt5_server_ip = db.Column(db.String(100), nullable=False, default="")
    mt5_login = db.Column(db.String(50), nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    api_key = db.Column(db.String(100), nullable=False, default="webhook-api-key")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Simple auth functions
def get_admin_credentials():
    return os.environ.get('ADMIN_USERNAME', 'ramshad'), os.environ.get('ADMIN_PASSWORD', 'Trading@123')

def is_authenticated():
    return session.get('authenticated', False)

def login_user(username, password):
    admin_user, admin_pass = get_admin_credentials()
    if username == admin_user and password == admin_pass:
        session['authenticated'] = True
        session.permanent = True
        return True
    return False

def login_required(f):
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if login_user(username, password):
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    admin_user, admin_pass = get_admin_credentials()
    return render_template('login.html', 
                         show_credentials=True,
                         admin_username=admin_user,
                         admin_password=admin_pass)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/webhook/<webhook_key>', methods=['POST'])
def webhook_endpoint(webhook_key):
    """Simple webhook endpoint for testing"""
    try:
        data = request.get_json(force=True)
        logging.info(f"Webhook received: {webhook_key}, Data: {data}")
        return {"status": "success", "message": "Webhook received"}, 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}, 400

# Create tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
