#!/usr/bin/env python3
"""
Multi-account management system for MT5/MT4 - NextLevelBot style
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from app import db
from models import TradingAccount, WebhookAlert, TradeExecution
from mt5_trader import MT5Trader

class MultiAccountManager:
    """Manages multiple MT5/MT4 trading accounts with unique webhooks"""
    
    def __init__(self):
        self.active_connections = {}  # account_id -> MT5Trader instance
        
    def create_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """Create new trading account with unique webhook key"""
        try:
            # Generate unique webhook key
            webhook_key = str(uuid.uuid4())[:8] + "-" + str(uuid.uuid4())[:8]
            
            account = TradingAccount()
            account.account_name = account_data['account_name']
            account.mt5_server_ip = account_data['server_ip']
            account.mt5_server_port = account_data.get('server_port', 443)
            account.mt5_login = account_data['login']
            account.mt5_password = account_data['password']
            account.broker_type = account_data.get('broker_type', 'MT5')
            account.webhook_key = webhook_key
            account.default_lot_size = account_data.get('lot_size', 0.01)
            account.max_daily_trades = account_data.get('max_trades', 10)
            account.max_risk_per_trade = account_data.get('max_risk', 2.0)
            account.slippage = account_data.get('slippage', 3)
            
            db.session.add(account)
            db.session.commit()
            
            logging.info(f"Created new account: {account.account_name} (ID: {account.id})")
            return True, f"Account created with webhook key: {webhook_key}", account.id
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to create account: {str(e)}"
            logging.error(error_msg)
            return False, error_msg, None
    
    def get_all_accounts(self) -> List[TradingAccount]:
        """Get all trading accounts"""
        return TradingAccount.query.filter_by(is_active=True).all()
    
    def get_account_by_webhook_key(self, webhook_key: str) -> Optional[TradingAccount]:
        """Get account by webhook key"""
        return TradingAccount.query.filter_by(webhook_key=webhook_key, is_active=True).first()
    
    def get_account_by_id(self, account_id: int) -> Optional[TradingAccount]:
        """Get account by ID"""
        return TradingAccount.query.filter_by(id=account_id, is_active=True).first()
    
    def test_account_connection(self, account_id: int) -> Tuple[bool, str]:
        """Test connection to specific account"""
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                return False, "Account not found"
            
            # Create MT5 trader instance
            trader = MT5Trader()
            server = f"{account.mt5_server_ip}:{account.mt5_server_port}"
            
            success = trader.connect(server, account.mt5_login, account.mt5_password)
            
            if success:
                # Update account status
                account.is_connected = True
                account.last_connected = datetime.utcnow()
                db.session.commit()
                
                # Store active connection
                self.active_connections[account_id] = trader
                
                logging.info(f"Successfully connected to account {account.account_name}")
                return True, "Connection successful"
            else:
                account.is_connected = False
                db.session.commit()
                return False, "Failed to connect to MT5"
                
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def execute_trade_for_account(self, account_id: int, trade_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Execute trade for specific account"""
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                return False, None, "Account not found"
            
            # Get or create MT5 connection
            if account_id not in self.active_connections:
                success, message = self.test_account_connection(account_id)
                if not success:
                    return False, None, f"Failed to connect: {message}"
            
            trader = self.active_connections[account_id]
            
            # Execute trade using existing MT5Trader logic
            symbol = trade_data.get('symbol')
            action = trade_data.get('action')
            volume = trade_data.get('volume', account.default_lot_size)
            price = trade_data.get('price')
            stop_loss = trade_data.get('stop_loss') or trade_data.get('sl')
            take_profit = trade_data.get('take_profit') or trade_data.get('tp')
            
            if action and action.upper() == 'CLOSE':
                success, message = trader.close_position(symbol)
                ticket = None
            else:
                success, ticket, message = trader.execute_trade(
                    symbol=symbol,
                    action=action,
                    volume=volume,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            # Update account statistics
            if success:
                account.total_trades += 1
                account.successful_trades += 1
            else:
                account.total_trades += 1
                account.failed_trades += 1
            
            db.session.commit()
            
            return success, str(ticket) if ticket else None, message
            
        except Exception as e:
            error_msg = f"Trade execution failed: {str(e)}"
            logging.error(error_msg)
            return False, None, error_msg
    
    def process_webhook_for_account(self, webhook_key: str, webhook_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Process webhook for specific account based on webhook key"""
        try:
            # Find account by webhook key
            account = self.get_account_by_webhook_key(webhook_key)
            if not account:
                return False, None, f"Invalid webhook key: {webhook_key}"
            
            # Log webhook alert
            alert = WebhookAlert(
                account_id=account.id,
                symbol=webhook_data.get('symbol', ''),
                action=webhook_data.get('action', ''),
                price=webhook_data.get('price'),
                volume=webhook_data.get('volume'),
                stop_loss=webhook_data.get('stop_loss') or webhook_data.get('sl'),
                take_profit=webhook_data.get('take_profit') or webhook_data.get('tp'),
                raw_data=str(webhook_data),
                status='RECEIVED'
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # Execute trade
            success, ticket, message = self.execute_trade_for_account(account.id, webhook_data)
            
            # Update alert status
            alert.status = 'PROCESSED' if success else 'FAILED'
            alert.error_message = None if success else message
            alert.processed_at = datetime.utcnow()
            
            # Log trade execution if successful
            if success and ticket:
                trade = TradeExecution(
                    webhook_alert_id=alert.id,
                    mt5_ticket=int(ticket),
                    symbol=webhook_data.get('symbol', ''),
                    action=webhook_data.get('action', ''),
                    volume=webhook_data.get('volume', account.default_lot_size),
                    open_price=webhook_data.get('price'),
                    stop_loss=webhook_data.get('stop_loss') or webhook_data.get('sl'),
                    take_profit=webhook_data.get('take_profit') or webhook_data.get('tp'),
                    status='FILLED'
                )
                db.session.add(trade)
            
            db.session.commit()
            
            logging.info(f"Processed webhook for account {account.account_name}: {message}")
            return success, ticket, message
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Webhook processing failed: {str(e)}"
            logging.error(error_msg)
            return False, None, error_msg
    
    def delete_account(self, account_id: int) -> Tuple[bool, str]:
        """Delete trading account"""
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                return False, "Account not found"
            
            # Disconnect if connected
            if account_id in self.active_connections:
                self.active_connections[account_id].disconnect()
                del self.active_connections[account_id]
            
            # Soft delete (set inactive)
            account.is_active = False
            db.session.commit()
            
            logging.info(f"Deleted account: {account.account_name}")
            return True, "Account deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to delete account: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics for all accounts"""
        accounts = self.get_all_accounts()
        
        total_alerts = WebhookAlert.query.count()
        total_trades = sum(account.total_trades for account in accounts)
        successful_trades = sum(account.successful_trades for account in accounts)
        failed_trades = sum(account.failed_trades for account in accounts)
        
        success_rate = 0
        if total_trades > 0:
            success_rate = round((successful_trades / total_trades) * 100, 1)
        
        recent_alerts = WebhookAlert.query.order_by(WebhookAlert.received_at.desc()).limit(10).all()
        
        return {
            'accounts': accounts,
            'stats': {
                'total_alerts': total_alerts,
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'failed_trades': failed_trades,
                'success_rate': success_rate
            },
            'recent_alerts': recent_alerts,
            'total_accounts': len(accounts)
        }

# Global instance
multi_account_manager = MultiAccountManager()

def get_multi_account_manager() -> MultiAccountManager:
    """Get global multi-account manager instance"""
    return multi_account_manager