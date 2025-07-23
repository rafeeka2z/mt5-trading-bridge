#!/usr/bin/env python3
"""
Real-time webhook monitor to track TradingView alerts
"""

import time
import requests
from datetime import datetime, timedelta

def monitor_webhooks():
    """Monitor webhook alerts in real-time"""
    print("TradingView Webhook Monitor")
    print("=" * 40)
    print("Monitoring for new webhook alerts...")
    print("Press Ctrl+C to stop")
    print()
    
    last_check = datetime.now() - timedelta(minutes=1)
    
    while True:
        try:
            # Check for new alerts since last check
            response = requests.get('http://localhost:5000/api/stats?hours=1')
            if response.status_code == 200:
                data = response.json()
                current_time = datetime.now()
                
                print(f"[{current_time.strftime('%H:%M:%S')}] Status Check:")
                print(f"  - Total Alerts: {data.get('alerts_count', 0)}")
                print(f"  - Total Trades: {data.get('trades_count', 0)}")
                print(f"  - Successful: {data.get('successful_trades', 0)}")
                print(f"  - Failed: {data.get('failed_trades', 0)}")
                print()
                
                last_check = current_time
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: Could not connect to webhook API")
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {str(e)}")
        
        # Wait 10 seconds before next check
        time.sleep(10)

if __name__ == "__main__":
    monitor_webhooks()