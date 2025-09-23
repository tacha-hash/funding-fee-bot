#!/usr/bin/env python3
"""
Telegram Notification System (Thai Version) for AsterDex Auto Smart Trader
แจ้งเตือนภาษาไทย และแจ้งเฉพาะเมื่อมีการเปลี่ยนแปลงสำคัญ
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

class TelegramNotifierThai:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID ต้องตั้งค่าใน environment variables")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # เก็บสถานะล่าสุดเพื่อเปรียบเทียบการเปลี่ยนแปลง
        self.last_state = {
            "pnl": None,
            "position_size": None,
            "funding_rate": None,
            "balance": None,
            "margin_ratio": None,
            "last_action_time": 0,
            "last_funding_alert_time": 0,
            "last_position_alert_time": 0
        }
        
        # เกณฑ์การแจ้งเตือน
        self.alert_thresholds = {
            "pnl_change_threshold": 5.0,        # แจ้งเมื่อ PnL เปลี่ยน ±5 USDT
            "position_change_threshold": 0.1,    # แจ้งเมื่อ Position เปลี่ยน 10%
            "funding_change_threshold": 0.001,   # แจ้งเมื่อ Funding Rate เปลี่ยน 0.1%
            "balance_change_threshold": 50.0,    # แจ้งเมื่อ Balance เปลี่ยน ±50 USDT
            "margin_change_threshold": 0.05,     # แจ้งเมื่อ Margin เปลี่ยน 5%
            "min_alert_interval": 300,           # ห้ามแจ้งเตือนเร็วกว่า 5 นาที
            "funding_alert_interval": 1800,      # Funding alert ทุก 30 นาที
            "position_alert_interval": 900       # Position alert ทุก 15 นาที
        }
        
    def send_message(self, message, parse_mode="HTML", disable_notification=False):
        """ส่งข้อความไป Telegram"""
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
            print(f"❌ ไม่สามารถส่งข้อความ Telegram: {e}")
            return None
    
    def should_alert_change(self, alert_type, current_time=None):
        """ตรวจสอบว่าควรแจ้งเตือนหรือไม่ตามเวลา"""
        if current_time is None:
            current_time = time.time()
        
        if alert_type == "action":
            return current_time - self.last_state["last_action_time"] >= self.alert_thresholds["min_alert_interval"]
        elif alert_type == "funding":
            return current_time - self.last_state["last_funding_alert_time"] >= self.alert_thresholds["funding_alert_interval"]
        elif alert_type == "position":
            return current_time - self.last_state["last_position_alert_time"] >= self.alert_thresholds["position_alert_interval"]
        
        return True
    
    def format_number(self, number, decimals=2):
        """จัดรูปแบบตัวเลขให้อ่านง่าย"""
        if abs(number) >= 1000000:
            return f"{number/1000000:.1f}M"
        elif abs(number) >= 1000:
            return f"{number/1000:.1f}K"
        else:
            return f"{number:.{decimals}f}"
    
    def send_trading_action(self, action_data):
        """แจ้งเตือนการกระทำทางการเทรด (แจ้งทุกครั้ง)"""
        action_type = action_data.get("type", "unknown")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        if action_type == "profit_take":
            emoji = "💰"
            title = "เก็บกำไร"
            percentage = action_data.get('percentage', 0)
            quantity = action_data.get('quantity', 0)
            profit = action_data.get('realized_profit', 0)
            remaining_pnl = action_data.get('remaining_pnl', 0)
            
            message = f"""
{emoji} <b>{title} - สำเร็จ!</b>

🎯 <b>กฎที่ใช้:</b> {action_data.get('rule', 'ไม่ระบุ')}
📊 <b>ปิด Position:</b> {percentage:.1f}% ({self.format_number(quantity)} ASTER)
💵 <b>กำไรที่ได้:</b> +{self.format_number(profit)} USDT
📈 <b>PnL คงเหลือ:</b> +{self.format_number(remaining_pnl)} USDT

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "stop_loss":
            emoji = "🚨"
            title = "Stop Loss"
            pnl = action_data.get('pnl', 0)
            
            message = f"""
{emoji} <b>{title} - ถูกเรียกใช้!</b>

🛑 <b>เหตุผล:</b> {action_data.get('reason', 'ไม่ระบุ')}
📉 <b>PnL สุดท้าย:</b> {pnl:+.2f} USDT
🔴 <b>สถานะ:</b> ปิด Position ทั้งหมดแล้ว

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "trailing_stop":
            emoji = "📉"
            title = "Trailing Stop"
            pnl = action_data.get('pnl', 0)
            
            message = f"""
{emoji} <b>{title} - ถูกเรียกใช้!</b>

