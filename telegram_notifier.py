#!/usr/bin/env python3
"""
Telegram Notification System for AsterDex Auto Smart Trader
Sends alerts and updates to Telegram chat
"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class TelegramNotifier:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be provided")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, message, parse_mode="HTML", disable_notification=False):
        """Send message to Telegram"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Telegram API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return None
    
    def send_trading_action(self, action_data):
        """Send trading action notification"""
        action_type = action_data.get("type", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if action_type == "profit_take":
            emoji = "💰"
            title = "PROFIT TAKING"
            message = f"""
{emoji} <b>{title}</b>

🎯 <b>Rule:</b> {action_data.get('rule', 'N/A')}
📊 <b>Closed:</b> {action_data.get('percentage', 0):.1f}% ({action_data.get('quantity', 0):.2f} ASTER)
💵 <b>Realized Profit:</b> +{action_data.get('realized_profit', 0):.2f} USDT
📈 <b>Remaining PnL:</b> +{action_data.get('remaining_pnl', 0):.2f} USDT

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "stop_loss":
            emoji = "🚨"
            title = "STOP LOSS TRIGGERED"
            message = f"""
{emoji} <b>{title}</b>

🛑 <b>Reason:</b> {action_data.get('reason', 'N/A')}
📉 <b>Final PnL:</b> {action_data.get('pnl', 0):+.2f} USDT
🔴 Position fully closed

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "trailing_stop":
            emoji = "📉"
            title = "TRAILING STOP"
            message = f"""
{emoji} <b>{title}</b>

📊 <b>Reason:</b> {action_data.get('reason', 'N/A')}
💰 <b>Final PnL:</b> +{action_data.get('pnl', 0):.2f} USDT
✅ Position fully closed - Profit secured

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "funding_exit":
            emoji = "⚠️"
            title = "FUNDING EXIT"
            message = f"""
{emoji} <b>{title}</b>

📊 <b>Reason:</b> {action_data.get('reason', 'N/A')}
📈 <b>Funding Rate:</b> {action_data.get('rate', 0)*100:.3f}%
🔴 Position closed due to negative funding

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "margin_management":
            emoji = "⚠️"
            title = "MARGIN MANAGEMENT"
            message = f"""
{emoji} <b>{title}</b>

📊 <b>Reason:</b> {action_data.get('reason', 'N/A')}
📉 <b>Reduced:</b> {action_data.get('percentage', 0)}% of position
🛡️ Risk management action

⏰ <code>{timestamp}</code>
"""
        
        else:
            emoji = "ℹ️"
            title = "TRADING ACTION"
            message = f"""
{emoji} <b>{title}</b>

📊 <b>Type:</b> {action_type}
📝 <b>Details:</b> {json.dumps(action_data, indent=2)}

⏰ <code>{timestamp}</code>
"""
        
        return self.send_message(message)
    
    def send_position_update(self, position_data, account_data=None):
        """Send position status update"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        side = position_data.get("side", "UNKNOWN")
        size = abs(position_data.get("size", 0))
        entry_price = position_data.get("entry_price", 0)
        mark_price = position_data.get("mark_price", 0)
        pnl = position_data.get("pnl", 0)
        
        pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💛"
        
        message = f"""
📊 <b>POSITION UPDATE</b>

{pnl_emoji} <b>PnL:</b> {pnl:+.2f} USDT
📈 <b>Position:</b> {side} {size:.2f} ASTER
💵 <b>Entry:</b> {entry_price:.4f} USDT
📊 <b>Mark:</b> {mark_price:.4f} USDT
"""
        
        if account_data:
            balance = account_data.get("total_balance", 0)
            margin_ratio = account_data.get("margin_ratio", 0) * 100
            
            message += f"""
💰 <b>Balance:</b> {balance:.2f} USDT
⚖️ <b>Margin:</b> {margin_ratio:.1f}%
"""
        
        message += f"\n⏰ <code>{timestamp}</code>"
        
        return self.send_message(message, disable_notification=True)
    
    def send_funding_alert(self, funding_data, position_data=None):
        """Send funding rate alert"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        rate = funding_data.get("rate", 0)
        next_time = funding_data.get("next_time", "Unknown")
        
        if isinstance(next_time, datetime):
            next_time_str = next_time.strftime("%H:%M:%S UTC")
        else:
            next_time_str = str(next_time)
        
        daily_rate = rate * 3 * 100  # 3 times per day, as percentage
        
        if rate >= 0.005:  # 0.5%
            emoji = "🎯"
            status = "EXCELLENT"
        elif rate >= 0.001:  # 0.1%
            emoji = "✅"
            status = "GOOD"
        elif rate >= 0:
            emoji = "💛"
            status = "NEUTRAL"
        elif rate >= -0.002:  # -0.2%
            emoji = "⚠️"
            status = "WARNING"
        else:
            emoji = "🚨"
            status = "DANGER"
        
        message = f"""
{emoji} <b>FUNDING RATE - {status}</b>

💎 <b>Rate (8h):</b> {rate*100:.3f}%
📈 <b>Daily Rate:</b> {daily_rate:.2f}%
⏰ <b>Next Funding:</b> {next_time_str}
"""
        
        if position_data:
            size = abs(position_data.get("size", 0))
            mark_price = position_data.get("mark_price", 0)
            position_value = size * mark_price
            funding_income = position_value * rate
            
            message += f"""
💰 <b>Expected Income:</b> {funding_income:+.2f} USDT
📊 <b>Position Value:</b> {position_value:.2f} USDT
"""
        
        message += f"\n⏰ <code>{timestamp}</code>"
        
        # Send with notification only for warnings/dangers
        notify = rate <= -0.001
        return self.send_message(message, disable_notification=not notify)
    
    def send_startup_message(self):
        """Send startup notification"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
🤖 <b>AUTO SMART TRADER STARTED</b>

✅ System initialized successfully
🎯 Monitoring position and executing rules
📊 Hybrid strategy active

⏰ <code>{timestamp}</code>
"""
        
        return self.send_message(message)
    
    def send_shutdown_message(self, reason="Manual stop"):
        """Send shutdown notification"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
🛑 <b>AUTO SMART TRADER STOPPED</b>

📝 <b>Reason:</b> {reason}
⏰ <code>{timestamp}</code>

Check your positions manually if needed.
"""
        
        return self.send_message(message)
    
    def send_error_alert(self, error_message, context=""):
        """Send error alert"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
🚨 <b>ERROR ALERT</b>

❌ <b>Error:</b> {error_message}
"""
        
        if context:
            message += f"📝 <b>Context:</b> {context}\n"
        
        message += f"\n⏰ <code>{timestamp}</code>"
        
        return self.send_message(message)
    
    def test_connection(self):
        """Test Telegram connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                bot_name = bot_info.get("result", {}).get("first_name", "Unknown")
                print(f"✅ Connected to Telegram bot: {bot_name}")
                
                # Send test message
                test_msg = "🧪 <b>TEST MESSAGE</b>\n\nTelegram notifications are working correctly!"
                result = self.send_message(test_msg)
                
                if result:
                    print("✅ Test message sent successfully")
                    return True
                else:
                    print("❌ Failed to send test message")
                    return False
            else:
                print(f"❌ Bot connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

def setup_telegram():
    """Interactive setup for Telegram notifications"""
    print("🤖 Telegram Notification Setup")
    print("=" * 50)
    print()
    
    print("📝 You need to:")
    print("1. Create a Telegram bot with @BotFather")
    print("2. Get your chat ID from @userinfobot")
    print("3. Add the credentials to your .env file")
    print()
    
    bot_token = input("🤖 Enter your Telegram Bot Token: ").strip()
    if not bot_token:
        print("❌ Bot token is required!")
        return False
    
    chat_id = input("💬 Enter your Chat ID: ").strip()
    if not chat_id:
        print("❌ Chat ID is required!")
        return False
    
    # Test connection
    print("\n🧪 Testing connection...")
    try:
        notifier = TelegramNotifier(bot_token, chat_id)
        if notifier.test_connection():
            # Add to .env file
            env_content = f"\n# Telegram Notifications\nTELEGRAM_BOT_TOKEN={bot_token}\nTELEGRAM_CHAT_ID={chat_id}\n"
            
            with open(".env", "a") as f:
                f.write(env_content)
            
            print("✅ Telegram notifications configured successfully!")
            print("📝 Credentials saved to .env file")
            return True
        else:
            print("❌ Connection test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def main():
    """Main function for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Notifier for Auto Smart Trader")
    parser.add_argument("--setup", action="store_true", help="Setup Telegram notifications")
    parser.add_argument("--test", action="store_true", help="Test Telegram connection")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_telegram()
        return
    
    if args.test:
        try:
            notifier = TelegramNotifier()
            notifier.test_connection()
        except Exception as e:
            print(f"❌ Error: {e}")
        return
    
    print("Use --setup to configure or --test to test connection")

if __name__ == "__main__":
    main()
