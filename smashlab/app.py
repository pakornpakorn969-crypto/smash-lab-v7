import os
from flask import Flask, render_template, jsonify, request

# 1. ประกาศตัวแปร app สำหรับ Gunicorn และ Flask
app = Flask(__name__, static_folder='static', template_folder='templates')

# ตั้งค่า Secret Key สำหรับ Session/Cookies
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smash-lab-v7-secret-key-2026')

# 2. Route หน้าหลัก (Landing Page)
@app.route('/')
def index():
    return render_template('index.html')

# --- ใส่ Route และ API เพิ่มเติมของระบบตรงนี้ ---


# 3. ส่วนการรันเซิร์ฟเวอร์แบบ Local และ Render
if __name__ == '__main__':
    # ดึงค่า PORT จาก Render (ถ้าไม่มีจะใช้พอร์ต 5000 สำหรับ Local)
    port = int(os.environ.get('PORT', 5000))
    # เปิด host 0.0.0.0 เพื่อรองรับการรับ Connection บน Cloud
    app.run(host='0.0.0.0', port=port, debug=False)