#!/usr/bin/env python3
"""
Auto Smart Trader with Thai Telegram Notifications
เวอร์ชันภาษาไทย แจ้งเตือนเฉพาะการเปลี่ยนแปลงสำคัญ
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import our Thai telegram notifier
try:
    from telegram_notifier_thai import TelegramNotifierThai
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram notifications ไม่พร้อมใช้งาน - ดำเนินการต่อโดยไม่มีการแจ้งเตือน")

class AutoSmartTraderThai:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("ไม่พบ API credentials")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
        
        # Initialize Thai Telegram notifier
        self.telegram = None
        if TELEGRAM_AVAILABLE:
            try:
                self.telegram = TelegramNotifierThai()
                print("✅ เปิดใช้งานการแจ้งเตือน Telegram ภาษาไทย")
            except Exception as e:
                print(f"⚠️ ตั้งค่า Telegram ล้มเหลว: {e}")
                print("ดำเนินการต่อโดยไม่มีการแจ้งเตือน...")
        
        # Trading rules - Hybrid Strategy
        self.rules = {
            # กฎการเก็บกำไร
            "profit_targets": {
                "partial_take_1": {"threshold": 10.0, "percentage": 0.25, "executed": False},
                "partial_take_2": {"threshold": 25.0, "percentage": 0.30, "executed": False},
                "partial_take_3": {"threshold": 50.0, "percentage": 0.40, "executed": False},
                "full_exit": {"threshold": 100.0, "percentage": 1.0, "executed": False}
            },
            
            # กฎการจัดการความเสี่ยง
            "risk_management": {
                "stop_loss": -20.0,           # Stop loss ที่ -20 USDT
                "trailing_stop": True,        # เปิดใช้ trailing stop
                "trailing_distance": 10.0,    # ห่างจาก peak 10 USDT
                "max_drawdown": 15.0,         # Drawdown สูงสุด 15 USDT
                "margin_limit": 0.35          # Margin สูงสุด 35%
            },
            
            # กฎ Funding rate
            "funding_rules": {
                "negative_threshold": -0.002,  # ออกถ้า funding < -0.2%
                "very_negative": -0.005,       # บังคับออกถ้า < -0.5%
                "rebalance_threshold": 0.01    # ปรับสมดุลถ้า > 1%
            },
            
            # การจัดการ Position
            "position_rules": {
                "min_position_size": 10.0,     # ขนาด position ขั้นต่ำ
                "max_position_size": 500.0,    # ขนาด position สูงสุด
                "rebalance_interval": 24,      # ชั่วโมงระหว่างการปรับสมดุล
                "max_hold_days": 30           # วันสูงสุดที่ถือ position
            }
        }
        
        # ติดตามสถานะ
        self.state = {
            "peak_pnl": 0.0,
            "last_rebalance": None,
            "position_start_time": None,
            "executed_rules": [],
            "total_realized_profit": 0.0
        }
        
        self.dry_run = False  # ตั้งเป็น True สำหรับทดสอบ
        
    def notify_telegram(self, message_type, data):
        """ส่งการแจ้งเตือนไป Telegram"""
        if not self.telegram:
            return
        
        try:
            if message_type == "trading_action":
                self.telegram.send_trading_action(data)
            elif message_type == "position_update":
                self.telegram.send_position_update(data.get("position"), data.get("account"))
            elif message_type == "funding_alert":
                self.telegram.send_funding_alert(data.get("funding"), data.get("position"))
            elif message_type == "startup":
                self.telegram.send_startup_message()
            elif message_type == "shutdown":
                self.telegram.send_shutdown_message(data.get("reason", "หยุดด้วยตัวเอง"))
            elif message_type == "error":
                self.telegram.send_error_alert(data.get("message"), data.get("context", ""))
        except Exception as e:
            print(f"⚠️ การแจ้งเตือน Telegram ล้มเหลว: {e}")
    
    def sign_params(self, params):
        """เซ็นพารามิเตอร์ API request"""
        api_secret = self.api_secret.encode('utf-8')
        params.setdefault("recvWindow", 5000)
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params, doseq=True)
        signature = hmac.new(api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params
    
    def make_request(self, base_url, path, params=None, method="GET", signed=False):
        """ทำ API request"""
        url = f"{base_url}{path}"
        params = params or {}
        
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "AutoSmartTraderThai/1.0",
        }
        
        if signed:
            params = self.sign_params(params)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.request(method.upper(), url, data=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                self.notify_telegram("error", {"message": error_msg, "context": f"{method} {path}"})
                return None
        except Exception as e:
            error_msg = f"Request failed: {e}"
            print(f"❌ {error_msg}")
            self.notify_telegram("error", {"message": error_msg, "context": f"{method} {path}"})
            return None
    
    def get_current_position(self):
        """ดึงข้อมูล position ปัจจุบัน ASTERUSDT"""
        positions = self.make_request(
            self.futures_base_url, "/fapi/v2/positionRisk", {}, signed=True
        )
        
        if not positions:
            return None
        
        for pos in positions:
            if pos["symbol"] == "ASTERUSDT" and abs(float(pos["positionAmt"])) > 0:
                return {
                    "symbol": pos["symbol"],
                    "size": float(pos["positionAmt"]),
                    "side": "LONG" if float(pos["positionAmt"]) > 0 else "SHORT",
                    "entry_price": float(pos["entryPrice"]),
                    "mark_price": float(pos["markPrice"]),
                    "pnl": float(pos["unRealizedProfit"]),
                    "notional": abs(float(pos["positionAmt"]) * float(pos["markPrice"]))
                }
        return None
    
    def get_account_info(self):
        """ดึงข้อมูลบัญชี futures"""
        account = self.make_request(
            self.futures_base_url, "/fapi/v2/account", {}, signed=True
        )
        
        if not account:
            return None
        
        return {
            "total_balance": float(account["totalWalletBalance"]),
            "available_balance": float(account["availableBalance"]),
            "total_pnl": float(account["totalUnrealizedProfit"]),
            "margin_ratio": float(account["totalInitialMargin"]) / float(account["totalWalletBalance"]) if float(account["totalWalletBalance"]) > 0 else 0
        }
    
    def get_funding_rate(self):
        """ดึงข้อมูล funding rate ปัจจุบัน"""
        funding = self.make_request(
            self.futures_base_url, "/fapi/v1/premiumIndex", {"symbol": "ASTERUSDT"}
        )
        
        if not funding:
            return None
        
        return {
            "rate": float(funding["lastFundingRate"]),
            "next_time": datetime.fromtimestamp(funding["nextFundingTime"] / 1000, timezone.utc)
        }
    
    def close_position_partial(self, position, percentage):
        """ปิด position บางส่วน"""
        close_size = abs(position["size"]) * percentage
        close_size = self._floor_to_step(close_size, 0.01)  # ปัดเศษตาม step size
        
        if close_size < 0.01:  # ขนาดคำสั่งขั้นต่ำ
            print(f"⚠️ ขนาดการปิดน้อยเกินไป: {close_size}")
            return None
        
        # สำหรับ SHORT position ใช้ BUY เพื่อปิด
        side = "BUY" if position["side"] == "SHORT" else "SELL"
        
        payload = {
            "symbol": "ASTERUSDT",
            "side": side,
            "type": "MARKET",
            "quantity": f"{close_size:.2f}",
            "reduceOnly": "true"
        }
        
        if self.dry_run:
            print(f"🧪 โหมดทดสอบ: จะปิด {percentage*100:.1f}% ({close_size:.2f} ASTER) ด้วย {side}")
            return {"orderId": "DRY_RUN", "executedQty": close_size, "status": "FILLED"}
        
        print(f"📤 กำลังปิด {percentage*100:.1f}% position: {side} {close_size:.2f} ASTER")
        
        result = self.make_request(
            self.futures_base_url, "/fapi/v1/order", payload, method="POST", signed=True
        )
        
        return result
    
    def close_position_full(self, position):
        """ปิด position ทั้งหมด"""
        return self.close_position_partial(position, 1.0)
    
    def _floor_to_step(self, value, step):
        """ปัดเศษตาม step size"""
        return float(Decimal(str(value)) - (Decimal(str(value)) % Decimal(str(step))))
    
    def evaluate_profit_targets(self, position, current_pnl):
        """ประเมินและดำเนินการตามกฎการเก็บกำไร"""
        actions = []
        
        if current_pnl <= 0:
            return actions
        
        # ตรวจสอบเป้าหมายการเก็บกำไร
        for rule_name, rule in self.rules["profit_targets"].items():
            if rule["executed"]:
                continue
                
            if current_pnl >= rule["threshold"]:
                print(f"🎯 เป้าหมายการเก็บกำไรถูกเรียกใช้: {rule_name} ที่ {current_pnl:.2f} USDT")
                
                # ดำเนินการปิด position บางส่วน
                result = self.close_position_partial(position, rule["percentage"])
                
                if result and result.get("status") == "FILLED":
                    executed_qty = float(result.get("executedQty", 0))
                    realized_profit = executed_qty * (position["mark_price"] - position["entry_price"])
                    if position["side"] == "SHORT":
                        realized_profit = -realized_profit  # กลับเครื่องหมายสำหรับ short
                    
                    self.state["total_realized_profit"] += realized_profit
                    rule["executed"] = True
                    
                    action_data = {
                        "type": "profit_take",
                        "rule": rule_name,
                        "percentage": rule["percentage"] * 100,
                        "quantity": executed_qty,
                        "realized_profit": realized_profit,
                        "remaining_pnl": current_pnl
                    }
                    
                    actions.append(action_data)
                    
                    # ส่งการแจ้งเตือน Telegram
                    self.notify_telegram("trading_action", action_data)
                    
                    print(f"✅ ดำเนินการ {rule_name}: ปิด {executed_qty:.2f} ASTER, กำไรที่ได้ {realized_profit:.2f} USDT")
                break  # ดำเนินการเพียงกฎเดียวต่อรอบ
        
        return actions
    
    def evaluate_risk_management(self, position, account, current_pnl):
        """ประเมินและดำเนินการจัดการความเสี่ยง"""
        actions = []
        
        # อัพเดท peak PnL สำหรับ trailing stop
        if current_pnl > self.state["peak_pnl"]:
            self.state["peak_pnl"] = current_pnl
        
        # ตรวจสอบ stop loss
        if current_pnl <= self.rules["risk_management"]["stop_loss"]:
            print(f"🚨 STOP LOSS ถูกเรียกใช้: {current_pnl:.2f} USDT")
            result = self.close_position_full(position)
            if result:
                action_data = {
                    "type": "stop_loss",
                    "reason": "Hard stop loss",
                    "pnl": current_pnl
                }
                actions.append(action_data)
                self.notify_telegram("trading_action", action_data)
            return actions
        
        # ตรวจสอบ trailing stop
        if self.rules["risk_management"]["trailing_stop"]:
            trailing_stop_level = self.state["peak_pnl"] - self.rules["risk_management"]["trailing_distance"]
            if current_pnl <= trailing_stop_level and self.state["peak_pnl"] > 0:
                print(f"🚨 TRAILING STOP ถูกเรียกใช้: {current_pnl:.2f} USDT (Peak: {self.state['peak_pnl']:.2f})")
                result = self.close_position_full(position)
                if result:
                    action_data = {
                        "type": "trailing_stop",
                        "reason": f"Trailing stop จาก peak {self.state['peak_pnl']:.2f}",
                        "pnl": current_pnl
                    }
                    actions.append(action_data)
                    self.notify_telegram("trading_action", action_data)
                return actions
        
        # ตรวจสอบ max drawdown
        drawdown = self.state["peak_pnl"] - current_pnl
        if drawdown >= self.rules["risk_management"]["max_drawdown"] and self.state["peak_pnl"] > 0:
            print(f"🚨 MAX DRAWDOWN ถูกเรียกใช้: {drawdown:.2f} USDT จาก peak")
            result = self.close_position_partial(position, 0.5)  # ปิด 50%
            if result:
                action_data = {
                    "type": "drawdown_protection",
                    "reason": f"Max drawdown {drawdown:.2f} USDT",
                    "percentage": 50
                }
                actions.append(action_data)
                self.notify_telegram("trading_action", action_data)
        
        # ตรวจสอบการใช้ margin
        if account and account["margin_ratio"] >= self.rules["risk_management"]["margin_limit"]:
            print(f"⚠️ การใช้ MARGIN สูง: {account['margin_ratio']*100:.1f}%")
            result = self.close_position_partial(position, 0.3)  # ปิด 30%
            if result:
                action_data = {
                    "type": "margin_management",
                    "reason": f"การใช้ margin สูง {account['margin_ratio']*100:.1f}%",
                    "percentage": 30
                }
                actions.append(action_data)
                self.notify_telegram("trading_action", action_data)
        
        return actions
    
    def evaluate_funding_rules(self, position, funding_rate):
        """ประเมินกฎ funding rate"""
        actions = []
        
        if not funding_rate:
            return actions
        
        rate = funding_rate["rate"]
        
        # ส่งการแจ้งเตือน funding (มีการ throttle)
        self.notify_telegram("funding_alert", {
            "funding": funding_rate,
            "position": position
        })
        
        # Funding rate ติดลบมาก - บังคับออก
        if rate <= self.rules["funding_rules"]["very_negative"]:
            print(f"🚨 FUNDING RATE ติดลบมาก: {rate*100:.3f}% - บังคับออก")
            result = self.close_position_full(position)
            if result:
                action_data = {
                    "type": "funding_exit",
                    "reason": f"Funding rate ติดลบมาก {rate*100:.3f}%",
                    "rate": rate
                }
                actions.append(action_data)
                self.notify_telegram("trading_action", action_data)
        
        # Funding rate ติดลบ - เตือน
        elif rate <= self.rules["funding_rules"]["negative_threshold"]:
            print(f"⚠️ FUNDING RATE ติดลบ: {rate*100:.3f}% - พิจารณาออก")
            # ไม่ปิดอัตโนมัติ แค่เตือน
            actions.append({
                "type": "funding_warning",
                "reason": f"Funding rate ติดลบ {rate*100:.3f}%",
                "rate": rate
            })
        
        return actions
    
    def run_strategy_cycle(self):
        """รันกลยุทธ์การเทรดหนึ่งรอบ"""
        print(f"\n🤖 รอบการทำงาน Auto Smart Trader - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 80)
        
        # ดึงข้อมูลปัจจุบัน
        position = self.get_current_position()
        if not position:
            print("ℹ️ ไม่พบ position ที่ใช้งานอยู่")
            return []
        
        account = self.get_account_info()
        funding = self.get_funding_rate()
        current_pnl = position["pnl"]
        
        print(f"📊 Position: {position['side']} {abs(position['size']):.2f} ASTER @ {position['entry_price']:.4f}")
        print(f"💰 PnL ปัจจุบัน: {current_pnl:+.2f} USDT")
        print(f"📈 ราคา Mark: {position['mark_price']:.4f} USDT")
        if funding:
            print(f"💎 Funding Rate: {funding['rate']*100:.3f}% (8h)")
        
        # ส่งการอัพเดท position (มี throttle)
        self.notify_telegram("position_update", {
            "position": position,
            "account": account
        })
        
        all_actions = []
        
        # 1. ประเมินเป้าหมายการเก็บกำไร
        profit_actions = self.evaluate_profit_targets(position, current_pnl)
        all_actions.extend(profit_actions)
        
        # 2. ประเมินการจัดการความเสี่ยง (เฉพาะถ้า position ยังอยู่)
        if not any(action["type"] in ["stop_loss", "funding_exit"] for action in all_actions):
            risk_actions = self.evaluate_risk_management(position, account, current_pnl)
            all_actions.extend(risk_actions)
        
        # 3. ประเมินกฎ funding (เฉพาะถ้า position ยังอยู่)
        if not any(action["type"] in ["stop_loss", "trailing_stop", "funding_exit"] for action in all_actions):
            funding_actions = self.evaluate_funding_rules(position, funding)
            all_actions.extend(funding_actions)
        
        # บันทึกการกระทำ
        if all_actions:
            print(f"\n📋 การกระทำในรอบนี้: {len(all_actions)}")
            for i, action in enumerate(all_actions, 1):
                print(f"   {i}. {action['type'].upper()}: {action.get('reason', 'ไม่ระบุ')}")
        else:
            print("\n✅ ไม่ต้องดำเนินการ - position เสถียร")
        
        return all_actions
    
    def run_continuous(self, check_interval_minutes=5):
        """รันการเทรดอัตโนมัติอย่างต่อเนื่อง"""
        print(f"🤖 เริ่ม Auto Smart Trader ภาษาไทย")
        print(f"⚙️ ช่วงเวลาการตรวจสอบ: {check_interval_minutes} นาที")
        print(f"🧪 โหมดทดสอบ: {'เปิด' if self.dry_run else 'ปิด'}")
        print(f"📱 Telegram: {'เปิด' if self.telegram else 'ปิด'}")
        print("กด Ctrl+C เพื่อหยุด")
        print("=" * 80)
        
        # ส่งการแจ้งเตือนเริ่มระบบ
        self.notify_telegram("startup", {})
        
        try:
            while True:
                actions = self.run_strategy_cycle()
                
                # ตรวจสอบว่า position ถูกปิดหมดหรือไม่
                position = self.get_current_position()
                if not position:
                    print(f"\n🎯 Position ถูกปิดหมดแล้ว กำไรรวมที่ได้: {self.state['total_realized_profit']:.2f} USDT")
                    self.notify_telegram("shutdown", {"reason": "Position ถูกปิดหมดแล้ว"})
                    print("หยุดการทำงาน auto trader...")
                    break
                
                print(f"\n⏰ ตรวจสอบครั้งถัดไปใน {check_interval_minutes} นาที...")
                print("=" * 80)
                
                time.sleep(check_interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n👋 Auto Smart Trader หยุดโดยผู้ใช้")
            self.notify_telegram("shutdown", {"reason": "หยุดโดยผู้ใช้"})
            
            # แสดงสรุปสุดท้าย
            position = self.get_current_position()
            if position:
                print(f"📊 Position สุดท้าย: {position['side']} {abs(position['size']):.2f} ASTER")
                print(f"💰 PnL ที่ยังไม่ได้รับ: {position['pnl']:+.2f} USDT")
            print(f"💎 กำไรรวมที่ได้: {self.state['total_realized_profit']:.2f} USDT")
        except Exception as e:
            error_msg = f"ข้อผิดพลาดที่ไม่คาดคิด: {e}"
            print(f"❌ {error_msg}")
            self.notify_telegram("error", {"message": error_msg, "context": "Main loop"})
            raise

def main():
    """ฟังก์ชันหลัก"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AsterDex Auto Smart Trader ภาษาไทย")
    parser.add_argument("--dry-run", action="store_true", help="รันในโหมดทดสอบ (ไม่เทรดจริง)")
    parser.add_argument("--interval", "-i", type=int, default=5, help="ช่วงเวลาการตรวจสอบเป็นนาที (default: 5)")
    parser.add_argument("--show-rules", action="store_true", help="แสดงกฎการเทรดและออก")
    
    args = parser.parse_args()
    
    try:
        trader = AutoSmartTraderThai()
        trader.dry_run = args.dry_run
        
        if args.show_rules:
            print("🎯 กฎการเทรดอัตโนมัติ:")
            print("=" * 50)
            print(json.dumps(trader.rules, indent=2, ensure_ascii=False))
            return
        
        trader.run_continuous(args.interval)
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาด: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
