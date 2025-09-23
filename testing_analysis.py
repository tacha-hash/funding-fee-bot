#!/usr/bin/env python3
"""
วิเคราะห์ผลการทดสอบระบบ Auto Smart Trader
และคำแนะนำระยะเวลาการทดสอบที่เหมาะสม
"""
import subprocess
import sys
from datetime import datetime, timedelta

def get_current_status():
    """ดึงสถานะปัจจุบัน"""
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

def analyze_testing_results():
    """วิเคราะห์ผลการทดสอบ"""
    print("🔍 วิเคราะห์ผลการทดสอบระบบ Auto Smart Trader")
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
    
    # คำนวณข้อมูลสำคัญ
    total_capital = spot_usdt + futures_balance
    position_value = position_size * position_mark
    roi_percentage = (position_pnl / total_capital) * 100
    
    print("💰 การวิเคราะห์ผลการทดสอบ:")
    print("-" * 50)
    print(f"💵 เงินต้นรวม: {total_capital:.2f} USDT")
    print(f"📊 Position: {position_size:.2f} ASTER @ {position_entry:.4f}")
    print(f"📈 ราคาปัจจุบัน: {position_mark:.4f} USDT")
    print(f"💰 PnL: {position_pnl:+.2f} USDT")
    print(f"📊 ROI: {roi_percentage:+.2f}%")
    print()
    
    # วิเคราะห์ความเสถียร
    analyze_stability(position_pnl, roi_percentage, position_value, total_capital)
    
    # คำแนะนำระยะเวลาการทดสอบ
    recommend_testing_duration(position_pnl, roi_percentage)
    
    # คำแนะนำการเพิ่มทุน
    recommend_capital_increase(position_pnl, roi_percentage, total_capital)

def analyze_stability(pnl, roi, position_value, total_capital):
    """วิเคราะห์ความเสถียรของระบบ"""
    print("🎯 การวิเคราะห์ความเสถียร:")
    print("-" * 40)
    
    # เกณฑ์การประเมิน
    stability_score = 0
    max_score = 5
    
    # 1. กำไร/ขาดทุน
    if pnl > 0:
        print("✅ กำไร: ระบบทำกำไรได้")
        stability_score += 1
    else:
        print("❌ ขาดทุน: ต้องปรับปรุง")
    
    # 2. ROI
    if roi > 0.5:  # มากกว่า 0.5%
        print("✅ ROI ดี: มากกว่า 0.5%")
        stability_score += 1
    elif roi > 0:
        print("⚠️ ROI ต่ำ: มากกว่า 0% แต่ต่ำกว่า 0.5%")
        stability_score += 0.5
    else:
        print("❌ ROI ติดลบ: ต้องปรับปรุง")
    
    # 3. ขนาด Position
    position_ratio = position_value / total_capital
    if 0.1 <= position_ratio <= 0.3:  # 10-30% ของเงินต้น
        print("✅ ขนาด Position เหมาะสม: 10-30% ของเงินต้น")
        stability_score += 1
    elif position_ratio < 0.1:
        print("⚠️ Position เล็กเกินไป: น้อยกว่า 10% ของเงินต้น")
        stability_score += 0.5
    else:
        print("⚠️ Position ใหญ่เกินไป: มากกว่า 30% ของเงินต้น")
        stability_score += 0.5
    
    # 4. ความเสี่ยง
    if abs(pnl) < total_capital * 0.05:  # PnL ไม่เกิน 5% ของเงินต้น
        print("✅ ความเสี่ยงต่ำ: PnL ไม่เกิน 5% ของเงินต้น")
        stability_score += 1
    else:
        print("⚠️ ความเสี่ยงสูง: PnL เกิน 5% ของเงินต้น")
    
    # 5. การจัดการ
    if pnl > 0 and roi > 0:
        print("✅ การจัดการดี: ระบบทำงานตามที่คาดหวัง")
        stability_score += 1
    
    # สรุปคะแนน
    stability_percentage = (stability_score / max_score) * 100
    print(f"\n📊 คะแนนความเสถียร: {stability_score:.1f}/{max_score} ({stability_percentage:.1f}%)")
    
    if stability_percentage >= 80:
        print("🎉 ระบบเสถียรมาก - พร้อมใช้งานจริง")
    elif stability_percentage >= 60:
        print("✅ ระบบเสถียรดี - ควรทดสอบต่อ")
    elif stability_percentage >= 40:
        print("⚠️ ระบบเสถียรปานกลาง - ต้องปรับปรุง")
    else:
        print("❌ ระบบไม่เสถียร - ต้องแก้ไขก่อน")

