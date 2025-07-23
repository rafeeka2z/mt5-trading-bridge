#!/usr/bin/env python3
"""
Multi-broker support system inspired by NextLevelBot architecture
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import logging

class BrokerInterface(ABC):
    """Abstract base class for broker implementations"""
    
    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    def execute_trade(self, trade_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Execute trade on broker"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        pass
    
    @abstractmethod
    def get_positions(self) -> list:
        """Get current positions"""
        pass

class MT5Broker(BrokerInterface):
    """MetaTrader 5 broker implementation"""
    
    def __init__(self):
        self.is_connected = False
        self.broker_name = "MetaTrader5"
        self.supported_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
        
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Connect to MT5"""
        try:
            server = credentials.get('server', '')
            login = credentials.get('login', '')
            password = credentials.get('password', '')
            
            # Use existing MT5Trader logic
            from mt5_trader import MT5Trader
            self.trader = MT5Trader()
            
            success = self.trader.connect(server, login, password)
            self.is_connected = success
            
            logging.info(f"MT5 connection: {'Success' if success else 'Failed'}")
            return success
            
        except Exception as e:
            logging.error(f"MT5 connection error: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from MT5"""
        if self.is_connected and hasattr(self, 'trader'):
            self.trader.disconnect()
            self.is_connected = False
            return True
        return False
    
    def execute_trade(self, trade_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Execute trade on MT5"""
        if not self.is_connected:
            return False, None, "Not connected to MT5"
        
        try:
            symbol = trade_data.get('symbol')
            action = trade_data.get('action')
            volume = trade_data.get('volume', 0.01)
            price = trade_data.get('price')
            stop_loss = trade_data.get('stop_loss') or trade_data.get('sl')
            take_profit = trade_data.get('take_profit') or trade_data.get('tp')
            
            if action.upper() == 'CLOSE':
                success, message = self.trader.close_position(symbol)
                return success, None, message
            else:
                success, ticket, message = self.trader.execute_trade(
                    symbol=symbol,
                    action=action,
                    volume=volume,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                return success, str(ticket) if ticket else None, message
                
        except Exception as e:
            error_msg = f"Trade execution error: {str(e)}"
            logging.error(error_msg)
            return False, None, error_msg
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get MT5 account info"""
        if not self.is_connected:
            return None
        
        try:
            return self.trader.get_account_info()
        except Exception as e:
            logging.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_positions(self) -> list:
        """Get MT5 positions"""
        if not self.is_connected:
            return []
        
        try:
            return self.trader.get_positions()
        except Exception as e:
            logging.error(f"Error getting positions: {str(e)}")
            return []

class BrokerManager:
    """Centralized broker management system like NextLevelBot"""
    
    def __init__(self):
        self.brokers = {
            'mt5': MT5Broker,
            'metatrader5': MT5Broker,
            'mt4': MT5Broker,  # Can use same implementation or create separate
        }
        self.active_broker = None
        self.active_broker_name = None
    
    def get_supported_brokers(self) -> list:
        """Get list of supported brokers"""
        return list(self.brokers.keys())
    
    def connect_broker(self, broker_name: str, credentials: Dict[str, str]) -> bool:
        """Connect to specified broker"""
        broker_name = broker_name.lower()
        
        if broker_name not in self.brokers:
            logging.error(f"Unsupported broker: {broker_name}")
            return False
        
        # Disconnect current broker if any
        if self.active_broker:
            self.active_broker.disconnect()
        
        # Create and connect new broker
        broker_class = self.brokers[broker_name]
        self.active_broker = broker_class()
        
        success = self.active_broker.connect(credentials)
        if success:
            self.active_broker_name = broker_name
            logging.info(f"Connected to broker: {broker_name}")
        else:
            self.active_broker = None
            self.active_broker_name = None
            logging.error(f"Failed to connect to broker: {broker_name}")
        
        return success
    
    def execute_trade(self, trade_data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Execute trade on active broker"""
        if not self.active_broker:
            return False, None, "No active broker connection"
        
        return self.active_broker.execute_trade(trade_data)
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account info from active broker"""
        if not self.active_broker:
            return None
        
        account_info = self.active_broker.get_account_info()
        if account_info:
            account_info['broker'] = self.active_broker_name
        
        return account_info
    
    def get_positions(self) -> list:
        """Get positions from active broker"""
        if not self.active_broker:
            return []
        
        return self.active_broker.get_positions()
    
    def disconnect(self) -> bool:
        """Disconnect from active broker"""
        if self.active_broker:
            success = self.active_broker.disconnect()
            self.active_broker = None
            self.active_broker_name = None
            return success
        return True

# Global broker manager instance
broker_manager = BrokerManager()

def get_broker_manager() -> BrokerManager:
    """Get global broker manager instance"""
    return broker_manager