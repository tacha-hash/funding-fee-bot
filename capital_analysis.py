#!/usr/bin/env python3
"""
วิเคราะห์ผลกระทบของการเก็บกำไรต่อเงินต้น Arbitrage
และคำแนะนำการ Re-invest
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class CapitalAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("ไม่พบ API credentials")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
    
    def make_request(self, base_url, endpoint, params=None, method="GET", signed=False):
        """สร้าง API request"""
        if params is None:
            params = {}
        
        url = f"{base_url}{endpoint}"
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query_string = urlencode(params)
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature
        
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers={"X-MBX-APIKEY": self.api_key})
            else:
                response = requests.post(url, data=params, headers={"X-MBX-APIKEY": self.api_key})
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ API Error: {e}")
            return None
    
    def get_account_balances(self):
        """ดึงข้อมูลยอดเงินในบัญชี"""
        # ใช้ API endpoints ที่ถูกต้องตาม check_balance.py
        spot_balance = self.make_request(
            self.spot_base_url, "/api/v3/account", {}, method="GET", signed=True
        )
        
        futures_balance = self.make_request(
            self.futures_base_url, "/fapi/v2/balance", {}, method="GET", signed=True
        )
        
        return spot_balance, futures_balance
    
    def get_current_position(self):
        """ดึงข้อมูล position ปัจจุบัน"""
        positions = self.make_request(
            self.futures_base_url, "/fapi/v2/positionRisk", {}, method="GET", signed=True
        )
        
        if not positions:
            return None
        
        for pos in positions:
            if pos["symbol"] == "ASTERUSDT" and float(pos["positionAmt"]) != 0:
                return {
                    "symbol": pos["symbol"],
                    "side": "LONG" if float(pos["positionAmt"]) > 0 else "SHORT",
                    "size": abs(float(pos["positionAmt"])),
                    "entry_price": float(pos["entryPrice"]),
                    "mark_price": float(pos["markPrice"]),
                    "pnl": float(pos.get("unRealizedPnl", 0)),
                    "percentage": float(pos.get("percentage", 0)),
                    "notional": float(pos.get("notional", 0))
                }
        
        return None
    
    def analyze_capital_impact(self):
        """วิเคราะห์ผลกระทบต่อเงินต้น"""
        print("🔍 วิเคราะห์ผลกระทบการเก็บกำไรต่อเงินต้น Arbitrage")
        print("=" * 70)
        
        # ดึงข้อมูลบัญชี
        spot_balance, futures_balance = self.get_account_balances()
        position = self.get_current_position()
        
        if not spot_balance or not futures_balance:
            print("❌ ไม่สามารถดึงข้อมูลบัญชีได้")
            return
        
        # คำนวณยอดเงินปัจจุบัน
        spot_usdt = 0
        futures_usdt = 0
        
        for asset in spot_balance.get("balances", []):
            if asset["asset"] == "USDT":
                spot_usdt = float(asset["free"]) + float(asset["locked"])
                break
        
        for asset in futures_balance:
            if asset["asset"] == "USDT":
                futures_usdt = float(asset["balance"])
                break
        
        total_capital = spot_usdt + futures_usdt
        
        print(f"💰 ยอดเงินปัจจุบัน:")
        print(f"   Spot Wallet: {spot_usdt:.2f} USDT")
        print(f"   Futures Wallet: {futures_usdt:.2f} USDT")
        print(f"   รวม: {total_capital:.2f} USDT")
        print()
        
        if position:
            print(f"📊 Position ปัจจุบัน:")
            print(f"   {position['side']} {position['size']:.2f} ASTER @ {position['entry_price']:.4f}")
            print(f"   Mark Price: {position['mark_price']:.4f}")
            print(f"   PnL: {position['pnl']:+.2f} USDT")
            print(f"   Notional Value: {position['notional']:.2f} USDT")
            print()
            
            # คำนวณเงินต้นที่ใช้ในการ arbitrage
            position_value = position['notional']
            available_capital = total_capital - position_value
            
            print(f"🎯 การวิเคราะห์เงินต้น:")
            print(f"   เงินที่ใช้ใน Position: {position_value:.2f} USDT")
            print(f"   เงินที่เหลือใช้ได้: {available_capital:.2f} USDT")
            print()
            
            # วิเคราะห์ผลกระทบการเก็บกำไร
            self.analyze_profit_taking_impact(position, total_capital, position_value)
        else:
            print("📊 ไม่มี Position ที่ใช้งานอยู่")
            print(f"💡 เงินต้นทั้งหมด {total_capital:.2f} USDT พร้อมสำหรับ Arbitrage ใหม่")
    
    def analyze_profit_taking_impact(self, position, total_capital, position_value):
        """วิเคราะห์ผลกระทบการเก็บกำไร"""
        print("📈 ผลกระทบการเก็บกำไรต่อเงินต้น:")
        print("-" * 50)
        
        # สมมติฐานการเก็บกำไร (ตามระบบปัจจุบัน)
        profit_rules = [
            {"name": "เก็บกำไร 20%", "percentage": 0.20, "threshold": 5.0},
            {"name": "เก็บกำไร 30%", "percentage": 0.30, "threshold": 10.0},
            {"name": "เก็บกำไร 50%", "percentage": 0.50, "threshold": 20.0}
        ]
        
        current_pnl = position['pnl']
        
        for rule in profit_rules:
            if current_pnl >= rule['threshold']:
                # คำนวณผลกระทบ
                close_size = position['size'] * rule['percentage']
                realized_profit = close_size * (position['mark_price'] - position['entry_price'])
                if position['side'] == 'SHORT':
                    realized_profit = -realized_profit
                
                remaining_size = position['size'] * (1 - rule['percentage'])
                remaining_value = remaining_size * position['mark_price']
                
                print(f"✅ {rule['name']} (กำไร {current_pnl:.2f} USDT):")
                print(f"   - เก็บกำไร: {realized_profit:.2f} USDT")
                print(f"   - Position เหลือ: {remaining_size:.2f} ASTER ({remaining_value:.2f} USDT)")
                print(f"   - เงินต้นที่ปลดล็อก: {position_value * rule['percentage']:.2f} USDT")
                print(f"   - เงินต้นรวมหลังเก็บกำไร: {total_capital + realized_profit:.2f} USDT")
                print()
                
                # คำแนะนำการ Re-invest
                self.recommend_reinvestment(total_capital + realized_profit, remaining_value)
                break
        else:
            print(f"⏳ ยังไม่ถึงเกณฑ์การเก็บกำไร (ปัจจุบัน: {current_pnl:.2f} USDT)")
            print("💡 เงินต้นยังคงถูกใช้ในการ Arbitrage ต่อไป")
    
    def recommend_reinvestment(self, total_capital, remaining_position_value):
        """แนะนำการ Re-invest"""
        print("🔄 คำแนะนำการ Re-invest:")
        print("-" * 40)
        
        available_capital = total_capital - remaining_position_value
        
        print(f"💰 เงินที่ใช้ได้สำหรับ Arbitrage ใหม่: {available_capital:.2f} USDT")
        
        if available_capital >= 100:  # ขั้นต่ำสำหรับ arbitrage
            print("✅ สามารถเริ่ม Arbitrage ใหม่ได้!")
            print(f"💡 แนะนำ:")
            print(f"   - ใช้เงิน {available_capital * 0.8:.2f} USDT สำหรับ Arbitrage ใหม่")
            print(f"   - เก็บเงิน {available_capital * 0.2:.2f} USDT เป็นเงินสำรอง")
            print()
            print("🎯 กลยุทธ์ Hybrid:")
            print("   1. Position เดิม: เก็บกำไรต่อไป")
            print("   2. Position ใหม่: เริ่ม Arbitrage ใหม่")
            print("   3. ผลรวม: เพิ่มโอกาสในการทำกำไร")
        else:
            print("⚠️ เงินไม่เพียงพอสำหรับ Arbitrage ใหม่")
            print("💡 แนะนำ:")
            print("   - รอให้ Position เดิมเก็บกำไรเพิ่มเติม")
            print("   - หรือรอให้ Position ปิดทั้งหมด")
            print("   - แล้วค่อยเริ่ม Arbitrage ใหม่")
        
        print()
        print("📊 ข้อดีของการ Re-invest:")
        print("   ✅ เพิ่มโอกาสในการทำกำไร")
        print("   ✅ กระจายความเสี่ยง")
        print("   ✅ ใช้เงินต้นอย่างมีประสิทธิภาพ")
        print()
        print("⚠️ ข้อควรระวัง:")
        print("   ⚠️ ต้องจัดการ Position หลายตัว")
        print("   ⚠️ ต้องมีเงินสำรองเพียงพอ")
        print("   ⚠️ ต้องติดตาม Funding Rate หลายคู่")

def main():
    """ฟังก์ชันหลัก"""
    try:
        analyzer = CapitalAnalyzer()
        analyzer.analyze_capital_impact()
        
        print("\n" + "=" * 70)
        print("🎯 สรุปคำตอบสำหรับคำถาม:")
        print("=" * 70)
        print("❓ การเก็บกำไรจะทำให้เงินต้นเสียหายไหม?")
        print("✅ คำตอบ: ไม่เสียหาย! ตรงกันข้าม - ดีขึ้น!")
        print()
        print("💡 เหตุผล:")
        print("   1. เงินที่เก็บกำไรจะกลับมาเป็นเงินสด")
        print("   2. สามารถใช้เงินสดนั้นเริ่ม Arbitrage ใหม่ได้")
        print("   3. Position เดิมยังคงทำกำไรต่อไป")
        print("   4. ผลรวม = กำไรมากขึ้น + ความเสี่ยงกระจาย")
        print()
        print("🔄 ระบบ Re-invest อัตโนมัติ:")
        print("   - ระบบปัจจุบัน: เก็บกำไรบางส่วน")
        print("   - เงินที่ได้: กลับมาเป็นเงินสด")
        print("   - ขั้นตอนต่อไป: เริ่ม Arbitrage ใหม่")
        print("   - ผลลัพธ์: เงินต้นเติบโต + กำไรเพิ่มขึ้น")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    main()