📊 <b>เหตุผล:</b> {action_data.get('reason', 'ไม่ระบุ')}
💰 <b>PnL สุดท้าย:</b> +{self.format_number(pnl)} USDT
✅ <b>สถานะ:</b> ปิด Position แล้ว - รักษากำไรไว้ได้

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "funding_exit":
            emoji = "⚠️"
            title = "ปิด Position เนื่องจาก Funding"
            rate = action_data.get('rate', 0) * 100
            
            message = f"""
{emoji} <b>{title}</b>

📊 <b>เหตุผล:</b> {action_data.get('reason', 'ไม่ระบุ')}
📈 <b>Funding Rate:</b> {rate:.3f}%
🔴 <b>สถานะ:</b> ปิด Position เนื่องจาก Funding ติดลบมาก

⏰ <code>{timestamp}</code>
"""
        
        elif action_type == "margin_management":
            emoji = "⚠️"
            title = "จัดการ Margin"
            percentage = action_data.get('percentage', 0)
            
            message = f"""
{emoji} <b>{title}</b>

📊 <b>เหตุผล:</b> {action_data.get('reason', 'ไม่ระบุ')}
📉 <b>ลดขนาด Position:</b> {percentage}%
🛡️ <b>วัตถุประสงค์:</b> จัดการความเสี่ยง

⏰ <code>{timestamp}</code>
"""
        
        else:
            emoji = "ℹ️"
            title = "การกระทำทางการเทรด"
            message = f"""
{emoji} <b>{title}</b>

📊 <b>ประเภท:</b> {action_type}
📝 <b>รายละเอียด:</b> {action_data.get('reason', 'ไม่ระบุ')}

⏰ <code>{timestamp}</code>
"""
        
        # บันทึกเวลาการแจ้งเตือน
        self.last_state["last_action_time"] = time.time()
        
        return self.send_message(message)
    
    def send_position_update(self, position_data, account_data=None):
        """แจ้งเตือน Position Update (เฉพาะเมื่อมีการเปลี่ยนแปลงสำคัญ)"""
        current_time = time.time()
        
        if not self.should_alert_change("position", current_time):
            return None
        
        current_pnl = position_data.get("pnl", 0)
        current_size = abs(position_data.get("size", 0))
        current_balance = account_data.get("total_balance", 0) if account_data else 0
        current_margin = account_data.get("margin_ratio", 0) if account_data else 0
        
        # ตรวจสอบการเปลี่ยนแปลงสำคัญ
        should_alert = False
        changes = []
        
        # เปลี่ยนแปลง PnL
        if self.last_state["pnl"] is not None:
            pnl_change = abs(current_pnl - self.last_state["pnl"])
            if pnl_change >= self.alert_thresholds["pnl_change_threshold"]:
                should_alert = True
                direction = "เพิ่มขึ้น" if current_pnl > self.last_state["pnl"] else "ลดลง"
                changes.append(f"PnL {direction} {self.format_number(pnl_change)} USDT")
        
        # เปลี่ยนแปลง Position Size
        if self.last_state["position_size"] is not None:
            if self.last_state["position_size"] > 0:
                size_change_pct = abs(current_size - self.last_state["position_size"]) / self.last_state["position_size"]
                if size_change_pct >= self.alert_thresholds["position_change_threshold"]:
                    should_alert = True
                    direction = "เพิ่มขึ้น" if current_size > self.last_state["position_size"] else "ลดลง"
                    changes.append(f"ขนาด Position {direction} {size_change_pct*100:.1f}%")
        
        # เปลี่ยนแปลง Balance
        if self.last_state["balance"] is not None:
            balance_change = abs(current_balance - self.last_state["balance"])
            if balance_change >= self.alert_thresholds["balance_change_threshold"]:
                should_alert = True
                direction = "เพิ่มขึ้น" if current_balance > self.last_state["balance"] else "ลดลง"
                changes.append(f"Balance {direction} {self.format_number(balance_change)} USDT")
        
        # บันทึกสถานะปัจจุบัน
        self.last_state.update({
            "pnl": current_pnl,
            "position_size": current_size,
            "balance": current_balance,
            "margin_ratio": current_margin
        })
        
        if not should_alert:
            return None
        
        # ส่งข้อความแจ้งเตือน
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        side = position_data.get("side", "UNKNOWN")
        size = abs(position_data.get("size", 0))
        entry_price = position_data.get("entry_price", 0)
        mark_price = position_data.get("mark_price", 0)
        
        pnl_emoji = "💚" if current_pnl > 0 else "❤️" if current_pnl < 0 else "💛"
        side_thai = "ขาย (Short)" if side == "SHORT" else "ซื้อ (Long)"
        
        message = f"""
📊 <b>อัพเดท Position - มีการเปลี่ยนแปลง</b>

{pnl_emoji} <b>PnL:</b> {current_pnl:+.2f} USDT
📈 <b>Position:</b> {side_thai} {self.format_number(size)} ASTER
💵 <b>ราคาเข้า:</b> {entry_price:.4f} USDT
📊 <b>ราคาปัจจุบัน:</b> {mark_price:.4f} USDT
"""
        
        if account_data:
            message += f"""
💰 <b>Balance:</b> {self.format_number(current_balance)} USDT
⚖️ <b>Margin:</b> {current_margin*100:.1f}%
"""
        
        if changes:
            message += f"\n🔄 <b>การเปลี่ยนแปลง:</b> {', '.join(changes)}"
        
        message += f"\n⏰ <code>{timestamp}</code>"
        
        # บันทึกเวลาการแจ้งเตือน
        self.last_state["last_position_alert_time"] = current_time
        
        return self.send_message(message, disable_notification=True)
    
    def send_funding_alert(self, funding_data, position_data=None):
        """แจ้งเตือน Funding Rate (เฉพาะเมื่อมีการเปลี่ยนแปลงสำคัญ)"""
        current_time = time.time()
        
        if not self.should_alert_change("funding", current_time):
            return None
        
        current_rate = funding_data.get("rate", 0)
        
        # ตรวจสอบการเปลี่ยนแปลง Funding Rate
        should_alert = False
        rate_change = 0
        
        if self.last_state["funding_rate"] is not None:
            rate_change = abs(current_rate - self.last_state["funding_rate"])
            if rate_change >= self.alert_thresholds["funding_change_threshold"]:
                should_alert = True
        else:
            should_alert = True  # แจ้งครั้งแรก
        
        # บันทึกสถานะปัจจุบัน
        self.last_state["funding_rate"] = current_rate
        
        # แจ้งเตือนถ้า Rate เป็นลบมาก หรือเปลี่ยนแปลงมาก
        if current_rate <= -0.002 or should_alert:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            next_time = funding_data.get("next_time", "ไม่ทราบ")
            
            if isinstance(next_time, datetime):
                next_time_str = next_time.strftime("%H:%M:%S UTC")
            else:
                next_time_str = str(next_time)
            
            daily_rate = current_rate * 3 * 100  # 3 ครั้งต่อวัน เป็นเปอร์เซ็นต์
            
            # กำหนดสถานะและ emoji
            if current_rate >= 0.005:  # 0.5%
                emoji = "🎯"
                status = "ดีเยี่ยม"
                color = "สำหรับ Short"
            elif current_rate >= 0.001:  # 0.1%
                emoji = "✅"
                status = "ดี"
                color = "สำหรับ Short"
            elif current_rate >= 0:
                emoji = "💛"
                status = "ปกติ"
                color = ""
            elif current_rate >= -0.002:  # -0.2%
                emoji = "⚠️"
                status = "เตือน"
                color = "ไม่ดีสำหรับ Short"
            else:
                emoji = "🚨"
                status = "อันตราย"
                color = "แย่มากสำหรับ Short"
            
            message = f"""
{emoji} <b>Funding Rate - {status}</b>

💎 <b>อัตรา (8 ชม.):</b> {current_rate*100:.3f}%
📈 <b>อัตรารายวัน:</b> {daily_rate:.2f}%
⏰ <b>Funding ครั้งถัดไป:</b> {next_time_str}
"""
            
            if color:
                message += f"📊 <b>สถานะ:</b> {color}\n"
            
            if rate_change > 0:
                message += f"🔄 <b>เปลี่ยนแปลง:</b> {rate_change*100:.3f}%\n"
            
            if position_data:
                size = abs(position_data.get("size", 0))
                mark_price = position_data.get("mark_price", 0)
                position_value = size * mark_price
                funding_income = position_value * current_rate
                
                message += f"""
💰 <b>รายได้คาดหวัง:</b> {funding_income:+.2f} USDT
📊 <b>มูลค่า Position:</b> {self.format_number(position_value)} USDT
"""
            
            message += f"\n⏰ <code>{timestamp}</code>"
            
            # บันทึกเวลาการแจ้งเตือน
            self.last_state["last_funding_alert_time"] = current_time
            
            # แจ้งเตือนพร้อมเสียงถ้าเป็นอันตราย
            notify = current_rate <= -0.002
            return self.send_message(message, disable_notification=not notify)
        
        return None
    
    def send_startup_message(self):
        """แจ้งเตือนเมื่อเริ่มระบบ"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
🤖 <b>เริ่มระบบ Auto Smart Trader แล้ว</b>

✅ ระบบเริ่มทำงานเรียบร้อย
🎯 กำลังตรวจสอบ Position และดำเนินการตามกฎ
📊 กลยุทธ์ Hybrid Strategy ทำงานแล้ว

⏰ <code>{timestamp}</code>
"""
        
        return self.send_message(message)
    
    def send_shutdown_message(self, reason="หยุดด้วยตัวเอง"):
        """แจ้งเตือนเมื่อหยุดระบบ"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
🛑 <b>หยุดระบบ Auto Smart Trader แล้ว</b>

📝 <b>เหตุผล:</b> {reason}
⏰ <code>{timestamp}</code>

กรุณาตรวจสอบ Position ด้วยตัวเองหากจำเป็น
"""
        
        return self.send_message(message)
    
    def send_error_alert(self, error_message, context=""):
        """แจ้งเตือนข้อผิดพลาด"""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
