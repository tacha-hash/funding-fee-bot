#!/usr/bin/env python3
"""
การวิเคราะห์ผลกระทบการเก็บกำไรต่อเงินต้น Arbitrage
แบบง่ายและเข้าใจง่าย
"""
import subprocess
import sys

def get_current_status():
    """ดึงสถานะปัจจุบันจาก check_balance.py"""
    try:
        result = subprocess.run(
            [sys.executable, "check_balance.py"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"❌ ไม่สามารถดึงข้อมูลได้: {result.stderr}"
    except Exception as e:
        return f"❌ ข้อผิดพลาด: {e}"

def analyze_capital_impact():
    """วิเคราะห์ผลกระทบต่อเงินต้น"""
    print("🔍 วิเคราะห์ผลกระทบการเก็บกำไรต่อเงินต้น Arbitrage")
    print("=" * 70)
    
    # ดึงข้อมูลปัจจุบัน
    status = get_current_status()
    print("📊 สถานะปัจจุบัน:")
    print(status)
    print()
    
    # วิเคราะห์จากข้อมูลที่ได้
    lines = status.split('\n')
    
    # หาข้อมูลสำคัญ
    spot_usdt = 0
    futures_balance = 0
    position_size = 0
    position_pnl = 0
    position_entry = 0
    position_mark = 0
    
    for line in lines:
        if "USDT:" in line and "Free:" in line:
            # Spot USDT
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "USDT:" and i+1 < len(parts):
                    spot_usdt = float(parts[i+1])
                    break
        elif "Total Balance:" in line:
            # Futures balance
            parts = line.split()
            futures_balance = float(parts[2])
        elif "ASTERUSDT: SHORT" in line or "ASTERUSDT: LONG" in line:
            # Position info
            parts = line.split()
            position_size = float(parts[2])
            position_entry = float(parts[4])
        elif "Mark:" in line and "PNL:" in line:
            # Mark price and PnL
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "Mark:" and i+1 < len(parts):
                    position_mark = float(parts[i+1].replace(',', ''))
                elif part == "PNL:" and i+1 < len(parts):
                    position_pnl = float(parts[i+1])
    
    # คำนวณเงินต้นทั้งหมด
    total_capital = spot_usdt + futures_balance
    position_value = position_size * position_mark
    
    print("💰 การวิเคราะห์เงินต้น:")
    print("-" * 50)
    print(f"💵 Spot Wallet: {spot_usdt:.2f} USDT")
    print(f"💵 Futures Wallet: {futures_balance:.2f} USDT")
    print(f"💵 รวมเงินต้น: {total_capital:.2f} USDT")
    print()
    
    if position_size > 0:
        print(f"📊 Position ปัจจุบัน:")
        print(f"   ขนาด: {position_size:.2f} ASTER")
        print(f"   ราคาเข้า: {position_entry:.4f} USDT")
        print(f"   ราคาปัจจุบัน: {position_mark:.4f} USDT")
        print(f"   มูลค่า Position: {position_value:.2f} USDT")
        print(f"   PnL: {position_pnl:+.2f} USDT")
        print()
        
        # วิเคราะห์ผลกระทบการเก็บกำไร
        print("🎯 ผลกระทบการเก็บกำไร:")
        print("-" * 40)
        
        if position_pnl > 0:
            print("✅ กำไร! ระบบจะเก็บกำไรบางส่วน")
            
            # สมมติเก็บกำไร 20% ของ position
            take_profit_percentage = 0.20
            close_size = position_size * take_profit_percentage
            realized_profit = close_size * (position_mark - position_entry)
            remaining_size = position_size * (1 - take_profit_percentage)
            remaining_value = remaining_size * position_mark
            
            print(f"📈 สมมติเก็บกำไร 20%:")
            print(f"   - ปิด Position: {close_size:.2f} ASTER")
            print(f"   - กำไรที่ได้: {realized_profit:.2f} USDT")
            print(f"   - Position เหลือ: {remaining_size:.2f} ASTER")
            print(f"   - มูลค่าเหลือ: {remaining_value:.2f} USDT")
            print(f"   - เงินต้นที่ปลดล็อก: {position_value * take_profit_percentage:.2f} USDT")
            print()
            
            # คำนวณเงินต้นหลังเก็บกำไร
            new_total_capital = total_capital + realized_profit
            available_for_new_arbitrage = new_total_capital - remaining_value
            
            print("🔄 หลังเก็บกำไร:")
            print(f"   💰 เงินต้นรวมใหม่: {new_total_capital:.2f} USDT")
            print(f"   💰 เงินที่ใช้ได้สำหรับ Arbitrage ใหม่: {available_for_new_arbitrage:.2f} USDT")
            print()
            
            if available_for_new_arbitrage >= 100:
                print("✅ สามารถเริ่ม Arbitrage ใหม่ได้!")
                print("💡 กลยุทธ์ Hybrid:")
                print("   1. Position เดิม: เก็บกำไรต่อไป")
                print("   2. Position ใหม่: เริ่ม Arbitrage ใหม่")
                print("   3. ผลรวม: กำไรมากขึ้น + ความเสี่ยงกระจาย")
            else:
                print("⚠️ เงินไม่เพียงพอสำหรับ Arbitrage ใหม่")
                print("💡 รอให้ Position เดิมเก็บกำไรเพิ่มเติม")
        else:
            print("⏳ ยังขาดทุน - ระบบจะรอให้กำไร")
            print("💡 เงินต้นยังคงถูกใช้ในการ Arbitrage ต่อไป")
    else:
        print("📊 ไม่มี Position ที่ใช้งานอยู่")
        print(f"💡 เงินต้นทั้งหมด {total_capital:.2f} USDT พร้อมสำหรับ Arbitrage ใหม่")

def main():
    """ฟังก์ชันหลัก"""
    analyze_capital_impact()
    
    print("\n" + "=" * 70)
    print("🎯 สรุปคำตอบสำหรับคำถาม:")
    print("=" * 70)
    print("❓ การเก็บกำไรจะทำให้เงินต้นเสียหายไหม?")
    print("✅ คำตอบ: ไม่เสียหาย! ตรงกันข้าม - ดีขึ้น!")
    print()
    print("💡 เหตุผล:")
    print("   1. 💰 เงินที่เก็บกำไรจะกลับมาเป็นเงินสด")
    print("   2. 🔄 สามารถใช้เงินสดนั้นเริ่ม Arbitrage ใหม่ได้")
    print("   3. 📈 Position เดิมยังคงทำกำไรต่อไป")
    print("   4. 🎯 ผลรวม = กำไรมากขึ้น + ความเสี่ยงกระจาย")
    print()
    print("🔄 ระบบ Re-invest อัตโนมัติ:")
    print("   ✅ ระบบปัจจุบัน: เก็บกำไรบางส่วน (20%, 30%, 50%)")
    print("   ✅ เงินที่ได้: กลับมาเป็นเงินสดในบัญชี")
    print("   ✅ ขั้นตอนต่อไป: เริ่ม Arbitrage ใหม่ด้วยเงินสด")
    print("   ✅ ผลลัพธ์: เงินต้นเติบโต + กำไรเพิ่มขึ้น")
    print()
    print("📊 ข้อดีของการ Re-invest:")
    print("   🎯 เพิ่มโอกาสในการทำกำไร")
    print("   🛡️ กระจายความเสี่ยง")
    print("   💎 ใช้เงินต้นอย่างมีประสิทธิภาพ")
    print("   🚀 เงินต้นเติบโตแบบทบต้น")
    print()
    print("⚠️ ข้อควรระวัง:")
    print("   📊 ต้องจัดการ Position หลายตัว")
    print("   💰 ต้องมีเงินสำรองเพียงพอ")
    print("   📈 ต้องติดตาม Funding Rate หลายคู่")
    print("   🎯 ต้องมีกลยุทธ์การจัดการความเสี่ยง")

if __name__ == "__main__":
    main()
