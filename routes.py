import json
from flask import render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
from app import app, db
from models import TradingConfig, SymbolConfig, WebhookAlert, TradeExecution
from webhook_handler import WebhookHandler
from mt5_trader import MT5Trader
from auth import auth_manager, login_required, admin_required

# Initialize webhook handler without immediate MT5 connection
webhook_handler = None

def get_webhook_handler():
    """Get or create webhook handler with proper app context"""
    global webhook_handler
    if webhook_handler is None:
        webhook_handler = WebhookHandler()
        webhook_handler._connect_mt5()
    return webhook_handler

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if auth_manager.is_authenticated():
        return redirect(url_for('nlb_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        csrf_token = request.form.get('csrf_token', '')
        
        # Validate CSRF token
        if not auth_manager.validate_csrf_token(csrf_token):
            flash('Security token invalid. Please try again.', 'error')
            return render_template('login.html', csrf_token=auth_manager.generate_csrf_token())
        
        if auth_manager.login_user(username, password):
            flash('Login successful!', 'success')
            
            # Redirect to intended page or dashboard
            next_url = session.pop('next_url', url_for('nlb_dashboard'))
            return redirect(next_url)
        else:
            flash('Invalid username or password.', 'error')
    
    # Show credentials in development mode
    admin_user, admin_pass = auth_manager.get_admin_credentials()
    show_credentials = True  # Always show custom credentials
    
    return render_template('login.html', 
                         csrf_token=auth_manager.generate_csrf_token(),
                         show_credentials=show_credentials,
                         admin_username=admin_user,
                         admin_password=admin_pass if show_credentials else None)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    auth_manager.logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Redirect to NextLevelBot-style dashboard"""
    return redirect(url_for('nlb_dashboard'))

@app.route('/old')
@login_required
def old_dashboard():
    """Original dashboard page"""
    # Get recent alerts and trades
    recent_alerts = WebhookAlert.query.order_by(WebhookAlert.received_at.desc()).limit(10).all()
    recent_trades = TradeExecution.query.order_by(TradeExecution.executed_at.desc()).limit(10).all()
    
    # Get trading statistics
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    stats = {
        'total_alerts': WebhookAlert.query.count(),
        'total_trades': TradeExecution.query.count(),
        'today_alerts': WebhookAlert.query.filter(WebhookAlert.received_at >= today_start).count(),
        'today_trades': TradeExecution.query.filter(TradeExecution.executed_at >= today_start).count(),
        'successful_trades': TradeExecution.query.filter_by(status='FILLED').count(),
        'failed_trades': TradeExecution.query.filter_by(status='FAILED').count()
    }
    
    # Get account info if connected
    account_info = None
    positions = []
    try:
        handler = get_webhook_handler()
        if handler.mt5_trader.is_connected:
            account_info = handler.mt5_trader.get_account_info()
            positions = handler.mt5_trader.get_positions()
    except Exception as e:
        app.logger.error(f"Error getting MT5 info: {str(e)}")
    
    return render_template('dashboard.html', 
                         recent_alerts=recent_alerts,
                         recent_trades=recent_trades,
                         stats=stats,
                         account_info=account_info,
                         positions=positions)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for TradingView alerts"""
    try:
        # Get API key from headers or query params
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key', '')
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Process webhook
        handler = get_webhook_handler()
        success, message, ticket = handler.process_webhook(data, api_key)
        
        if success:
            response = {'status': 'success', 'message': message}
            if ticket:
                response['ticket'] = str(ticket)
            return jsonify(response), 200
        else:
            return jsonify({'status': 'error', 'message': message}), 400
            
    except Exception as e:
        app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/settings')
@admin_required
def settings():
    """Trading settings page"""
    config = TradingConfig.query.first()
    if not config:
        config = TradingConfig()
        db.session.add(config)
        db.session.commit()
    
    symbols = SymbolConfig.query.all()
    return render_template('settings.html', config=config, symbols=symbols)

@app.route('/settings/trading', methods=['POST'])
@admin_required
def update_trading_settings():
    """Update trading configuration"""
    try:
        config = TradingConfig.query.first()
        if not config:
            config = TradingConfig()
            db.session.add(config)
        
        config.mt5_server_ip = request.form.get('mt5_server_ip', '')
        config.mt5_server_port = int(request.form.get('mt5_server_port', 443))
        config.mt5_login = request.form.get('mt5_login', '')
        config.mt5_password = request.form.get('mt5_password', '')
        config.default_lot_size = float(request.form.get('default_lot_size', 0.01))
        config.max_daily_trades = int(request.form.get('max_daily_trades', 10))
        config.max_risk_per_trade = float(request.form.get('max_risk_per_trade', 2.0))
        config.slippage = int(request.form.get('slippage', 3))
        config.is_active = 'is_active' in request.form
        config.api_key = request.form.get('api_key', 'webhook-api-key')
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Reconnect MT5 with new settings
        handler = get_webhook_handler()
        handler._connect_mt5()
        
        flash('Trading settings updated successfully', 'success')
        
    except Exception as e:
        app.logger.error(f"Error updating settings: {str(e)}")
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/settings/symbol', methods=['POST'])
def add_symbol():
    """Add or update symbol configuration"""
    try:
        symbol = request.form.get('symbol', '').upper()
        if not symbol:
            flash('Symbol name is required', 'error')
            return redirect(url_for('settings'))
        
        # Check if symbol already exists
        existing = SymbolConfig.query.filter_by(symbol=symbol).first()
        if existing:
            # Update existing
            existing.lot_size = float(request.form.get('lot_size', 0.01))
            existing.max_position_size = float(request.form.get('max_position_size', 1.0))
            existing.is_enabled = 'is_enabled' in request.form
        else:
            # Create new
            symbol_config = SymbolConfig(
                symbol=symbol,
                lot_size=float(request.form.get('lot_size', 0.01)),
                max_position_size=float(request.form.get('max_position_size', 1.0)),
                is_enabled='is_enabled' in request.form
            )
            db.session.add(symbol_config)
        
        db.session.commit()
        flash(f'Symbol {symbol} configuration saved', 'success')
        
    except Exception as e:
        app.logger.error(f"Error saving symbol: {str(e)}")
        flash(f'Error saving symbol: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/settings/symbol/<int:symbol_id>/delete', methods=['POST'])
def delete_symbol(symbol_id):
    """Delete symbol configuration"""
    try:
        symbol = SymbolConfig.query.get_or_404(symbol_id)
        symbol_name = symbol.symbol
        db.session.delete(symbol)
        db.session.commit()
        flash(f'Symbol {symbol_name} deleted', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting symbol: {str(e)}")
        flash(f'Error deleting symbol: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/logs')
@login_required
def logs():
    """View trading logs"""
    page = request.args.get('page', 1, type=int)
    
    # Get alerts with pagination
    alerts = WebhookAlert.query.order_by(WebhookAlert.received_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('logs.html', alerts=alerts)

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test MT5 connection"""
    try:
        config = TradingConfig.query.first()
        if not config:
            return jsonify({'success': False, 'message': 'No configuration found'})
        
        trader = MT5Trader()
        server_address = f"{config.mt5_server_ip}:{config.mt5_server_port}"
        success = trader.connect(server_address, config.mt5_login, config.mt5_password)
        
        if success:
            account_info = trader.get_account_info()
            trader.disconnect()
            return jsonify({
                'success': True, 
                'message': 'Connection successful',
                'account_info': account_info
            })
        else:
            return jsonify({'success': False, 'message': 'Connection failed'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        # Get time range from query params
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get alerts and trades in time range
        alerts = WebhookAlert.query.filter(WebhookAlert.received_at >= since).all()
        trades = TradeExecution.query.filter(TradeExecution.executed_at >= since).all()
        
        # Calculate statistics
        stats = {
            'alerts_count': len(alerts),
            'trades_count': len(trades),
            'successful_trades': len([t for t in trades if t.status == 'FILLED']),
            'failed_trades': len([t for t in trades if t.status == 'FAILED']),
            'total_profit': sum([t.profit or 0 for t in trades if t.profit]),
            'alerts_by_hour': {},
            'trades_by_symbol': {}
        }
        
        # Group alerts by hour
        for alert in alerts:
            hour = alert.received_at.replace(minute=0, second=0, microsecond=0)
            hour_str = hour.strftime('%Y-%m-%d %H:00')
            stats['alerts_by_hour'][hour_str] = stats['alerts_by_hour'].get(hour_str, 0) + 1
        
        # Group trades by symbol
        for trade in trades:
            symbol = trade.symbol
            if symbol not in stats['trades_by_symbol']:
                stats['trades_by_symbol'][symbol] = {'count': 0, 'profit': 0}
            stats['trades_by_symbol'][symbol]['count'] += 1
            stats['trades_by_symbol'][symbol]['profit'] += trade.profit or 0
        
        return jsonify(stats)
        
    except Exception as e:
        app.logger.error(f"API stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connection-status')
def api_connection_status():
    """API endpoint for MT5 connection status"""
    try:
        handler = get_webhook_handler()
        config = TradingConfig.query.first()
        
        if not config:
            return jsonify({
                'connected': False,
                'message': 'No configuration found',
                'account_info': None
            })
        
        # Check if trader is connected
        is_connected = handler.mt5_trader.is_connected
        
        if is_connected:
            account_info = handler.mt5_trader.get_account_info()
            return jsonify({
                'connected': True,
                'message': 'Connected',
                'account_info': account_info,
                'config': {
                    'login': config.mt5_login,
                    'server': f"{config.mt5_server_ip}:{config.mt5_server_port}"
                }
            })
        else:
            return jsonify({
                'connected': False,
                'message': 'Not connected',
                'account_info': None,
                'config': {
                    'login': config.mt5_login,
                    'server': f"{config.mt5_server_ip}:{config.mt5_server_port}"
                }
            })
            
    except Exception as e:
        app.logger.error(f"Connection status error: {str(e)}")
        return jsonify({
            'connected': False,
            'message': f'Error: {str(e)}',
            'account_info': None
        }), 500

# NextLevelBot-style routes for multiple accounts
@app.route('/nlb')
@login_required
def nlb_dashboard():
    """NextLevelBot-style dashboard"""
    try:
        from multi_account_manager import get_multi_account_manager
        manager = get_multi_account_manager()
        dashboard_data = manager.get_dashboard_stats()
        return render_template('dashboard_nlb.html', **dashboard_data)
    except Exception as e:
        app.logger.error(f"NLB Dashboard error: {str(e)}")
        # Fallback to basic data
        accounts = []
        stats = {'total_alerts': 0, 'total_trades': 0, 'successful_trades': 0, 'failed_trades': 0, 'success_rate': 0}
        return render_template('dashboard_nlb.html', accounts=accounts, stats=stats, recent_alerts=[])

@app.route('/webhook/<webhook_key>', methods=['POST'])
def webhook_multi_account(webhook_key):
    """Handle webhook for specific account using unique key"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided',
                'code': 'INVALID_DATA'
            }), 400
        
        from multi_account_manager import get_multi_account_manager
        manager = get_multi_account_manager()
        
        success, ticket, message = manager.process_webhook_for_account(webhook_key, data)
        
        if success:
            response = {
                'status': 'success',
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'bridge': 'MT5-NextLevelBot-Style',
                'webhook_key': webhook_key
            }
            if ticket:
                response['ticket'] = str(ticket)
                response['trade_id'] = str(ticket)
            return jsonify(response), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_key': webhook_key,
                'code': 'PROCESSING_ERROR'
            }), 400
            
    except Exception as e:
        app.logger.error(f"Multi-account webhook error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'timestamp': datetime.utcnow().isoformat(),
            'code': 'INTERNAL_ERROR'
        }), 500

