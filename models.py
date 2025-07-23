from datetime import datetime
from app import db

class TradingAccount(db.Model):
    """Multiple MT5/MT4 account support - NextLevelBot style"""
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)  # User-friendly name
    mt5_server_ip = db.Column(db.String(100), nullable=False, default="")
    mt5_server_port = db.Column(db.Integer, nullable=False, default=443)
    mt5_login = db.Column(db.String(50), nullable=False, default="")
    mt5_password = db.Column(db.String(100), nullable=False, default="")
    broker_type = db.Column(db.String(20), nullable=False, default="MT5")  # MT5 or MT4
    
    # Unique webhook endpoint for each account
    webhook_key = db.Column(db.String(100), nullable=False, unique=True)
    
    # Trading settings
    default_lot_size = db.Column(db.Float, nullable=False, default=0.01)
    max_daily_trades = db.Column(db.Integer, nullable=False, default=10)
    max_risk_per_trade = db.Column(db.Float, nullable=False, default=2.0)
    slippage = db.Column(db.Integer, nullable=False, default=3)
    
    # Account status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_connected = db.Column(db.Boolean, nullable=False, default=False)
    last_connected = db.Column(db.DateTime)
    
    # Statistics
    total_trades = db.Column(db.Integer, nullable=False, default=0)
    successful_trades = db.Column(db.Integer, nullable=False, default=0)
    failed_trades = db.Column(db.Integer, nullable=False, default=0)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Keep old model for backward compatibility
class TradingConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mt5_server_ip = db.Column(db.String(100), nullable=False, default="")
    mt5_server_port = db.Column(db.Integer, nullable=False, default=443)
    mt5_login = db.Column(db.String(50), nullable=False, default="")
    mt5_password = db.Column(db.String(100), nullable=False, default="")
    default_lot_size = db.Column(db.Float, nullable=False, default=0.01)
    max_daily_trades = db.Column(db.Integer, nullable=False, default=10)
    max_risk_per_trade = db.Column(db.Float, nullable=False, default=2.0)  # Percentage
    slippage = db.Column(db.Integer, nullable=False, default=3)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    api_key = db.Column(db.String(100), nullable=False, default="webhook-api-key")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class SymbolConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False, unique=True)
    lot_size = db.Column(db.Float, nullable=False, default=0.01)
    max_position_size = db.Column(db.Float, nullable=False, default=1.0)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(SymbolConfig, self).__init__(**kwargs)

class WebhookAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('trading_account.id'))  # Link to specific account
    symbol = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # BUY, SELL, CLOSE
    price = db.Column(db.Float)
    volume = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    raw_data = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="RECEIVED")  # RECEIVED, PROCESSED, FAILED
    error_message = db.Column(db.Text)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationship
    trading_account = db.relationship('TradingAccount', backref='webhook_alerts')
    
    def __init__(self, **kwargs):
        super(WebhookAlert, self).__init__(**kwargs)

class TradeExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    webhook_alert_id = db.Column(db.Integer, db.ForeignKey('webhook_alert.id'))
    mt5_ticket = db.Column(db.Integer)
    symbol = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(10), nullable=False)
    volume = db.Column(db.Float, nullable=False)
    open_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    profit = db.Column(db.Float, default=0.0)
    commission = db.Column(db.Float, default=0.0)
    swap = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="PENDING")  # PENDING, FILLED, CLOSED, FAILED
    error_message = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super(TradeExecution, self).__init__(**kwargs)
    
    # Relationship
    webhook_alert = db.relationship('WebhookAlert', backref='trade_executions')
