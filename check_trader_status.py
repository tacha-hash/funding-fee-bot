#!/usr/bin/env python3
"""
Script สำหรับตรวจสอบสถานะ Auto Smart Trader
ใช้เพื่อดูว่าระบบยังทำงานอยู่หรือไม่
"""
import os
import sys
import subprocess
import time
from datetime import datetime

def check_process_status():
    """ตรวจสอบว่า Auto Smart Trader ยังทำงานอยู่หรือไม่"""
    try:
        # ค้นหา process ที่รัน auto_smart_trader_thai.py
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            if 'auto_smart_trader_thai.py' in line and 'grep' not in line:
                processes.append(line.strip())
        
        return processes
    except Exception as e:
        print(f"❌ ไม่สามารถตรวจสอบ process ได้: {e}")
        return []

def check_recent_activity():
    """ตรวจสอบกิจกรรมล่าสุดจากไฟล์ log (ถ้ามี)"""
    log_files = [
        "trader.log",
        "auto_trader.log", 
        "smart_trader.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        return f"📋 Log ล่าสุด: {last_line}"
            except Exception as e:
                continue
    
    return "📋 ไม่พบไฟล์ log"

def get_position_info():
    """ดึงข้อมูล position ปัจจุบัน"""
    try:
        # เรียกใช้ check_balance.py เพื่อดูสถานะปัจจุบัน
        result = subprocess.run(
            [sys.executable, "check_balance.py"], 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            output = result.stdout
            # หาข้อมูล position จาก output
            lines = output.split('\n')
            position_info = []
            
            in_positions = False
            for line in lines:
                if "CURRENT POSITIONS:" in line:
                    in_positions = True
                    continue
                elif "RECENT ORDERS:" in line:
                    in_positions = False
                    break
                elif in_positions and line.strip() and not line.startswith("---"):
                    position_info.append(line.strip())
            
            if position_info:
                return "📊 " + "\n📊 ".join(position_info)
            else:
                return "📊 ไม่มี Position ที่ใช้งานอยู่"
        else:
            return f"❌ ไม่สามารถดึงข้อมูล position ได้: {result.stderr}"
            
    except Exception as e:
        return f"❌ ข้อผิดพลาด: {e}"

def main():
    """ฟังก์ชันหลัก"""
    print("🔍 ตรวจสอบสถานะ Auto Smart Trader")
    print("=" * 60)
    print(f"⏰ เวลาตรวจสอบ: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # ตรวจสอบ process
    processes = check_process_status()
    
    if processes:
        print("✅ Auto Smart Trader กำลังทำงานอยู่:")
        for i, process in enumerate(processes, 1):
            # แยกข้อมูล process
            parts = process.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_used = parts[9]
                command = " ".join(parts[10:])
                
                print(f"   {i}. PID: {pid}")
                print(f"      CPU: {cpu}%, Memory: {mem}%")
                print(f"      เวลาทำงาน: {time_used}")
                print(f"      คำสั่ง: {command}")
                print()
        
        print("🎯 สถานะ: ระบบทำงานปกติ")
        
    else:
        print("❌ Auto Smart Trader ไม่ได้ทำงาน")
        print("💡 เรียกใช้: python3 auto_smart_trader_thai.py --interval 3")
        print()
    
    # ตรวจสอบข้อมูล position
    print("📊 ข้อมูล Position ปัจจุบัน:")
    print("-" * 40)
    position_info = get_position_info()
    print(position_info)
    print()
    
    # ตรวจสอบกิจกรรมล่าสุด
    activity = check_recent_activity()
    print(activity)
    print()
    
    # คำแนะนำ
    if processes:
        print("💡 คำแนะนำ:")
        print("   - คุณสามารถปิดหน้าต่าง Terminal ได้")
        print("   - ระบบจะทำงานต่อไปในพื้นหลัง")
        print("   - ใช้คำสั่งนี้เพื่อตรวจสอบสถานะอีกครั้ง:")
        print("     python3 check_trader_status.py")
        print("   - หรือดูจาก Telegram notifications")
        print()
        print("🛑 หยุดระบบ: kill " + " ".join([p.split()[1] for p in processes]))
    else:
        print("🚀 เริ่มระบบ: python3 auto_smart_trader_thai.py --interval 3")

if __name__ == "__main__":
    main()
