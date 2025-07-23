#!/usr/bin/env python3
"""
NextLevelBot-inspired enhancements for MT5 Trading Bridge
Based on analysis of https://nextlevelbot.com/
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class EnhancedWebhookProcessor:
    """Enhanced webhook processor inspired by NextLevelBot architecture"""
    
    def __init__(self):
        self.supported_actions = ['BUY', 'SELL', 'CLOSE', 'MODIFY']
        self.supported_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
        
    def validate_request(self, data: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """Enhanced request validation like NextLevelBot"""
        
        # Check required fields
        required_fields = ['symbol', 'action']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate action
        if data['action'].upper() not in self.supported_actions:
            return False, f"Unsupported action: {data['action']}. Supported: {', '.join(self.supported_actions)}"
        
        # Validate symbol format
        symbol = data['symbol'].upper()
        if len(symbol) < 6 or len(symbol) > 8:
            return False, f"Invalid symbol format: {symbol}"
        
        # Check volume if provided
        if 'volume' in data:
            try:
                volume = float(data['volume'])
                if volume <= 0 or volume > 100:
                    return False, f"Invalid volume: {volume}. Must be between 0.01 and 100"
            except (ValueError, TypeError):
                return False, f"Invalid volume format: {data['volume']}"
        
        return True, "Validation passed"
    
    def format_response(self, success: bool, message: str, 
                       ticket: Optional[str] = None, 
                       additional_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Format response in NextLevelBot style"""
        
        response = {
            'status': 'success' if success else 'error',
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'bridge': 'MT5-TradingView',
            'version': '1.0'
        }
        
        if success and ticket:
            response.update({
                'trade_id': str(ticket),
                'ticket': str(ticket),
                'broker': 'MetaTrader5'
            })
        
        if additional_data:
            response.update(additional_data)
        
        return response

class TelegramNotifier:
    """Telegram notification system like NextLevelBot"""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
    
    def send_trade_notification(self, trade_data: Dict[str, Any], success: bool):
        """Send trade notification to Telegram"""
        if not self.enabled:
            return
        
        status_emoji = "✅" if success else "❌"
        action_emoji = {"BUY": "📈", "SELL": "📉", "CLOSE": "🔄"}.get(trade_data.get('action', ''), '📊')
        
        message = f"""
{status_emoji} **MT5 Trade Alert**

{action_emoji} **Action**: {trade_data.get('action', 'N/A')}
💱 **Symbol**: {trade_data.get('symbol', 'N/A')}
📊 **Volume**: {trade_data.get('volume', 'Default')}
💰 **Price**: {trade_data.get('price', 'Market')}

🎯 **Status**: {'Success' if success else 'Failed'}
⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # In real implementation, would send via Telegram API
        logging.info(f"Telegram notification: {message}")

class AdvancedRiskManager:
    """Advanced risk management inspired by NextLevelBot"""
    
    def __init__(self):
        self.max_daily_volume = 10.0  # Maximum daily volume
        self.max_position_size = 2.0  # Maximum single position
        self.allowed_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
        
    def check_risk_limits(self, trade_data: Dict[str, Any], daily_stats: Dict[str, Any]) -> tuple:
        """Enhanced risk checking"""
        
        symbol = trade_data.get('symbol', '').upper()
        volume = float(trade_data.get('volume', 0.01))
        action = trade_data.get('action', '').upper()
        
        # Check symbol whitelist
        if symbol not in self.allowed_symbols:
            return False, f"Symbol {symbol} not in allowed list: {', '.join(self.allowed_symbols)}"
        
        # Check daily volume limit
        daily_volume = daily_stats.get('total_volume', 0)
        if daily_volume + volume > self.max_daily_volume:
            return False, f"Daily volume limit exceeded: {daily_volume + volume:.2f} > {self.max_daily_volume}"
        
        # Check position size
        if volume > self.max_position_size:
            return False, f"Position size too large: {volume} > {self.max_position_size}"
        
        # Check for CLOSE action (always allow)
        if action == 'CLOSE':
            return True, "Close action approved"
        
        return True, "Risk checks passed"

def create_nlb_style_webhook_response(success: bool, message: str, trade_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create NextLevelBot style webhook response"""
    
    processor = EnhancedWebhookProcessor()
    ticket = trade_data.get('ticket') if trade_data else None
    
    additional_data = {}
    if trade_data:
        additional_data = {
            'symbol': trade_data.get('symbol'),
            'action': trade_data.get('action'),
            'volume': trade_data.get('volume'),
            'price': trade_data.get('price')
        }
    
    return processor.format_response(success, message, ticket, additional_data)

if __name__ == "__main__":
    # Test the enhanced processor
    processor = EnhancedWebhookProcessor()
    
    test_data = {
        'symbol': 'EURUSD',
        'action': 'BUY',
        'volume': 0.1,
        'price': 1.1234
    }
    
    is_valid, msg = processor.validate_request(test_data, {})
    print(f"Validation: {is_valid} - {msg}")
    
    response = processor.format_response(True, "Trade executed", "123456", test_data)
    print(f"Response: {json.dumps(response, indent=2)}")