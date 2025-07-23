import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import random
import time

# Mock MT5 constants for demo purposes
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_TIME_GTC = 0
ORDER_FILLING_IOC = 1
TRADE_RETCODE_DONE = 10009

class MockMT5Result:
    def __init__(self, retcode=TRADE_RETCODE_DONE, order=None, comment="Success"):
        self.retcode = retcode
        self.order = order or random.randint(100000, 999999)
        self.comment = comment

class MockAccountInfo:
    def __init__(self, login=None, server=None):
        # Use real account info when provided, otherwise use demo defaults
        if login and login != "demo":
            # Use your real account credentials when provided
            self.login = int(login) if str(login).isdigit() else 12345678
            self.server = server if server else "18.61.99.175:443"
            # Note: In production MT5 environment, these would come from actual MT5 account
            # For demo showing your real account number but simulated balance
            self.balance = 25000.00  # Replace with your actual balance
            self.equity = 25150.75   # Replace with your actual equity
            self.margin = 125.00
            self.margin_free = 25025.75
            self.margin_level = 20020.60
            self.currency = "USD"
        else:
            # Demo/fallback account
            self.login = 12345678
            self.server = "Demo-Server"
            self.balance = 10000.00
            self.equity = 10025.50
            self.margin = 50.00
            self.margin_free = 9975.50
            self.margin_level = 20051.00
            self.currency = "USD"

class MockSymbolInfo:
    def __init__(self, symbol="EURUSD"):
        self.name = symbol
        self.bid = 1.1000 + random.uniform(-0.0050, 0.0050)
        self.ask = self.bid + 0.0003
        self.spread = 3
        self.digits = 5
        self.point = 0.00001
        self.trade_mode = 4
        self.volume_min = 0.01
        self.volume_max = 100.0
        self.volume_step = 0.01

class MockPosition:
    def __init__(self, symbol="EURUSD", position_type=ORDER_TYPE_BUY):
        self.ticket = random.randint(100000, 999999)
        self.symbol = symbol
        self.type = position_type
        self.volume = 0.1
        self.price_open = 1.1000 + random.uniform(-0.0050, 0.0050)
        self.price_current = self.price_open + random.uniform(-0.0020, 0.0020)
        self.profit = (self.price_current - self.price_open) * 100000 * self.volume if position_type == ORDER_TYPE_BUY else (self.price_open - self.price_current) * 100000 * self.volume
        self.swap = 0.0
        self.commission = -0.5
        self.time = int(time.time())

# Mock MT5 functions
def initialize():
    """Mock MT5 initialize function"""
    print("Mock MT5: Initialize called (success)")
    return True

def mock_login(login, password, server):
    """Mock MT5 login function"""
    print(f"Mock MT5: Login called for {login} on {server}")
    return True

def shutdown():
    """Mock MT5 shutdown function"""
    print("Mock MT5: Shutdown called")
    return True

def account_info(login=None, server=None):
    """Mock MT5 account_info function"""
    return MockAccountInfo(login, server)

def symbol_info(symbol):
    """Mock MT5 symbol_info function"""
    return MockSymbolInfo(symbol)

def symbol_info_tick(symbol):
    """Mock MT5 symbol_info_tick function"""
    return MockSymbolInfo(symbol)

def order_send(request):
    """Mock MT5 order_send function"""
    print(f"Mock MT5: Order sent - {request}")
    return MockMT5Result()

def positions_get(symbol=None):
    """Mock MT5 positions_get function"""
    if symbol:
        return [MockPosition(symbol)] if random.choice([True, False]) else []
    return [MockPosition("EURUSD"), MockPosition("GBPUSD", ORDER_TYPE_SELL)] if random.choice([True, False]) else []

def symbols_get():
    """Mock MT5 symbols_get function"""
    common_symbols = [
        MockSymbolInfo("EURUSD"),
        MockSymbolInfo("GBPUSD"),
        MockSymbolInfo("USDJPY"),
        MockSymbolInfo("USDCHF"),
        MockSymbolInfo("AUDUSD"),
        MockSymbolInfo("USDCAD"),
        MockSymbolInfo("NZDUSD"),
        MockSymbolInfo("EURGBP"),
        MockSymbolInfo("EURJPY"),
        MockSymbolInfo("GBPJPY"),
        MockSymbolInfo("XAUUSD"),  # Gold
        MockSymbolInfo("XAGUSD"),  # Silver
        MockSymbolInfo("USOIL"),   # Oil
        MockSymbolInfo("US30"),    # Dow Jones
        MockSymbolInfo("BTCUSD"),  # Bitcoin
    ]
    
    # Add some extra attributes for symbols
    for symbol in common_symbols:
        symbol.description = f"{symbol.name} Description"
        symbol.path = f"Forex\\Major\\{symbol.name}"
        symbol.currency_base = symbol.name[:3]
        symbol.currency_profit = symbol.name[3:]
        symbol.currency_margin = symbol.name[3:]
        symbol.visible = True
        
    return common_symbols

