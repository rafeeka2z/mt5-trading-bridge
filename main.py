import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "webhook-bridge-secret-key")

# Login template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MT5 Trading Bridge - Login</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header"><h3>MT5 Trading Bridge Login</h3></div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }}">{{ message }}</div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        <form method="POST">
                            <div class="mb-3">
                                <label class="form-label">Username</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary">Login</button>
                        </form>
                        <div class="mt-3 text-muted">
                            <small>Credentials: {{ admin_username }} / {{ admin_password }}</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Dashboard template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MT5 Trading Bridge - Dashboard</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand">MT5 Trading Bridge</span>
            <a href="/logout" class="btn btn-outline-light">Logout</a>
        </div>
    </nav>
    <div class="container mt-4">
        <h1>Trading Dashboard</h1>
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header"><h5>Webhook Information</h5></div>
                    <div class="card-body">
                        <p><strong>Your Webhook URL:</strong></p>
                        <code>https://a2ztrading-a7c73d7225ba.herokuapp.com/webhook/afcdc49e-7cbffed4</code>
                        <p class="mt-3">Use this URL in your TradingView alerts.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header"><h5>System Status</h5></div>
                    <div class="card-body">
                        <p><span class="badge bg-success">✓</span> Heroku App Running</p>
                        <p><span class="badge bg-success">✓</span> Webhook Endpoint Active</p>
                        <p><span class="badge bg-warning">!</span> MT5 Connection (Demo Mode)</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Auth functions
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
    return render_template_string(LOGIN_TEMPLATE, 
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
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/webhook/<webhook_key>', methods=['POST'])
def webhook_endpoint(webhook_key):
    """Webhook endpoint for TradingView alerts"""
    try:
        data = request.get_json(force=True) if request.is_json else request.form.to_dict()
        
        if webhook_key != "afcdc49e-7cbffed4":
            return {"status": "error", "message": "Invalid webhook key"}, 401
        
        app.logger.info(f"Webhook received: {data}")
        
        return {
            "status": "success", 
            "message": "Webhook received successfully",
            "data_received": data
        }, 200
        
    except Exception as e:
        app.logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}, 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
