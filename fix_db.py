import os
import glob

# 1. ค้นหาและลบไฟล์ฐานข้อมูลเดิม (.db) ทั้งหมด
db_files = glob.glob('**/instance/*.db', recursive=True) + glob.glob('*.db')
for f in db_files:
    try:
        os.remove(f)
        print(f"ลบไฟล์ฐานข้อมูลเดิมเรียบร้อย: {f}")
    except Exception as e:
        print(f"ข้ามการลบไฟล์ {f}: {e}")

# 2. นำเข้าแอปและสั่งสร้างตารางใหม่ทั้งหมดให้อัตโนมัติ
try:
    from smashlab.app import app, db
except ImportError:
    from app import app, db

with app.app_context():
    db.create_all()
    print("==========================================")
    print("สร้างโครงสร้างตารางใหม่ทั้งหมดเรียบร้อยแล้ว!")
    print("==========================================")