import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from app import db
from models import WebhookAlert, TradeExecution, TradingConfig, SymbolConfig
from mt5_trader import MT5Trader

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self):
        self.mt5_trader = MT5Trader()
        # Don't connect MT5 in constructor to avoid app context issues
    
    def _connect_mt5(self):
        """Initialize MT5 connection using config"""
        try:
            config = TradingConfig.query.first()
            if config and config.is_active:
                # For demo mode, use empty credentials to trigger demo connection
                if not config.mt5_login or not config.mt5_password:
                    logger.info("Using demo mode - no MT5 credentials provided")
                    success = self.mt5_trader.connect(
                        server="",
                        login="",
                        password=""
                    )
                else:
                    # Combine IP and port for server connection
                    server_address = f"{config.mt5_server_ip}:{config.mt5_server_port}"
                    success = self.mt5_trader.connect(
                        server=server_address,
                        login=config.mt5_login,
                        password=config.mt5_password
                    )
                
                if success:
                    logger.info("MT5 connection established")
                else:
                    logger.error("Failed to connect to MT5")
            else:
                logger.warning("No active trading configuration found")
        except Exception as e:
            logger.error(f"Error connecting to MT5: {str(e)}")
    
    def validate_api_key(self, provided_key: str) -> bool:
        """Validate API key from webhook request"""
        try:
            config = TradingConfig.query.first()
            if config and config.api_key == provided_key:
                return True
            return False
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return False
    
    def parse_webhook_data(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Parse and validate webhook data from TradingView"""
        try:
            # Common TradingView webhook fields
            required_fields = ['symbol', 'action']
            parsed_data = {}
            
            # Extract and validate required fields
            for field in required_fields:
                if field not in data:
                    return False, {}, f"Missing required field: {field}"
                parsed_data[field] = data[field]
            
            # Validate action
            valid_actions = ['BUY', 'SELL', 'CLOSE']
            if parsed_data['action'].upper() not in valid_actions:
                return False, {}, f"Invalid action: {parsed_data['action']}"
            
            parsed_data['action'] = parsed_data['action'].upper()
            
            # Extract optional fields
            optional_fields = {
                'price': float,
                'volume': float,
                'stop_loss': float,
                'take_profit': float,
                'sl': float,  # Alternative for stop_loss
                'tp': float   # Alternative for take_profit
            }
            
            for field, field_type in optional_fields.items():
                if field in data and data[field] is not None:
                    try:
                        parsed_data[field] = field_type(data[field])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid {field} value: {data[field]}")
            
            # Handle alternative field names
            if 'sl' in parsed_data and 'stop_loss' not in parsed_data:
                parsed_data['stop_loss'] = parsed_data['sl']
            if 'tp' in parsed_data and 'take_profit' not in parsed_data:
                parsed_data['take_profit'] = parsed_data['tp']
            
            return True, parsed_data, "Success"
            
        except Exception as e:
            logger.error(f"Error parsing webhook data: {str(e)}")
            return False, {}, f"Parsing error: {str(e)}"
    
    def check_risk_limits(self, symbol: str, volume: float) -> Tuple[bool, str]:
        """Check if trade meets risk management criteria"""
        try:
            config = TradingConfig.query.first()
            if not config:
                return False, "No trading configuration found"
            
            # Check daily trade limit
            today = datetime.utcnow().date()
            daily_trades = TradeExecution.query.filter(
                TradeExecution.executed_at >= datetime.combine(today, datetime.min.time())
            ).count()
            
            if daily_trades >= config.max_daily_trades:
                return False, f"Daily trade limit reached: {daily_trades}/{config.max_daily_trades}"
            
            # Check symbol configuration
            symbol_config = SymbolConfig.query.filter_by(symbol=symbol).first()
            if symbol_config and not symbol_config.is_enabled:
                return False, f"Trading disabled for symbol: {symbol}"
            
            # Check position size limits
            if symbol_config and volume > symbol_config.max_position_size:
                return False, f"Volume exceeds limit: {volume} > {symbol_config.max_position_size}"
            
            return True, "Risk checks passed"
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {str(e)}")
            return False, f"Risk check error: {str(e)}"
    
    def process_webhook(self, data: Dict[str, Any], api_key: str) -> Tuple[bool, str, Optional[int]]:
        """Main webhook processing function"""
        try:
            # Validate API key
            if not self.validate_api_key(api_key):
                logger.warning("Invalid API key provided")
                return False, "Invalid API key", None
            
            # Parse webhook data
            is_valid, parsed_data, parse_message = self.parse_webhook_data(data)
            if not is_valid:
                logger.error(f"Invalid webhook data: {parse_message}")
                return False, parse_message, None
            
            # Create webhook alert record
            alert = WebhookAlert(
                symbol=parsed_data['symbol'],
                action=parsed_data['action'],
                price=parsed_data.get('price'),
                volume=parsed_data.get('volume'),
                stop_loss=parsed_data.get('stop_loss'),
                take_profit=parsed_data.get('take_profit'),
                raw_data=json.dumps(data),
                status='RECEIVED'
            )
            db.session.add(alert)
            db.session.commit()
            
            # Process the trade
            success, message, ticket = self._execute_trade(alert, parsed_data)
            
            # Update alert status
            alert.status = 'PROCESSED' if success else 'FAILED'
            alert.error_message = message if not success else None
            alert.processed_at = datetime.utcnow()
            db.session.commit()
            
            return success, message, ticket
            
        except Exception as e:
            error_msg = f"Webhook processing error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _execute_trade(self, alert: WebhookAlert, parsed_data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Execute the actual trade"""
        try:
            symbol = parsed_data['symbol']
            action = parsed_data['action']
            
            # Handle CLOSE action
            if action == 'CLOSE':
                return self._close_positions(alert, symbol)
            
            # Get trading configuration
            config = TradingConfig.query.first()
            if not config or not config.is_active:
                return False, "Trading configuration not active", None
            
            # Determine volume
            volume = parsed_data.get('volume', config.default_lot_size)
            symbol_config = SymbolConfig.query.filter_by(symbol=symbol).first()
            if symbol_config:
                volume = parsed_data.get('volume', symbol_config.lot_size)
            
            # Check risk limits
            risk_ok, risk_message = self.check_risk_limits(symbol, volume)
            if not risk_ok:
                return False, risk_message, None
            
            # Ensure MT5 is connected
            if not self.mt5_trader.is_connected:
                self._connect_mt5()
                if not self.mt5_trader.is_connected:
                    return False, "MT5 not connected", None
            
            # Execute trade
            success, ticket, message = self.mt5_trader.execute_trade(
                symbol=symbol,
                action=action,
                volume=volume,
                price=parsed_data.get('price'),
                stop_loss=parsed_data.get('stop_loss'),
                take_profit=parsed_data.get('take_profit'),
                slippage=config.slippage
            )
            
            # Create trade execution record
            execution = TradeExecution(
                webhook_alert_id=alert.id,
                mt5_ticket=ticket,
                symbol=symbol,
                action=action,
                volume=volume,
                open_price=parsed_data.get('price'),
                stop_loss=parsed_data.get('stop_loss'),
                take_profit=parsed_data.get('take_profit'),
                status='FILLED' if success else 'FAILED',
                error_message=message if not success else None
            )
            db.session.add(execution)
            db.session.commit()
            
            return success, message, ticket
            
        except Exception as e:
            error_msg = f"Trade execution error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _close_positions(self, alert: WebhookAlert, symbol: str) -> Tuple[bool, str, Optional[int]]:
        """Close all positions for a symbol"""
        try:
            if not self.mt5_trader.is_connected:
                self._connect_mt5()
                if not self.mt5_trader.is_connected:
                    return False, "MT5 not connected", None
            
            success, message = self.mt5_trader.close_position(symbol)
            
            # Create execution record
            execution = TradeExecution(
                webhook_alert_id=alert.id,
                symbol=symbol,
                action='CLOSE',
                volume=0.0,
                status='FILLED' if success else 'FAILED',
                error_message=message if not success else None
            )
            db.session.add(execution)
            db.session.commit()
            
            return success, message, None
            
        except Exception as e:
            error_msg = f"Position close error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