def last_error():
    """Mock MT5 last_error function"""
    return (0, "Success")

# Create mock mt5 module
class MockMT5:
    ORDER_TYPE_BUY = ORDER_TYPE_BUY
    ORDER_TYPE_SELL = ORDER_TYPE_SELL
    TRADE_ACTION_DEAL = TRADE_ACTION_DEAL
    ORDER_TIME_GTC = ORDER_TIME_GTC
    ORDER_FILLING_IOC = ORDER_FILLING_IOC
    TRADE_RETCODE_DONE = TRADE_RETCODE_DONE
    
    @staticmethod
    def initialize():
        return initialize()
    
    @staticmethod
    def login(login, password, server):
        return mock_login(login, password, server)
    
    @staticmethod
    def shutdown():
        return shutdown()
    
    @staticmethod
    def account_info(login=None, server=None):
        return account_info(login, server)
    
    @staticmethod
    def symbol_info(symbol):
        return symbol_info(symbol)
    
    @staticmethod
    def last_error():
        return last_error()
    
    @staticmethod
    def symbol_info_tick(symbol):
        return symbol_info_tick(symbol)
    
    @staticmethod
    def order_send(request):
        return order_send(request)
    
    @staticmethod
    def positions_get(symbol=None):
        return positions_get(symbol)
    
    @staticmethod
    def symbols_get():
        return symbols_get()

# Use mock MT5 for demo purposes
mt5 = MockMT5()

logger = logging.getLogger(__name__)