# Symbol Management API
@app.route('/api/symbols')
@login_required
def get_symbols():
    """Get available MT5 symbols"""
    try:
        handler = get_webhook_handler()
        symbols = handler.mt5_trader.get_symbols(limit=100)
        
        return jsonify({
            'status': 'success',
            'symbols': symbols,
            'count': len(symbols),
            'connection_status': handler.mt5_trader.is_connected
        })
    except Exception as e:
        app.logger.error(f"Error getting symbols: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get symbols',
            'connection_status': False
        }), 500

@app.route('/api/symbol/<symbol_name>')
@login_required
def get_symbol_detail(symbol_name):
    """Get detailed symbol information"""
    try:
        handler = get_webhook_handler()
        symbol_detail = handler.mt5_trader.get_symbol_detail(symbol_name)
        
        if symbol_detail is None:
            return jsonify({
                'status': 'error',
                'message': f'Symbol {symbol_name} not found or connection failed'
            }), 404
        
        return jsonify({
            'status': 'success',
            'symbol': symbol_detail,
            'connection_status': handler.mt5_trader.is_connected
        })
    except Exception as e:
        app.logger.error(f"Error getting symbol detail for {symbol_name}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get symbol detail for {symbol_name}'
        }), 500

@app.route('/symbols')
@login_required
def symbols_page():
    """Symbols management page"""
    try:
        handler = get_webhook_handler()
        symbols = handler.mt5_trader.get_symbols(limit=100)
        account_info = handler.mt5_trader.get_account_info()
        
        return render_template('symbols.html', 
                             symbols=symbols, 
                             account_info=account_info,
                             connection_status=handler.mt5_trader.is_connected)
    except Exception as e:
        app.logger.error(f"Symbols page error: {str(e)}")
        return render_template('symbols.html', 
                             symbols=[], 
                             account_info=None,
                             connection_status=False,
                             error_message=str(e))

