import threading
import webview
from smashlab.app import app

def run_server():
    # รัน Flask เบื้องหลัง
    app.run(port=5000, debug=False)

if __name__ == '__main__':
    # เริ่มต้นรันเซิร์ฟเวอร์ Flask ใน Thread แยก
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()

    # สร้างหน้าต่างแอปพลิเคชัน
    webview.create_window('Smash Lab Enterprise V7', 'http://127.0.0.1:5000', width=1280, height=800)
    webview.start()