def recommend_testing_duration(pnl, roi):
    """แนะนำระยะเวลาการทดสอบ"""
    print("\n⏰ คำแนะนำระยะเวลาการทดสอบ:")
    print("-" * 50)
    
    if pnl > 0 and roi > 0.5:
        print("✅ ผลการทดสอบดี:")
        print("   - กำไร: +{:.2f} USDT".format(pnl))
        print("   - ROI: +{:.2f}%".format(roi))
        print()
        print("🎯 แนะนำระยะเวลาการทดสอบ:")
        print("   📅 ขั้นต่ำ: 7-14 วัน")
        print("   📅 เหมาะสม: 30 วัน")
        print("   📅 ปลอดภัย: 60-90 วัน")
        print()
        print("💡 เหตุผล:")
        print("   - ต้องทดสอบในสภาวะตลาดต่างๆ")
        print("   - ต้องผ่าน Funding Rate หลายรอบ")
        print("   - ต้องทดสอบระบบ Auto Smart Trader")
        print("   - ต้องทดสอบการจัดการความเสี่ยง")
        
    elif pnl > 0:
        print("⚠️ ผลการทดสอบปานกลาง:")
        print("   - กำไร: +{:.2f} USDT".format(pnl))
        print("   - ROI: +{:.2f}%".format(roi))
        print()
        print("🎯 แนะนำระยะเวลาการทดสอบ:")
        print("   📅 ขั้นต่ำ: 30 วัน")
        print("   📅 เหมาะสม: 60 วัน")
        print("   📅 ปลอดภัย: 90-120 วัน")
        print()
        print("💡 เหตุผล:")
        print("   - ต้องปรับปรุงประสิทธิภาพ")
        print("   - ต้องทดสอบในสภาวะตลาดที่หลากหลาย")
        print("   - ต้องทดสอบระบบจัดการความเสี่ยง")
        
    else:
        print("❌ ผลการทดสอบไม่ดี:")
        print("   - PnL: {:.2f} USDT".format(pnl))
        print("   - ROI: {:.2f}%".format(roi))
        print()
        print("🎯 แนะนำระยะเวลาการทดสอบ:")
        print("   📅 ต้องปรับปรุงก่อน: 30-60 วัน")
        print("   📅 หลังปรับปรุง: 60-90 วัน")
        print()
        print("💡 ต้องแก้ไข:")
        print("   - ปรับปรุงกลยุทธ์การเทรด")
        print("   - ปรับปรุงการจัดการความเสี่ยง")
        print("   - ทดสอบในสภาวะตลาดต่างๆ")