# Account Management Routes
@app.route('/accounts/add')
@login_required
def add_account():
    """Add new trading account page"""
    return render_template('add_account.html')

@app.route('/accounts/add', methods=['POST'])
@login_required
def create_account():
    """Create new trading account"""
    try:
        from models import TradingAccount
        import secrets
        
        # Generate unique webhook key
        webhook_key = secrets.token_urlsafe(32)
        
        account = TradingAccount(
            account_name=request.form.get('account_name', '').strip(),
            mt5_server_ip=request.form.get('mt5_server_ip', '').strip(),
            mt5_server_port=int(request.form.get('mt5_server_port', 443)),
            mt5_login=request.form.get('mt5_login', '').strip(),
            mt5_password=request.form.get('mt5_password', '').strip(),
            broker_type=request.form.get('broker_type', 'MT5'),
            webhook_key=webhook_key,
            default_lot_size=float(request.form.get('default_lot_size', 0.01)),
            max_daily_trades=int(request.form.get('max_daily_trades', 10)),
            max_risk_per_trade=float(request.form.get('max_risk_per_trade', 2.0)),
            slippage=int(request.form.get('slippage', 3)),
            is_active=True
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash(f'Account "{account.account_name}" created successfully!', 'success')
        return redirect(url_for('nlb_dashboard'))
        
    except Exception as e:
        app.logger.error(f"Error creating account: {str(e)}")
        flash(f'Error creating account: {str(e)}', 'error')
        return redirect(url_for('add_account'))

@app.route('/accounts/<int:account_id>/edit')
@login_required
def edit_account(account_id):
    """Edit account page"""
    from models import TradingAccount
    account = TradingAccount.query.get_or_404(account_id)
    return render_template('add_account.html', account=account, edit_mode=True)

@app.route('/accounts/<int:account_id>/edit', methods=['POST'])
@login_required
def update_account(account_id):
    """Update existing account"""
    try:
        from models import TradingAccount
        account = TradingAccount.query.get_or_404(account_id)
        
        account.account_name = request.form.get('account_name', '').strip()
        account.mt5_server_ip = request.form.get('mt5_server_ip', '').strip()
        account.mt5_server_port = int(request.form.get('mt5_server_port', 443))
        account.mt5_login = request.form.get('mt5_login', '').strip()
        account.mt5_password = request.form.get('mt5_password', '').strip()
        account.broker_type = request.form.get('broker_type', 'MT5')
        account.default_lot_size = float(request.form.get('default_lot_size', 0.01))
        account.max_daily_trades = int(request.form.get('max_daily_trades', 10))
        account.max_risk_per_trade = float(request.form.get('max_risk_per_trade', 2.0))
        account.slippage = int(request.form.get('slippage', 3))
        account.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Account "{account.account_name}" updated successfully!', 'success')
        return redirect(url_for('nlb_dashboard'))
        
    except Exception as e:
        app.logger.error(f"Error updating account: {str(e)}")
        flash(f'Error updating account: {str(e)}', 'error')
        return redirect(url_for('edit_account', account_id=account_id))

@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    """Delete account"""
    try:
        from models import TradingAccount
        account = TradingAccount.query.get_or_404(account_id)
        account_name = account.account_name
        
        db.session.delete(account)
        db.session.commit()
        
        flash(f'Account "{account_name}" deleted successfully!', 'success')
        
    except Exception as e:
        app.logger.error(f"Error deleting account: {str(e)}")
        flash(f'Error deleting account: {str(e)}', 'error')
    
    return redirect(url_for('nlb_dashboard'))

@app.route('/api/accounts/<int:account_id>/test', methods=['POST'])
@login_required
def test_account_connection(account_id):
    """Test MT5 connection for specific account"""
    try:
        from models import TradingAccount
        from mt5_trader import MT5Trader
        
        account = TradingAccount.query.get_or_404(account_id)
        
        # Create temporary MT5 trader for testing
        trader = MT5Trader()
        
        # Test connection with account credentials
        if account.mt5_login and account.mt5_password:
            server_address = f"{account.mt5_server_ip}:{account.mt5_server_port}"
            success = trader.connect(
                server=server_address,
                login=account.mt5_login,
                password=account.mt5_password
            )
        else:
            # Demo mode test
            success = trader.connect(server="", login="", password="")
        
        if success:
            account_info = trader.get_account_info()
            trader.disconnect()
            
            # Update connection status
            account.is_connected = True
            account.last_connected = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Connection successful! Account: {account_info.get("login", "Demo")}',
                'account_info': account_info
            })
        else:
            trader.disconnect()
            account.is_connected = False
            db.session.commit()
            
            return jsonify({
                'success': False,
                'message': 'Failed to connect to MT5. Please check your credentials.'
            })
            
    except Exception as e:
        app.logger.error(f"Error testing account connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        })