🚨 <b>แจ้งเตือนข้อผิดพลาด</b>

❌ <b>ข้อผิดพลาด:</b> {error_message}
"""
        
        if context:
            message += f"📝 <b>บริบท:</b> {context}\n"
        
        message += f"\n⏰ <code>{timestamp}</code>"
        
        return self.send_message(message)
    
    def test_connection(self):
        """ทดสอบการเชื่อมต่อ Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                bot_name = bot_info.get("result", {}).get("first_name", "ไม่ทราบชื่อ")
                print(f"✅ เชื่อมต่อ Telegram bot สำเร็จ: {bot_name}")
                
                # ส่งข้อความทดสอบ
                test_msg = "🧪 <b>ทดสอบระบบ</b>\n\nการแจ้งเตือน Telegram ภาษาไทยทำงานได้ปกติ!"
                result = self.send_message(test_msg)
                
                if result:
                    print("✅ ส่งข้อความทดสอบสำเร็จ")
                    return True
                else:
                    print("❌ ไม่สามารถส่งข้อความทดสอบได้")
                    return False
            else:
                print(f"❌ การเชื่อมต่อ Bot ล้มเหลว: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ การทดสอบการเชื่อมต่อล้มเหลว: {e}")
            return False

def main():
    """ฟังก์ชันหลักสำหรับทดสอบ"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telegram Notifier ภาษาไทย สำหรับ Auto Smart Trader")
    parser.add_argument("--test", action="store_true", help="ทดสอบการเชื่อมต่อ Telegram")
    
    args = parser.parse_args()
    
    if args.test:
        try:
            notifier = TelegramNotifierThai()
            notifier.test_connection()
        except Exception as e:
            print(f"❌ ข้อผิดพลาด: {e}")
        return
    
    print("ใช้ --test เพื่อทดสอบการเชื่อมต่อ")

if __name__ == "__main__":
    main()
