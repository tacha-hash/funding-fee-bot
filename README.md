# AsterDex Funding Bot

`funding_bot.py` เป็นสคริปต์ Python สำหรับทำกลยุทธ์ Buy Spot / Short Futures หรือ Sell Spot / Long Futures บน AsterDex เพื่อฟาร์มค่าธรรมเนียม Funding โดยอัตโนมัติ สคริปต์จะทยอยส่งคำสั่งในแต่ละขาแบบจับคู่จนกว่าจะครบยอดทุนรวมที่กำหนด

## คุณสมบัติหลัก
- ส่งคำสั่ง Spot และ Futures แบบจับคู่ทีละรอบ พร้อมดีเลย์ตามที่ตั้งค่า
- ตรวจสอบการเติมเต็มคำสั่ง (fill) และเรียกดูสถานะซ้ำจนกว่าจะได้รับการยืนยัน
- รองรับการตั้งค่าคีย์ API และพารามิเตอร์สำคัญผ่านตัวแปรด้านบนไฟล์หรือผ่านบรรทัดคำสั่ง
- ล็อกกิจกรรมแบบมีสี แสดงสถานะการทำงานอย่างละเอียดในแต่ละขั้น
- เลือกทิศทางเทรดได้ผ่าน `--mode` (ซื้อสปอต/ชอร์ตฟิวเจอร์ส หรือขายสปอต/ลองฟิวเจอร์ส)

## สิ่งที่ต้องมี
- Python 3.9 ขึ้นไป
- ไลบรารี `requests`
- บัญชี AsterDex ที่มี API Key/Secret และเงินทุนเพียงพอ

## การตั้งค่า

### วิธีที่ 1: ใช้ Setup Script (แนะนำ)
รันสคริปต์ตั้งค่า environment อัตโนมัติ:
```bash
python3 setup_env.py
```

### วิธีที่ 2: ตั้งค่าเอง
1. คัดลอกไฟล์ตัวอย่าง:
```bash
cp .env.example .env
```

2. แก้ไขไฟล์ `.env` และใส่ API credentials ของคุณ:
```
ASTERDEX_API_KEY=your_actual_api_key_here
ASTERDEX_API_SECRET=your_actual_api_secret_here
```

### วิธีที่ 3: ใช้ Environment Variables
ตั้งค่าผ่าน shell:
```bash
export ASTERDEX_API_KEY="your_api_key"
export ASTERDEX_API_SECRET="your_api_secret"
```

### การปรับแต่งค่าเริ่มต้น
ค่าพื้นฐานสามารถแก้ไขได้ในไฟล์ `.env` หรือผ่าน command line arguments:
```
DEFAULT_CAPITAL_USD=200000
DEFAULT_SPOT_SYMBOL=ASTERUSDT
DEFAULT_FUTURES_SYMBOL=ASTERUSDT
DEFAULT_BATCH_QUOTE=200
DEFAULT_BATCH_DELAY=1.0
DEFAULT_MODE=buy_spot_short_futures
```

## การใช้งาน
ติดตั้งไลบรารีที่จำเป็นก่อน:
```bash
pip3 install -r requirements.txt
```
หรือติดตั้งแยก:
```bash
pip3 install requests python-dotenv
```
รันสคริปต์ด้วยค่าเริ่มต้น:
```
python3 funding_bot.py
```
หรือกำหนดพารามิเตอร์ผ่าน CLI:
```
python3 funding_bot.py \
  --capital 5000 \
  --spot-symbol ASTERUSDT \
  --futures-symbol ASTERUSDT \
  --batch-quote 100 \
  --batch-delay 2 \
  --log-level DEBUG \
  --mode sell_spot_long_futures
```

## ผลลัพธ์
เมื่อรันเสร็จ สคริปต์จะแสดง JSON สรุปการเทรด
- รายการคำสั่ง Spot ในแต่ละรอบ พร้อมจำนวนที่เติมเต็มและค่าใช้จ่าย
- รายการคำสั่ง Futures ในแต่ละรอบ พร้อมจำนวนและโนเชียนอลที่ป้องกันความเสี่ยง
- ข้อมูลเป้าหมายโดยรวม (ทุนรวม, จำนวนรอบ, ขนาดแต่ละล็อต)

## หมายเหตุความปลอดภัย
- พึงระวังการฝังรหัส API ลงในไฟล์ ถ้าแชร์โค้ดให้พิจารณาย้ายไปใช้ environment variable และไม่ commit ค่า key จริง
- ทดสอบด้วยทุนจำนวนน้อยก่อน และตรวจสอบว่าคำสั่งแต่ละชุดผ่านข้อกำหนดขั้นต่ำของตลาด (LOT_SIZE, MIN_NOTIONAL)
- ตรวจสอบรายการเทรดและยอดคงเหลือบน AsterDex เสมอ เพื่อยืนยันว่าการป้องกันความเสี่ยงทำงานสมบูรณ์ และไม่มีคำสั่งตกค้าง

ขอให้ใช้งานอย่างปลอดภัยและทดสอบกลยุทธ์ก่อนลงเงินจำนวนมาก