def recommend_capital_increase(pnl, roi, total_capital):
    """แนะนำการเพิ่มทุน"""
    print("\n💰 คำแนะนำการเพิ่มทุน:")
    print("-" * 50)
    
    if pnl > 0 and roi > 1.0:  # ROI มากกว่า 1%
        print("🚀 ผลการทดสอบยอดเยี่ยม!")
        print("   - กำไร: +{:.2f} USDT".format(pnl))
        print("   - ROI: +{:.2f}%".format(roi))
        print()
        print("💎 แนะนำการเพิ่มทุน:")
        print("   📈 หลังทดสอบ 30 วัน: เพิ่ม 50-100%")
        print("   📈 หลังทดสอบ 60 วัน: เพิ่ม 100-200%")
        print("   📈 หลังทดสอบ 90 วัน: เพิ่ม 200-500%")
        print()
        print("🎯 ตัวอย่าง:")
        current = total_capital
        print(f"   - เงินต้นปัจจุบัน: {current:.2f} USDT")
        print(f"   - เพิ่ม 50%: {current * 1.5:.2f} USDT")
        print(f"   - เพิ่ม 100%: {current * 2:.2f} USDT")
        print(f"   - เพิ่ม 200%: {current * 3:.2f} USDT")
        
    elif pnl > 0 and roi > 0.5:  # ROI มากกว่า 0.5%
        print("✅ ผลการทดสอบดี!")
        print("   - กำไร: +{:.2f} USDT".format(pnl))
        print("   - ROI: +{:.2f}%".format(roi))
        print()
        print("💎 แนะนำการเพิ่มทุน:")
        print("   📈 หลังทดสอบ 60 วัน: เพิ่ม 25-50%")
        print("   📈 หลังทดสอบ 90 วัน: เพิ่ม 50-100%")
        print("   📈 หลังทดสอบ 120 วัน: เพิ่ม 100-200%")
        print()
        print("🎯 ตัวอย่าง:")
        current = total_capital
        print(f"   - เงินต้นปัจจุบัน: {current:.2f} USDT")
        print(f"   - เพิ่ม 25%: {current * 1.25:.2f} USDT")
        print(f"   - เพิ่ม 50%: {current * 1.5:.2f} USDT")
        print(f"   - เพิ่ม 100%: {current * 2:.2f} USDT")
        
    elif pnl > 0:
        print("⚠️ ผลการทดสอบปานกลาง")
        print("   - กำไร: +{:.2f} USDT".format(pnl))
        print("   - ROI: +{:.2f}%".format(roi))
        print()
        print("💎 แนะนำการเพิ่มทุน:")
        print("   📈 หลังทดสอบ 90 วัน: เพิ่ม 10-25%")
        print("   📈 หลังทดสอบ 120 วัน: เพิ่ม 25-50%")
        print("   📈 หลังทดสอบ 180 วัน: เพิ่ม 50-100%")
        print()
        print("🎯 ตัวอย่าง:")
        current = total_capital
        print(f"   - เงินต้นปัจจุบัน: {current:.2f} USDT")
        print(f"   - เพิ่ม 10%: {current * 1.1:.2f} USDT")
        print(f"   - เพิ่ม 25%: {current * 1.25:.2f} USDT")
        print(f"   - เพิ่ม 50%: {current * 1.5:.2f} USDT")
        
    else:
        print("❌ ผลการทดสอบไม่ดี")
        print("   - PnL: {:.2f} USDT".format(pnl))
        print("   - ROI: {:.2f}%".format(roi))
        print()
        print("💎 แนะนำการเพิ่มทุน:")
        print("   🚫 ไม่ควรเพิ่มทุนในขณะนี้")
        print("   🔧 ต้องปรับปรุงระบบก่อน")
        print("   📅 หลังปรับปรุงและทดสอบ 90 วัน: พิจารณาเพิ่มทุน")
        print()
        print("🎯 ต้องแก้ไข:")
        print("   - ปรับปรุงกลยุทธ์การเทรด")
        print("   - ปรับปรุงการจัดการความเสี่ยง")
        print("   - ทดสอบในสภาวะตลาดต่างๆ")

def main():
    """ฟังก์ชันหลัก"""
    analyze_testing_results()
    
    print("\n" + "=" * 70)
    print("🎯 สรุปคำแนะนำ:")
    print("=" * 70)
    print("📅 ระยะเวลาการทดสอบที่แนะนำ:")
    print("   ✅ ขั้นต่ำ: 30 วัน")
    print("   ✅ เหมาะสม: 60 วัน")
    print("   ✅ ปลอดภัย: 90 วัน")
    print()
    print("💰 การเพิ่มทุนที่แนะนำ:")
    print("   🚀 ผลดีมาก: เพิ่ม 50-200%")
    print("   ✅ ผลดี: เพิ่ม 25-100%")
    print("   ⚠️ ผลปานกลาง: เพิ่ม 10-50%")
    print("   ❌ ผลไม่ดี: ไม่ควรเพิ่มทุน")
    print()
    print("🎯 เกณฑ์การประเมิน:")
    print("   📊 ROI > 1%: ยอดเยี่ยม")
    print("   📊 ROI > 0.5%: ดี")
    print("   📊 ROI > 0%: ปานกลาง")
    print("   📊 ROI < 0%: ต้องปรับปรุง")
    print()
    print("⚠️ ข้อควรระวัง:")
    print("   🛡️ อย่าเพิ่มทุนเร็วเกินไป")
    print("   📈 ต้องทดสอบในสภาวะตลาดต่างๆ")
    print("   🔄 ต้องผ่าน Funding Rate หลายรอบ")
    print("   🎯 ต้องทดสอบระบบ Auto Smart Trader")

if __name__ == "__main__":
    main()