class MT5Trader:
    def __init__(self):
        self.is_connected = False
        self.account_info = None
        self.current_login = None
        self.current_server = None
        
    def connect(self, server: str, login: str, password: str) -> bool:
        """Connect to MT5 terminal"""
        try:
            # Validate credentials
            if not server or not login or not password:
                logger.warning("Missing MT5 credentials - using demo mode")
                # For demo purposes, simulate successful connection
                self.is_connected = True
                self.current_login = "demo"
                self.current_server = "demo-server"
                self.account_info = mt5.account_info("demo", "demo-server")
                logger.info("Connected to MT5 demo mode")
                return True
            
            # Initialize MT5 connection
            if not mt5.initialize():
                logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                return False
            
            # Login to account
            try:
                login_num = int(login)
            except ValueError:
                logger.error(f"Invalid login format: {login}")
                return False
                
            if not mt5.login(login=login_num, password=password, server=server):
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
            
            self.is_connected = True
            self.current_login = login
            self.current_server = server
            self.account_info = mt5.account_info(login, server)
            logger.info(f"Connected to MT5 account: {login}")
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            logger.info("Disconnected from MT5")
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        if not self.is_connected:
            return None
            
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Symbol {symbol} not found")
                return None
                
            return {
                'symbol': symbol_info.name,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'spread': symbol_info.spread,
                'digits': symbol_info.digits,
                'point': symbol_info.point,
                'trade_mode': symbol_info.trade_mode,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step
            }
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return None
    
    def execute_trade(self, symbol: str, action: str, volume: float, 
                     price: Optional[float] = None, stop_loss: Optional[float] = None, 
                     take_profit: Optional[float] = None, slippage: int = 3) -> Tuple[bool, Optional[int], str]:
        """Execute a trade"""
        if not self.is_connected:
            return False, None, "Not connected to MT5"
        
        try:
            # Get symbol info
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return False, None, f"Symbol {symbol} not available"
            
            # Determine order type
            if action.upper() == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                execution_price = symbol_info['ask'] if price is None else price
            elif action.upper() == "SELL":
                order_type = mt5.ORDER_TYPE_SELL
                execution_price = symbol_info['bid'] if price is None else price
            else:
                return False, None, f"Invalid action: {action}"
            
            # Validate volume
            if volume < symbol_info['volume_min']:
                volume = symbol_info['volume_min']
            elif volume > symbol_info['volume_max']:
                volume = symbol_info['volume_max']
            
            # Round volume to step
            volume_step = symbol_info['volume_step']
            volume = round(volume / volume_step) * volume_step
            
            # Prepare trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": execution_price,
                "slippage": slippage,
                "magic": 234000,
                "comment": "TradingView Webhook",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send trade request
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Trade failed: {result.retcode} - {result.comment}"
                logger.error(error_msg)
                return False, None, error_msg
            
            logger.info(f"Trade executed successfully: {result.order} for {symbol}")
            return True, result.order, "Trade executed successfully"
            
        except Exception as e:
            error_msg = f"Trade execution error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def close_position(self, symbol: str, volume: Optional[float] = None) -> Tuple[bool, str]:
        """Close position for a symbol"""
        if not self.is_connected:
            return False, "Not connected to MT5"
        
        try:
            # Get current positions
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                return False, f"No open positions for {symbol}"
            
            success_count = 0
            errors = []
            
            for position in positions:
                # Determine close action (opposite of position type)
                if position.type == mt5.ORDER_TYPE_BUY:
                    close_type = mt5.ORDER_TYPE_SELL
                    close_price = mt5.symbol_info_tick(symbol).bid
                else:
                    close_type = mt5.ORDER_TYPE_BUY
                    close_price = mt5.symbol_info_tick(symbol).ask
                
                # Use specified volume or position volume
                close_volume = volume if volume else position.volume
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": close_volume,
                    "type": close_type,
                    "position": position.ticket,
                    "price": close_price,
                    "magic": 234000,
                    "comment": "TradingView Close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    success_count += 1
                    logger.info(f"Position {position.ticket} closed successfully")
                else:
                    error_msg = f"Failed to close position {position.ticket}: {result.comment}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if success_count > 0:
                return True, f"Closed {success_count} positions"
            else:
                return False, "; ".join(errors)
                
        except Exception as e:
            error_msg = f"Error closing positions: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        if not self.is_connected:
            return None
        
        try:
            account = mt5.account_info()
            if account:
                return {
                    'login': account.login,
                    'server': account.server,
                    'balance': account.balance,
                    'equity': account.equity,
                    'margin': account.margin,
                    'free_margin': account.margin_free,
                    'margin_level': account.margin_level,
                    'currency': account.currency
                }
            return None
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_positions(self, symbol: Optional[str] = None) -> list:
        """Get current positions"""
        if not self.is_connected:
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if not positions:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'commission': pos.commission,
                    'time': datetime.fromtimestamp(pos.time)
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def get_symbols(self, limit=50):
        """Get available MT5 symbols"""
        if not self.is_connected:
            return []
        
        try:
            # Get all symbols
            symbols = mt5.symbols_get()
            if symbols is None:
                return []
            
            symbol_list = []
            for symbol in symbols[:limit]:  # Limit to avoid too many symbols
                try:
                    symbol_list.append({
                        'name': symbol.name,
                        'description': getattr(symbol, 'description', f"{symbol.name} Description"),
                        'path': getattr(symbol, 'path', f"Forex\\{symbol.name}"),
                        'currency_base': getattr(symbol, 'currency_base', symbol.name[:3] if len(symbol.name) >= 6 else 'USD'),
                        'currency_profit': getattr(symbol, 'currency_profit', symbol.name[3:] if len(symbol.name) >= 6 else 'USD'),
                        'digits': symbol.digits,
                        'point': symbol.point,
                        'bid': symbol.bid,
                        'ask': symbol.ask,
                        'spread': symbol.spread,
                        'visible': getattr(symbol, 'visible', True)
                    })
                except Exception as e:
                    logger.warning(f"Error processing symbol {symbol.name}: {e}")
                    continue
            
            return symbol_list
            
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []
    
    def get_symbol_detail(self, symbol_name):
        """Get detailed information for a specific symbol"""
        if not self.is_connected:
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol_name)
            if symbol_info is None:
                return None
            
            # Get current tick data
            tick = mt5.symbol_info_tick(symbol_name)
            
            return {
                'name': symbol_info.name,
                'description': getattr(symbol_info, 'description', f"{symbol_info.name} Description"),
                'path': getattr(symbol_info, 'path', f"Forex\\{symbol_info.name}"),
                'currency_base': getattr(symbol_info, 'currency_base', symbol_info.name[:3] if len(symbol_info.name) >= 6 else 'USD'),
                'currency_profit': getattr(symbol_info, 'currency_profit', symbol_info.name[3:] if len(symbol_info.name) >= 6 else 'USD'),
                'digits': symbol_info.digits,
                'point': symbol_info.point,
                'spread': symbol_info.spread,
                'visible': getattr(symbol_info, 'visible', True),
                'bid': tick.bid if tick else symbol_info.bid,
                'ask': tick.ask if tick else symbol_info.ask,
                'time': tick.time if tick else 0,
                'volume_min': getattr(symbol_info, 'volume_min', 0.01),
                'volume_max': getattr(symbol_info, 'volume_max', 100.0),
                'volume_step': getattr(symbol_info, 'volume_step', 0.01)
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol detail for {symbol_name}: {e}")
            return None
