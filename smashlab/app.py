import sys
import subprocess

# ==============================================================================
# 0. AUTO-DEPENDENCY INSTALLER (ตรวจสอบและติดตั้ง Packages ให้อัตโนมัติ)
# ==============================================================================
required_packages = ["flask", "flask_sqlalchemy", "requests", "werkzeug"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"[SYSTEM] กำลังติดตั้งแพ็กเกจ '{package}' ให้อัตโนมัติ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import os
import json
import base64
import random
import requests
import webbrowser
from datetime import datetime
from functools import wraps
from threading import Timer

from flask import Flask, render_template_string, request, jsonify, session, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# 1. CONFIGURATION & DATABASE INITIALIZATION
# ==============================================================================
app = Flask(__name__)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "smashlab-v7-ultimate-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///smashlab_v7.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

app.config.from_object(Config)
db = SQLAlchemy(app)

# ==============================================================================
# 2. HELPER SERVICES (LINE Notify & Vector SVG Generator)
# ==============================================================================
def send_line_notification(message_text):
    """ส่งข้อความแจ้งเตือนผ่าน LINE Notify (หรือจำลองใน Terminal)"""
    token = os.environ.get("LINE_NOTIFY_TOKEN", "")
    if not token:
        print(f"\n[LINE NOTIFY ALERT]: {message_text.strip()}\n")
        return
    
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        requests.post(url, headers=headers, data={"message": message_text}, timeout=3)
    except Exception as e:
        print(f"LINE Notification Error: {e}")

class VectorAssetService:
    @staticmethod
    def generate_racket_svg(brand, model, category, accent_color="#06b6d4"):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 400" width="100%" height="100%">
            <defs>
                <radialGradient id="grad-{brand}-{model}" cx="50%" cy="30%" r="70%">
                    <stop offset="0%" stop-color="{accent_color}" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#020617" stop-opacity="0.95"/>
                </radialGradient>
                <linearGradient id="frameGrad-{brand}-{model}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="{accent_color}"/>
                    <stop offset="100%" stop-color="#1e293b"/>
                </linearGradient>
            </defs>
            <rect width="300" height="400" rx="16" fill="url(#grad-{brand}-{model})"/>
            <ellipse cx="150" cy="120" rx="65" ry="85" fill="none" stroke="url(#frameGrad-{brand}-{model})" stroke-width="10"/>
            <ellipse cx="150" cy="120" rx="58" ry="78" fill="none" stroke="#334155" stroke-width="1.5" stroke-dasharray="4 4"/>
            <path d="M 115 120 H 185 M 110 90 H 190 M 110 150 H 190 M 120 65 H 180 M 120 175 H 180" stroke="#94a3b8" stroke-width="0.8" opacity="0.6"/>
            <path d="M 150 40 V 200 M 130 45 V 195 M 170 45 V 195 M 110 80 V 160 M 190 80 V 160" stroke="#94a3b8" stroke-width="0.8" opacity="0.6"/>
            <line x1="150" y1="205" x2="150" y2="310" stroke="#475569" stroke-width="7"/>
            <line x1="150" y1="205" x2="150" y2="310" stroke="{accent_color}" stroke-width="2"/>
            <rect x="141" y="310" width="18" height="65" rx="4" fill="#0f172a" stroke="#334155" stroke-width="2"/>
            <text x="150" y="28" text-anchor="middle" fill="#f8fafc" font-family="sans-serif" font-size="12" font-weight="bold" letter-spacing="2">{brand}</text>
            <text x="150" y="388" text-anchor="middle" fill="{accent_color}" font-family="sans-serif" font-size="10" font-weight="bold">{category} SPEC</text>
        </svg>'''
        encoded = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
        return f"data:image/svg+xml;base64,{encoded}"

# ==============================================================================
# 3. DATABASE MODELS
# ==============================================================================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='customer') # 'admin' or 'customer'
    points = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role, "points": self.points}

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    series = db.Column(db.String(50))
    category = db.Column(db.String(50), nullable=False) # POWER, SPEED, CONTROL
    weight_spec = db.Column(db.String(20), default="4U (83g)")
    max_tension = db.Column(db.String(20), default="28 lbs")
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=10)
    color_hex = db.Column(db.String(10), default="#06b6d4")
    description = db.Column(db.Text)
    badge = db.Column(db.String(30), default="HOT")
    image_url = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id, "brand": self.brand, "model": self.model, "series": self.series,
            "category": self.category, "weight_spec": self.weight_spec, "max_tension": self.max_tension,
            "price": self.price, "stock": self.stock, "color_hex": self.color_hex,
            "description": self.description, "badge": self.badge, "image_url": self.image_url
        }

class Coupon(db.Model):
    __tablename__ = 'coupons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    discount_type = db.Column(db.String(10), nullable=False) # 'percent' or 'fixed'
    discount_value = db.Column(db.Float, nullable=False)
    min_spend = db.Column(db.Float, default=0)

    def to_dict(self):
        return {"id": self.id, "code": self.code, "discount_type": self.discount_type, "discount_value": self.discount_value, "min_spend": self.min_spend}

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_email = db.Column(db.String(120), nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float, nullable=False)
    coupon_code = db.Column(db.String(30))
    slip_image = db.Column(db.Text)
    status = db.Column(db.String(30), default='รอตรวจสอบ') # 'รอตรวจสอบ', 'ชำระแล้ว', 'กำลังจัดส่ง'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "order_no": self.order_no, "user_id": self.user_id, "user_email": self.user_email,
            "items": json.loads(self.items_json), "subtotal": self.subtotal, "discount_amount": self.discount_amount,
            "total_price": self.total_price, "coupon_code": self.coupon_code, "slip_image": self.slip_image,
            "status": self.status, "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class QueueBooking(db.Model):
    __tablename__ = 'queue_bookings'
    id = db.Column(db.Integer, primary_key=True)
    booking_no = db.Column(db.String(50), unique=True, nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    string_type = db.Column(db.String(50))
    tension_lbs = db.Column(db.Integer)
    booking_date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default='กำลังรอคิว') # 'กำลังรอคิว', 'กำลังขึ้นเอ็น', 'เสร็จสิ้นพร้อมรับ'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "booking_no": self.booking_no, "user_name": self.user_name, "phone": self.phone,
            "service_type": self.service_type, "string_type": self.string_type, "tension_lbs": self.tension_lbs,
            "booking_date": self.booking_date, "status": self.status, "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class CourtBooking(db.Model):
    __tablename__ = 'court_bookings'
    id = db.Column(db.Integer, primary_key=True)
    booking_no = db.Column(db.String(50), unique=True, nullable=False)
    court_no = db.Column(db.Integer, nullable=False)
    booking_date = db.Column(db.String(20), nullable=False)
    time_slot = db.Column(db.String(30), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, default=250.0)
    status = db.Column(db.String(30), default='ยืนยันการจอง')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "booking_no": self.booking_no, "court_no": self.court_no,
            "booking_date": self.booking_date, "time_slot": self.time_slot,
            "user_name": self.user_name, "phone": self.phone, "price": self.price, "status": self.status
        }

class MatchmakingPost(db.Model):
    __tablename__ = 'matchmaking_posts'
    id = db.Column(db.Integer, primary_key=True)
    court_location = db.Column(db.String(100), default="SMASH LAB Badminton Club")
    play_date = db.Column(db.String(20), nullable=False)
    play_time = db.Column(db.String(30), nullable=False)
    level = db.Column(db.String(50), default="มือใหม่ / ออกกำลังกาย")
    players_needed = db.Column(db.Integer, default=2)
    contact_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "court_location": self.court_location, "play_date": self.play_date,
            "play_time": self.play_time, "level": self.level, "players_needed": self.players_needed,
            "contact_name": self.contact_name, "phone": self.phone, "note": self.note,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M')
        }

# ==============================================================================
# 4. API BLUEPRINTS & ROUTES
# ==============================================================================
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
catalog_bp = Blueprint('catalog', __name__, url_prefix='/api/catalog')
order_bp = Blueprint('order', __name__, url_prefix='/api/orders')
queue_bp = Blueprint('queue', __name__, url_prefix='/api/queue')
court_bp = Blueprint('court', __name__, url_prefix='/api/court')
community_bp = Blueprint('community', __name__, url_prefix='/api/community')
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# --- Auth Routes ---
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email, password = data.get('email'), data.get('password')
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"}), 401

    session['user_id'], session['role'], session['user_name'] = user.id, user.role, user.name
    return jsonify({"success": True, "user": user.to_dict()})

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@auth_bp.route('/me', methods=['GET'])
def get_me():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({"is_logged_in": True, "user": user.to_dict()})
    return jsonify({"is_logged_in": False})

# --- Catalog & AI Matcher Routes ---
@catalog_bp.route('/products', methods=['GET'])
def get_products():
    category = request.args.get('category', 'ALL')
    search = request.args.get('search', '').strip().lower()

    query = Product.query
    if category != 'ALL':
        query = query.filter_by(category=category)

    products = query.all()
    if search:
        products = [p for p in products if search in p.brand.lower() or search in p.model.lower()]

    return jsonify([p.to_dict() for p in products])

@catalog_bp.route('/spin-wheel', methods=['POST'])
def spin_wheel():
    prizes = [
        {"code": "SPIN10", "type": "percent", "value": 10, "label": "ส่วนลด 10%"},
        {"code": "SPIN20", "type": "percent", "value": 20, "label": "ส่วนลด 20%"},
        {"code": "LUCKY100", "type": "fixed", "value": 100, "label": "ส่วนลด 100 บาท"},
        {"code": "FREESHIP", "type": "fixed", "value": 50, "label": "ส่งฟรี (ส่วนลด 50฿)"}
    ]
    prize = random.choice(prizes)
    if not Coupon.query.filter_by(code=prize['code']).first():
        db.session.add(Coupon(code=prize['code'], discount_type=prize['type'], discount_value=prize['value'], min_spend=500))
        db.session.commit()
    return jsonify({"success": True, "prize": prize})

@catalog_bp.route('/ai-recommend', methods=['POST'])
def ai_recommend():
    data = request.json or {}
    style = data.get('style', 'POWER')
    level = data.get('level', 'BEGINNER')
    budget = float(data.get('budget', 10000))

    products = Product.query.filter(Product.category == style, Product.price <= budget).all()
    recommended_tension = 20 if level == 'BEGINNER' else (24 if level == 'INTERMEDIATE' else 27)

    return jsonify({
        "success": True,
        "recommended_tension": recommended_tension,
        "products": [p.to_dict() for p in products]
    })

# --- Order Routes ---
@order_bp.route('/create', methods=['POST'])
def create_order():
    data = request.json or {}
    items, discount_amount, coupon_code, slip_image = data.get('items', []), data.get('discount_amount', 0), data.get('coupon_code'), data.get('slip_image')
    if not items:
        return jsonify({"success": False, "message": "ไม่มีสินค้าในตะกร้า"}), 400

    subtotal = sum(item['price'] * item['quantity'] for item in items)
    total_price = max(0, subtotal - discount_amount)
    user_email, user_id = "Guest", None

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user: user_id, user_email = user.id, user.email

    order_no = f"SL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order = Order(
        order_no=order_no, user_id=user_id, user_email=user_email,
        items_json=json.dumps([{"product_name": f"{i.get('brand')} {i.get('model')}", "price": i.get('price'), "quantity": i.get('quantity')} for i in items]),
        subtotal=subtotal, discount_amount=discount_amount, total_price=total_price,
        coupon_code=coupon_code, slip_image=slip_image, status='รอตรวจสอบ' if slip_image else 'รอชำระเงิน'
    )
    db.session.add(order)
    db.session.commit()

    send_line_notification(f"\n🛒 ออเดอร์ใหม่: {order_no}\nผู้สั่ง: {user_email}\nยอดสุทธิ: {total_price:,.2f} บาท")
    return jsonify({"success": True, "order": order.to_dict()})

# --- Queue & Court Booking Routes ---
@queue_bp.route('/create', methods=['POST'])
def create_queue():
    data = request.json or {}
    booking_no = f"Q-{datetime.now().strftime('%m%d%H%M%S')}"
    booking = QueueBooking(
        booking_no=booking_no, user_name=data.get('user_name'), phone=data.get('phone'),
        service_type=data.get('service_type'), string_type=data.get('string_type', 'BG-65'),
        tension_lbs=int(data.get('tension_lbs', 24)), booking_date=data.get('booking_date')
    )
    db.session.add(booking)
    db.session.commit()
    send_line_notification(f"\n🏸 คิวขึ้นเอ็นใหม่: {booking_no}\nคุณ {booking.user_name} ({booking.phone})\nบริการ: {booking.service_type} {booking.tension_lbs} Lbs")
    return jsonify({"success": True, "booking": booking.to_dict()})

@queue_bp.route('/list', methods=['GET'])
def list_queues():
    return jsonify([q.to_dict() for q in QueueBooking.query.order_by(QueueBooking.created_at.desc()).all()])

@court_bp.route('/book', methods=['POST'])
def book_court():
    data = request.json or {}
    court_no, date, time_slot = data.get('court_no'), data.get('booking_date'), data.get('time_slot')
    
    existing = CourtBooking.query.filter_by(court_no=court_no, booking_date=date, time_slot=time_slot).first()
    if existing:
        return jsonify({"success": False, "message": "ช่วงเวลานี้ในสนามดังกล่าวถูกจองแล้ว"}), 400

    booking_no = f"CRT-{datetime.now().strftime('%m%d%H%M%S')}"
    booking = CourtBooking(
        booking_no=booking_no, court_no=court_no, booking_date=date,
        time_slot=time_slot, user_name=data.get('user_name'), phone=data.get('phone')
    )
    db.session.add(booking)
    db.session.commit()
    send_line_notification(f"\n🏟️ จองสนามแบดมินตัน: {booking_no}\nคอร์ด: {court_no} | วันที่: {date} ({time_slot})\nผู้จอง: {booking.user_name}")
    return jsonify({"success": True, "booking": booking.to_dict()})

@court_bp.route('/list', methods=['GET'])
def list_courts():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return jsonify([c.to_dict() for c in CourtBooking.query.filter_by(booking_date=date).all()])

# --- Community Matchmaking Routes ---
@community_bp.route('/posts', methods=['GET'])
def get_community_posts():
    return jsonify([p.to_dict() for p in MatchmakingPost.query.order_by(MatchmakingPost.created_at.desc()).all()])

@community_bp.route('/posts/create', methods=['POST'])
def create_community_post():
    data = request.json or {}
    post = MatchmakingPost(
        court_location=data.get('court_location', 'SMASH LAB Court'),
        play_date=data.get('play_date'), play_time=data.get('play_time'),
        level=data.get('level', 'มือใหม่ / ออกกำลังกาย'), players_needed=int(data.get('players_needed', 2)),
        contact_name=data.get('contact_name'), phone=data.get('phone'), note=data.get('note', '')
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"success": True, "post": post.to_dict()})

# --- Admin Management Routes ---
@admin_bp.route('/dashboard', methods=['GET'])
def admin_dashboard():
    total_revenue = db.session.query(db.func.sum(Order.total_price)).filter(Order.status == 'ชำระแล้ว').scalar() or 0
    return jsonify({
        "total_revenue": total_revenue,
        "total_orders": Order.query.count(),
        "pending_orders": Order.query.filter_by(status='รอตรวจสอบ').count(),
        "pending_queues": QueueBooking.query.filter(QueueBooking.status != 'เสร็จสิ้นพร้อมรับ').count(),
        "total_court_bookings": CourtBooking.query.count()
    })

@admin_bp.route('/orders', methods=['GET'])
def admin_orders():
    return jsonify([o.to_dict() for o in Order.query.order_by(Order.created_at.desc()).all()])

@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    order = Order.query.get(order_id)
    if not order: return jsonify({"success": False, "message": "ไม่พบออเดอร์"}), 404
    order.status = (request.json or {}).get('status')
    db.session.commit()
    return jsonify({"success": True, "order": order.to_dict()})

@admin_bp.route('/queue/<int:queue_id>/status', methods=['PUT'])
def update_queue_status(queue_id):
    q = QueueBooking.query.get(queue_id)
    if not q: return jsonify({"success": False, "message": "ไม่พบคิว"}), 404
    q.status = (request.json or {}).get('status')
    db.session.commit()
    return jsonify({"success": True, "queue": q.to_dict()})

app.register_blueprint(auth_bp)
app.register_blueprint(catalog_bp)
app.register_blueprint(order_bp)
app.register_blueprint(queue_bp)
app.register_blueprint(court_bp)
app.register_blueprint(community_bp)
app.register_blueprint(admin_bp)

# ==============================================================================
# 5. SINGLE PAGE APPLICATION (SPA) HTML TEMPLATE
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th" class="dark scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMASH LAB V7 - Enterprise Badminton Ecosystem</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: { cyan: { 400: '#22d3ee', 500: '#06b6d4', 950: '#083344' }, slate: { 850: '#0f172a', 950: '#020617' } }
                }
            }
        }
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600;700&family=Orbitron:wght@600;800;900&display=swap');
        body { font-family: 'Kanit', sans-serif; background-color: #020617; color: #f8fafc; }
        .font-mono { font-family: 'Orbitron', monospace; }
        .glass { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glass-modal { background: rgba(2, 6, 23, 0.92); backdrop-filter: blur(20px); }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between selection:bg-cyan-500 selection:text-slate-950">

    <!-- Toast Notification -->
    <div id="toast" class="fixed top-5 right-5 z-50 transform translate-x-full transition-transform duration-300 px-5 py-3 rounded-xl glass border border-cyan-500/30 text-white font-medium shadow-2xl flex items-center gap-3">
        <i id="toastIcon" class="fa-solid fa-circle-check text-cyan-400"></i>
        <span id="toastMsg">ข้อความแจ้งเตือน</span>
    </div>

    <!-- Navigation Header -->
    <header class="sticky top-0 z-40 glass border-b border-slate-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            <div class="flex items-center gap-3 cursor-pointer" onclick="window.scrollTo({top: 0, behavior: 'smooth'})">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-mono font-black text-slate-950 text-xl shadow-lg shadow-cyan-500/20">SL</div>
                <span class="font-mono font-extrabold text-2xl tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-cyan-400">SMASH LAB V7</span>
            </div>

            <nav class="hidden lg:flex items-center gap-6 text-xs font-semibold text-slate-300">
                <a href="#studio" class="hover:text-cyan-400 transition">3D STUDIO</a>
                <a href="#ai-quiz" class="hover:text-cyan-400 transition"><i class="fa-solid fa-wand-magic-sparkles text-cyan-400 mr-1"></i>AI MATCHER</a>
                <a href="#courts" class="hover:text-cyan-400 transition">จองสนาม</a>
                <a href="#queue" class="hover:text-cyan-400 transition">คิวขึ้นเอ็น</a>
                <a href="#community" class="hover:text-cyan-400 transition">ก๊วนแบด</a>
                <a href="#catalog" class="hover:text-cyan-400 transition">CATALOG</a>
            </nav>

            <div class="flex items-center gap-3">
                <button onclick="openAdminModal()" class="bg-rose-600/20 border border-rose-500/40 text-rose-400 font-bold px-3 py-2 rounded-xl text-xs font-mono hover:bg-rose-600 hover:text-white transition flex items-center gap-1.5">
                    <i class="fa-solid fa-user-shield"></i> แอดมิน
                </button>
                <button onclick="openSpinModal()" class="bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold px-3 py-2 rounded-xl text-xs font-mono transition flex items-center gap-1.5 shadow-lg shadow-amber-500/20">
                    <i class="fa-solid fa-arrows-spin animate-spin"></i> หมุนวงล้อ
                </button>
                <button onclick="openCartModal()" class="relative bg-slate-900 border border-slate-800 hover:border-cyan-500/50 p-2.5 rounded-xl text-slate-200 transition">
                    <i class="fa-solid fa-cart-shopping text-base"></i>
                    <span id="cartCountBadge" class="absolute -top-1.5 -right-1.5 bg-cyan-500 text-slate-950 text-[11px] font-mono font-bold px-2 py-0.5 rounded-full shadow">0</span>
                </button>
            </div>
        </div>
    </header>

    <main class="flex-grow space-y-16 py-8">

        <!-- 3D STUDIO SECTION -->
        <section id="studio" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex flex-col lg:flex-row items-center gap-8 bg-slate-900/50 border border-slate-800 rounded-3xl p-6 lg:p-8 backdrop-blur-md">
                <div class="w-full lg:w-2/3 h-[420px] bg-slate-950 rounded-2xl relative overflow-hidden border border-slate-800/80 shadow-2xl">
                    <div id="racket3dContainer" class="w-full h-full cursor-grab"></div>
                    <div class="absolute bottom-4 left-4 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400">
                        <i class="fa-solid fa-arrows-spin mr-1"></i> หมุนได้ 360° / ซูมเข้า-ออก
                    </div>
                </div>

                <div class="w-full lg:w-1/3 space-y-5">
                    <div>
                        <span class="text-xs font-bold text-cyan-400 font-mono uppercase">CUSTOM RACKET STUDIO</span>
                        <h2 class="text-3xl font-extrabold text-white mt-1">ออกแบบไม้แบด 3D</h2>
                    </div>

                    <div class="space-y-4 text-xs">
                        <div>
                            <label class="text-slate-300 block mb-1">เลือกโมเดลตั้งต้น</label>
                            <select id="studioRacketSelect" onchange="loadStudioRacket()" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"></select>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="text-slate-300 block mb-1">สีเฟรมไม้</label>
                                <input type="color" id="colFrame" value="#06b6d4" oninput="update3DColors()" class="w-full h-10 rounded-xl bg-slate-950 border border-slate-800 p-1 cursor-pointer">
                            </div>
                            <div>
                                <label class="text-slate-300 block mb-1">สีสายเอ็น</label>
                                <input type="color" id="colStrings" value="#f8fafc" oninput="update3DColors()" class="w-full h-10 rounded-xl bg-slate-950 border border-slate-800 p-1 cursor-pointer">
                            </div>
                        </div>

                        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                            <div class="flex justify-between text-slate-400"><span>รุ่น:</span><span id="specModel" class="text-white font-bold">-</span></div>
                            <div class="flex justify-between text-slate-400"><span>ราคาประมาณ:</span><span id="specPrice" class="text-cyan-400 font-mono font-bold">-</span></div>
                        </div>

                        <button onclick="addStudioToCart()" class="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold py-3 rounded-xl transition font-mono shadow-lg shadow-cyan-500/20">
                            เพิ่มคัสตอมเซตลงตะกร้า
                        </button>
                    </div>
                </div>
            </div>
        </section>

        <!-- AI SMART RACKET MATCHER SECTION -->
        <section id="ai-quiz" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="bg-gradient-to-r from-slate-900 via-cyan-950 to-slate-900 border border-cyan-500/30 rounded-3xl p-6 lg:p-8 space-y-6">
                <div class="border-b border-slate-800 pb-4">
                    <span class="text-xs font-bold text-cyan-400 font-mono tracking-widest uppercase"><i class="fa-solid fa-wand-magic-sparkles mr-1"></i> AI RECOMMENDATION</span>
                    <h2 class="text-2xl font-extrabold text-white mt-1">ระบบวิเคราะห์และแนะนำไม้แบดมินตันอัจฉริยะ</h2>
                    <p class="text-xs text-slate-400 mt-1">เลือกสไตล์และประสบการณ์เพื่อค้นหาไม้ที่เข้ากับคุณที่สุด</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div>
                        <label class="text-slate-300 block mb-2 font-bold">1. สไตล์การเล่นหลัก</label>
                        <select id="aiStyle" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white">
                            <option value="POWER">สายตบหนัก บุกทำแต้ม (POWER)</option>
                            <option value="SPEED">สายความเร็ว หน้าตาข่าย (SPEED)</option>
                            <option value="CONTROL">สายวางลูก คอนโทรลเกม (CONTROL)</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-slate-300 block mb-2 font-bold">2. ระดับประสบการณ์</label>
                        <select id="aiLevel" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white">
                            <option value="BEGINNER">มือใหม่ / เล่นออกกำลังกาย (แนะนำ 20 lbs)</option>
                            <option value="INTERMEDIATE">มือปานกลาง / เล่นชมรมประจำ (แนะนำ 24 lbs)</option>
                            <option value="PRO">มือการแข่งขัน / นักกีฬามืออาชีพ (แนะนำ 27+ lbs)</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-slate-300 block mb-2 font-bold">3. งบประมาณสูงสุด (บาท)</label>
                        <input type="number" id="aiBudget" value="7000" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white">
                    </div>
                </div>

                <button onclick="runAiRecommend()" class="bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 font-bold px-6 py-3 rounded-xl font-mono text-xs transition shadow-lg shadow-cyan-500/20">
                    วิเคราะห์อุปกรณ์ที่เหมาะสม
                </button>

                <div id="aiResultArea" class="hidden space-y-4 pt-4 border-t border-slate-800">
                    <div id="aiTensionNotice" class="text-xs font-mono text-cyan-400 bg-slate-950 p-3 rounded-xl border border-cyan-500/30"></div>
                    <div id="aiMatchedGrid" class="grid grid-cols-1 sm:grid-cols-3 gap-4"></div>
                </div>
            </div>
        </section>

        <!-- COURT RESERVATION SECTION -->
        <section id="courts" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <span class="text-xs font-bold text-emerald-400 font-mono tracking-widest uppercase">BADMINTON COURT BOOKING</span>
                <h2 class="text-3xl font-extrabold text-white mt-1">ระบบจองสนามแบดมินตัน</h2>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Form จองสนาม -->
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 class="text-sm font-bold text-white font-mono flex items-center gap-2">
                        <i class="fa-solid fa-calendar-check text-emerald-400"></i> ทำรายการจองคอร์ด
                    </h3>
                    <form onsubmit="submitCourtBooking(event)" class="space-y-3 text-xs">
                        <div>
                            <label class="text-slate-400 block mb-1">เลือกสนาม (Court)</label>
                            <select id="cbCourt" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                                <option value="1">คอร์ดที่ 1 (PB Studio Court)</option>
                                <option value="2">คอร์ดที่ 2 (Standard Hardcourt)</option>
                                <option value="3">คอร์ดที่ 3 (Standard Hardcourt)</option>
                                <option value="4">คอร์ดที่ 4 (VIP Mat Court)</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">วันที่เล่น</label>
                            <input type="date" id="cbDate" required onchange="fetchCourtBookings()" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">รอบเวลา (Time Slot)</label>
                            <select id="cbTime" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                                <option value="17:00 - 18:00">17:00 - 18:00 น. (250฿)</option>
                                <option value="18:00 - 19:00">18:00 - 19:00 น. (250฿)</option>
                                <option value="19:00 - 20:00">19:00 - 20:00 น. (250฿)</option>
                                <option value="20:00 - 21:00">20:00 - 21:00 น. (250฿)</option>
                            </select>
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">ชื่อผู้จอง</label>
                            <input type="text" id="cbName" required placeholder="ชื่อ-นามสกุล" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">เบอร์โทรศัพท์</label>
                            <input type="tel" id="cbPhone" required placeholder="081-XXX-XXXX" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <button type="submit" class="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-3 rounded-xl font-mono transition shadow-lg shadow-emerald-500/20">
                            ยืนยันการจองสนาม (250 บาท)
                        </button>
                    </form>
                </div>

                <!-- ตารางสถานะสนาม -->
                <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="text-sm font-bold text-white font-mono flex items-center gap-2">
                            <i class="fa-solid fa-border-all text-emerald-400"></i> สถานะการจองประจำวัน
                        </h3>
                        <button onclick="fetchCourtBookings()" class="text-xs text-emerald-400 hover:underline"><i class="fa-solid fa-rotate mr-1"></i>รีเฟรช</button>
                    </div>
                    <div id="courtBookingsList" class="space-y-3 max-h-[350px] overflow-y-auto pr-1"></div>
                </div>
            </div>
        </section>

        <!-- STRINGING QUEUE SECTION -->
        <section id="queue" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <span class="text-xs font-bold text-amber-400 font-mono tracking-widest uppercase">STRINGING SERVICE</span>
                <h2 class="text-3xl font-extrabold text-white mt-1">บริการจองคิวขึ้นเอ็น</h2>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <h3 class="text-sm font-bold text-white font-mono flex items-center gap-2">
                        <i class="fa-solid fa-calendar-plus text-amber-400"></i> ลงทะเบียนขึ้นเอ็น
                    </h3>
                    <form onsubmit="submitQueueBooking(event)" class="space-y-3 text-xs">
                        <div>
                            <label class="text-slate-400 block mb-1">ชื่อผู้รับบริการ</label>
                            <input type="text" id="qName" required placeholder="ชื่อ-นามสกุล" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">เบอร์โทรศัพท์</label>
                            <input type="tel" id="qPhone" required placeholder="081-XXX-XXXX" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-slate-400 block mb-1">ชนิดเอ็น</label>
                                <select id="qString" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                                    <option value="YONEX BG-65">YONEX BG-65</option>
                                    <option value="YONEX BG-80">YONEX BG-80</option>
                                    <option value="VICTOR VBS-66">VICTOR VBS-66</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-slate-400 block mb-1">ความตึง (Lbs)</label>
                                <input type="number" id="qTension" value="24" min="18" max="35" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                            </div>
                        </div>
                        <div>
                            <label class="text-slate-400 block mb-1">วันที่รับบริการ</label>
                            <input type="date" id="qDate" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                        </div>
                        <button type="submit" class="w-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold py-3 rounded-xl font-mono transition shadow-lg shadow-amber-500/20">
                            ยืนยันคิวขึ้นเอ็น
                        </button>
                    </form>
                </div>

                <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                    <div class="flex justify-between items-center">
                        <h3 class="text-sm font-bold text-white font-mono flex items-center gap-2">
                            <i class="fa-solid fa-list-check text-cyan-400"></i> คิวงานปัจจุบัน
                        </h3>
                        <button onclick="fetchQueueList()" class="text-xs text-cyan-400 hover:underline"><i class="fa-solid fa-rotate mr-1"></i>รีเฟรช</button>
                    </div>
                    <div id="queueListContainer" class="space-y-3 max-h-[320px] overflow-y-auto pr-1"></div>
                </div>
            </div>
        </section>

        <!-- MATCHMAKING COMMUNITY SECTION -->
        <section id="community" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <div class="flex justify-between items-end border-b border-slate-800 pb-4">
                <div>
                    <span class="text-xs font-bold text-purple-400 font-mono tracking-widest uppercase">COMMUNITY</span>
                    <h2 class="text-3xl font-extrabold text-white mt-1">บอร์ดหาเพื่อนตีแบด (Matchmaking)</h2>
                </div>
                <button onclick="openCreatePostModal()" class="bg-purple-600 hover:bg-purple-500 text-white font-bold px-4 py-2 rounded-xl text-xs font-mono transition">
                    + ประกาศหาก๊วน
                </button>
            </div>

            <div id="communityPostsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6"></div>
        </section>

        <!-- CATALOG SECTION -->
        <section id="catalog" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-800 pb-6">
                <div>
                    <span class="text-xs font-bold text-cyan-400 font-mono tracking-widest uppercase">STORE CATALOG</span>
                    <h2 class="text-3xl font-extrabold text-white mt-1">สินค้าและอุปกรณ์</h2>
                </div>

                <div class="flex flex-wrap items-center gap-3 w-full sm:w-auto">
                    <input type="text" id="searchInput" oninput="fetchCatalog()" placeholder="ค้นหารุ่น/แบรนด์..." class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 w-full sm:w-48">
                    <select id="categoryFilter" onchange="fetchCatalog()" class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none">
                        <option value="ALL">ประเภททั้งหมด</option>
                        <option value="POWER">POWER (สายบุก)</option>
                        <option value="SPEED">SPEED (สายความเร็ว)</option>
                        <option value="CONTROL">CONTROL (สายคอนโทรล)</option>
                    </select>
                </div>
            </div>

            <div id="catalogGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"></div>
        </section>
    </main>

    <footer class="border-t border-slate-800 bg-slate-950 py-8 text-center text-xs text-slate-500">
        <p>© 2026 SMASH LAB ENTERPRISE V7. All rights reserved.</p>
    </footer>

    <!-- ADMIN MANAGEMENT MODAL -->
    <div id="adminModal" class="fixed inset-0 z-50 glass-modal flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-800 w-full max-w-4xl h-[85vh] rounded-2xl p-6 flex flex-col justify-between">
            <div class="space-y-4 flex-grow overflow-y-auto pr-2">
                <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                    <h3 class="font-bold text-white text-lg font-mono flex items-center gap-2"><i class="fa-solid fa-user-shield text-rose-500"></i> แผงควบคุมผู้ดูแลระบบ (Admin Dashboard)</h3>
                    <button onclick="closeModal('adminModal')" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
                </div>

                <!-- Admin Stats -->
                <div id="adminStatsGrid" class="grid grid-cols-2 sm:grid-cols-4 gap-3"></div>

                <!-- Admin Orders Management -->
                <div class="space-y-3 pt-4 border-t border-slate-800">
                    <h4 class="font-bold text-xs font-mono text-cyan-400 uppercase">รายการสั่งซื้อย้อนหลัง</h4>
                    <div id="adminOrdersList" class="space-y-2"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- CART MODAL -->
    <div id="cartModal" class="fixed inset-0 z-50 glass-modal flex justify-end hidden">
        <div class="w-full max-w-md bg-slate-900 h-full border-l border-slate-800 flex flex-col justify-between p-6 overflow-y-auto">
            <div class="space-y-6">
                <div class="flex justify-between items-center border-b border-slate-800 pb-4">
                    <h3 class="font-bold text-lg text-white font-mono"><i class="fa-solid fa-bag-shopping text-cyan-400 mr-2"></i>ตะกร้าสินค้า</h3>
                    <button onclick="closeModal('cartModal')" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
                </div>
                <div id="cartItemList" class="space-y-3"></div>
            </div>

            <div class="space-y-4 pt-6 border-t border-slate-800">
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-center space-y-2">
                    <div class="text-[11px] text-slate-400 font-mono">สแกนจ่ายผ่าน PromptPay</div>
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=00020101021129370016A000000677010111011300668123456785802TH5303764" class="w-32 h-32 mx-auto rounded-lg border border-slate-700 p-1 bg-white">
                    <div class="text-[10px] text-cyan-400">พร้อมเพย์: 081-234-5678 (SMASH LAB CO., LTD.)</div>
                </div>

                <div class="space-y-1.5">
                    <label class="text-[11px] font-semibold text-slate-400 block">แนบสลิปโอนเงิน</label>
                    <input type="file" id="slipInput" accept="image/*" onchange="handleSlipUpload(event)" class="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:bg-slate-800 file:text-cyan-400">
                </div>

                <div class="space-y-1 text-xs text-slate-400 font-mono">
                    <div class="flex justify-between"><span>รวม:</span><span id="summarySubtotal" class="text-white">0 ฿</span></div>
                    <div class="flex justify-between text-base font-bold text-white pt-2 border-t border-slate-800"><span>สุทธิ:</span><span id="summaryTotal" class="text-cyan-400">0 ฿</span></div>
                </div>

                <button onclick="submitCheckout()" class="w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold py-3.5 rounded-xl font-mono text-xs shadow-lg shadow-cyan-500/20">
                    ยืนยันการสั่งซื้อ
                </button>
            </div>
        </div>
    </div>

    <!-- CREATE MATCH POST MODAL -->
    <div id="postModal" class="fixed inset-0 z-50 glass-modal flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-800 w-full max-w-md rounded-2xl p-6 space-y-4">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 class="font-bold text-white text-base font-mono">ประกาศหาเพื่อนร่วมก๊วน</h3>
                <button onclick="closeModal('postModal')" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <form onsubmit="submitMatchPost(event)" class="space-y-3 text-xs">
                <div>
                    <label class="text-slate-400 block mb-1">สถานที่สนาม</label>
                    <input type="text" id="mpLocation" value="SMASH LAB Badminton Club" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-slate-400 block mb-1">วันที่ตี</label>
                        <input type="date" id="mpDate" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                    </div>
                    <div>
                        <label class="text-slate-400 block mb-1">เวลา</label>
                        <input type="text" id="mpTime" placeholder="18:00 - 20:00 น." required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="text-slate-400 block mb-1">ระดับฝีมือ</label>
                        <select id="mpLevel" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                            <option value="มือใหม่ / ออกกำลังกาย">มือใหม่ / ออกกำลังกาย</option>
                            <option value="มือกลาง / สนุกสนาน">มือกลาง / สนุกสนาน</option>
                            <option value="มือหนัก / เข้มข้น">มือหนัก / เข้มข้น</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-slate-400 block mb-1">ต้องการเพิ่ม (คน)</label>
                        <input type="number" id="mpNeeded" value="2" min="1" max="10" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                    </div>
                </div>
                <div>
                    <label class="text-slate-400 block mb-1">ชื่อผู้ลงประกาศ</label>
                    <input type="text" id="mpName" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                </div>
                <div>
                    <label class="text-slate-400 block mb-1">เบอร์โทรศัพท์</label>
                    <input type="tel" id="mpPhone" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white">
                </div>
                <button type="submit" class="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 rounded-xl font-mono transition">
                    โพสต์ประกาศ
                </button>
            </form>
        </div>
    </div>

    <!-- SPIN MODAL -->
    <div id="spinModal" class="fixed inset-0 z-50 glass-modal flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-800 w-full max-w-sm rounded-2xl p-6 text-center space-y-6">
            <h3 class="font-bold text-white text-base font-mono">วงล้อนำโชคประจำวัน</h3>
            <div class="w-36 h-36 mx-auto rounded-full bg-gradient-to-tr from-amber-500 to-rose-500 flex items-center justify-center text-slate-950 font-black text-2xl shadow-2xl animate-pulse">SPIN!</div>
            <div id="spinResult" class="text-xs text-slate-300 font-mono">กดหมุนเพื่อรับคูปองส่วนลดพิเศษ!</div>
            <button onclick="doSpin()" class="w-full bg-amber-500 text-slate-950 font-bold py-3 rounded-xl font-mono text-xs">หมุนวงล้อเสี่ยงโชค</button>
        </div>
    </div>

    <script>
        const state = { catalog: [], cart: [], activeCoupon: null, slipBase64: "", currentStudioId: null };
        let scene, camera, renderer, racketMesh, frameMesh, stringMesh, controls;

        function showToast(msg, isError = false) {
            const toast = document.getElementById('toast');
            document.getElementById('toastMsg').innerText = msg;
            toast.classList.remove('translate-x-full');
            setTimeout(() => toast.classList.add('translate-x-full'), 3000);
        }

        function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        window.addEventListener('DOMContentLoaded', async () => {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('cbDate').value = today;
            document.getElementById('qDate').value = today;

            await fetchCatalog();
            await fetchQueueList();
            await fetchCourtBookings();
            await fetchCommunityPosts();
            init3DStudio();
        });

        // ADMIN DASHBOARD
        async function openAdminModal() {
            openModal('adminModal');
            const resStats = await fetch('/api/admin/dashboard');
            const stats = await resStats.json();
            
            document.getElementById('adminStatsGrid').innerHTML = `
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                    <div class="text-slate-400">รายได้รวม</div>
                    <div class="text-emerald-400 font-mono font-bold text-sm mt-1">${stats.total_revenue.toLocaleString()} ฿</div>
                </div>
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                    <div class="text-slate-400">ออเดอร์ทั้งหมด</div>
                    <div class="text-white font-mono font-bold text-sm mt-1">${stats.total_orders}</div>
                </div>
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                    <div class="text-slate-400">คิวขึ้นเอ็นค้าง</div>
                    <div class="text-amber-400 font-mono font-bold text-sm mt-1">${stats.pending_queues}</div>
                </div>
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                    <div class="text-slate-400">การจองสนาม</div>
                    <div class="text-cyan-400 font-mono font-bold text-sm mt-1">${stats.total_court_bookings}</div>
                </div>
            `;

            const resOrders = await fetch('/api/admin/orders');
            const orders = await resOrders.json();
            document.getElementById('adminOrdersList').innerHTML = orders.length === 0 ? 
                `<div class="text-xs text-slate-500 font-mono">ไม่มีออเดอร์ในระบบ</div>` :
                orders.map(o => `
                    <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
                        <div>
                            <div class="font-mono font-bold text-white">${o.order_no} (${o.user_email})</div>
                            <div class="text-cyan-400 font-mono">${o.total_price.toLocaleString()} ฿ | สถานะ: ${o.status}</div>
                        </div>
                        <div class="flex gap-1">
                            <button onclick="updateOrderStatus(${o.id}, 'ชำระแล้ว')" class="bg-emerald-600 text-white px-2 py-1 rounded text-[10px]">อนุมัติ</button>
                        </div>
                    </div>
                `).join('');
        }

        async function updateOrderStatus(orderId, status) {
            await fetch(`/api/admin/orders/${orderId}/status`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status })
            });
            showToast("อัปเดตสถานะเรียบร้อย");
            openAdminModal();
        }

        // CATALOG & AI MATCHER
        async function fetchCatalog() {
            const cat = document.getElementById('categoryFilter').value;
            const search = document.getElementById('searchInput').value;
            const res = await fetch(`/api/catalog/products?category=${cat}&search=${encodeURIComponent(search)}`);
            state.catalog = await res.json();
            renderCatalog();
            populateStudioSelect();
        }

        function renderCatalog() {
            document.getElementById('catalogGrid').innerHTML = state.catalog.map(p => `
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between">
                    <div>
                        <img src="${p.image_url}" class="w-full h-44 object-contain p-2 bg-slate-950 rounded-xl mb-3 border border-slate-800">
                        <div class="text-[10px] font-mono font-bold text-cyan-400">${p.brand}</div>
                        <h3 class="text-base font-bold text-white mb-1">${p.model}</h3>
                    </div>
                    <div class="pt-2 border-t border-slate-800 space-y-2">
                        <div class="flex justify-between font-mono text-xs"><span class="text-slate-400">${p.weight_spec}</span><span class="text-white font-bold">${p.price.toLocaleString()} ฿</span></div>
                        <button onclick="addToCart(${p.id})" class="w-full bg-slate-800 hover:bg-cyan-500 hover:text-slate-950 text-cyan-400 font-bold py-2 rounded-xl text-xs font-mono transition">เพิ่มลงตะกร้า</button>
                    </div>
                </div>
            `).join('');
        }

        async function runAiRecommend() {
            const payload = {
                style: document.getElementById('aiStyle').value,
                level: document.getElementById('aiLevel').value,
                budget: document.getElementById('aiBudget').value
            };
            const res = await fetch('/api/catalog/ai-recommend', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            document.getElementById('aiResultArea').classList.remove('hidden');
            document.getElementById('aiTensionNotice').innerText = `💡 ระดับเอ็นที่แนะนำสำหรับระดับฝีมือคุณคือ: ${data.recommended_tension} Lbs`;
            document.getElementById('aiMatchedGrid').innerHTML = data.products.map(p => `
                <div class="bg-slate-950 p-3 rounded-xl border border-cyan-500/30 text-xs">
                    <div class="font-bold text-white">${p.brand} ${p.model}</div>
                    <div class="text-cyan-400 font-mono mt-1">${p.price.toLocaleString()} ฿</div>
                    <button onclick="addToCart(${p.id})" class="w-full mt-2 bg-cyan-500 text-slate-950 font-bold py-1 rounded text-[10px]">เลือกไม้นี้</button>
                </div>
            `).join('');
        }

        // COURT BOOKING LOGIC
        async function submitCourtBooking(e) {
            e.preventDefault();
            const payload = {
                court_no: parseInt(document.getElementById('cbCourt').value),
                booking_date: document.getElementById('cbDate').value,
                time_slot: document.getElementById('cbTime').value,
                user_name: document.getElementById('cbName').value,
                phone: document.getElementById('cbPhone').value
            };
            const res = await fetch('/api/court/book', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast(`จองคอร์ด ${payload.court_no} สำเร็จ!`);
                fetchCourtBookings();
            } else {
                showToast(data.message, true);
            }
        }

        async function fetchCourtBookings() {
            const date = document.getElementById('cbDate').value;
            const res = await fetch(`/api/court/list?date=${date}`);
            const bookings = await res.json();
            
            const container = document.getElementById('courtBookingsList');
            if (bookings.length === 0) {
                container.innerHTML = `<div class="text-center py-6 text-xs text-slate-500 font-mono">ไม่มีการจองในสนามวันนี้</div>`;
                return;
            }
            container.innerHTML = bookings.map(b => `
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
                    <div>
                        <span class="font-bold text-emerald-400 font-mono">คอร์ดที่ ${b.court_no}</span> - <span class="text-white">${b.user_name}</span>
                        <div class="text-slate-400 text-[10px]">${b.time_slot} | โทร: ${b.phone}</div>
                    </div>
                    <span class="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-mono">${b.status}</span>
                </div>
            `).join('');
        }

        // QUEUE LOGIC
        async function submitQueueBooking(e) {
            e.preventDefault();
            const payload = {
                user_name: document.getElementById('qName').value, phone: document.getElementById('qPhone').value,
                string_type: document.getElementById('qString').value, tension_lbs: document.getElementById('qTension').value,
                booking_date: document.getElementById('qDate').value, service_type: 'ขึ้นเอ็นใหม่'
            };
            const res = await fetch('/api/queue/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (data.success) { showToast(`จองคิวสำเร็จ! หมายเลข: ${data.booking.booking_no}`); fetchQueueList(); }
        }

        async function fetchQueueList() {
            const res = await fetch('/api/queue/list');
            const queues = await res.json();
            document.getElementById('queueListContainer').innerHTML = queues.map(q => `
                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
                    <div>
                        <div class="font-mono font-bold text-amber-400">${q.booking_no} - ${q.user_name}</div>
                        <div class="text-slate-400 text-[10px]">${q.string_type} (${q.tension_lbs} Lbs)</div>
                    </div>
                    <span class="bg-slate-800 text-slate-300 px-2 py-1 rounded text-[10px] font-mono">${q.status}</span>
                </div>
            `).join('');
        }

        // COMMUNITY MATCHMAKING
        function openCreatePostModal() { openModal('postModal'); }
        async function submitMatchPost(e) {
            e.preventDefault();
            const payload = {
                court_location: document.getElementById('mpLocation').value, play_date: document.getElementById('mpDate').value,
                play_time: document.getElementById('mpTime').value, level: document.getElementById('mpLevel').value,
                players_needed: document.getElementById('mpNeeded').value, contact_name: document.getElementById('mpName').value,
                phone: document.getElementById('mpPhone').value
            };
            const res = await fetch('/api/community/posts/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (data.success) { closeModal('postModal'); fetchCommunityPosts(); showToast("สร้างประกาศสำเร็จ!"); }
        }

        async function fetchCommunityPosts() {
            const res = await fetch('/api/community/posts');
            const posts = await res.json();
            document.getElementById('communityPostsGrid').innerHTML = posts.map(p => `
                <div class="bg-slate-900 p-4 rounded-2xl border border-slate-800 space-y-3 text-xs">
                    <div class="flex justify-between items-center">
                        <span class="font-bold text-purple-400">${p.court_location}</span>
                        <span class="bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded text-[10px]">ขาด ${p.players_needed} คน</span>
                    </div>
                    <div class="text-white font-semibold">${p.play_date} (${p.play_time})</div>
                    <div class="text-slate-400">ระดับ: ${p.level}</div>
                    <div class="text-[11px] text-slate-500">ติดต่อ: ${p.contact_name} (${p.phone})</div>
                    <button onclick="alert('ส่งข้อความเข้าร่วมก๊วนเรียบร้อย!')" class="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 rounded-xl transition font-mono">ขอเข้าร่วมก๊วน</button>
                </div>
            `).join('');
        }

        // THREE.JS 3D STUDIO
        function init3DStudio() {
            const container = document.getElementById('racket3dContainer');
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 15);

            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            scene.add(new THREE.AmbientLight(0xffffff, 0.8));
            const dirLight = new THREE.DirectionalLight(0xffffff, 1);
            dirLight.position.set(5, 10, 7);
            scene.add(dirLight);

            racketMesh = new THREE.Group();
            const frameGeo = new THREE.TorusGeometry(2.5, 0.12, 16, 100);
            frameGeo.scale(1, 1.3, 1);
            frameMesh = new THREE.Mesh(frameGeo, new THREE.MeshStandardMaterial({ color: 0x06b6d4, metalness: 0.5 }));
            frameMesh.position.y = 2.5;
            racketMesh.add(frameMesh);

            const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 4.5), new THREE.MeshStandardMaterial({ color: 0x334155 }));
            shaft.position.y = -1;
            racketMesh.add(shaft);

            stringMesh = new THREE.Mesh(new THREE.PlaneGeometry(3.5, 5), new THREE.MeshBasicMaterial({ color: 0xf8fafc, wireframe: true, opacity: 0.4, transparent: true }));
            stringMesh.position.y = 2.5;
            racketMesh.add(stringMesh);

            scene.add(racketMesh);
            function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
            animate();
        }

        function populateStudioSelect() {
            const select = document.getElementById('studioRacketSelect');
            select.innerHTML = state.catalog.map(p => `<option value="${p.id}">${p.brand} - ${p.model}</option>`).join('');
            if (state.catalog.length > 0) loadStudioRacket();
        }

        function loadStudioRacket() {
            const id = parseInt(document.getElementById('studioRacketSelect').value);
            const item = state.catalog.find(p => p.id === id);
            if (!item) return;
            state.currentStudioId = item.id;
            document.getElementById('specModel').innerText = `${item.brand} ${item.model}`;
            document.getElementById('specPrice').innerText = `${item.price.toLocaleString()} ฿`;
            document.getElementById('colFrame').value = item.color_hex || '#06b6d4';
            update3DColors();
        }

        function update3DColors() {
            if (!frameMesh || !stringMesh) return;
            frameMesh.material.color.set(document.getElementById('colFrame').value);
            stringMesh.material.color.set(document.getElementById('colStrings').value);
        }

        function addStudioToCart() {
            if (!state.currentStudioId) return;
            addToCart(state.currentStudioId, `(Custom Color: ${document.getElementById('colFrame').value})`);
        }

        // CART & SPIN
        function addToCart(productId, extra = "") {
            const product = state.catalog.find(p => p.id === productId);
            if (!product) return;
            const existing = state.cart.find(c => c.id === productId && c.extra === extra);
            if (existing) existing.quantity++; else state.cart.push({ ...product, quantity: 1, extra });
            document.getElementById('cartCountBadge').innerText = state.cart.reduce((s, i) => s + i.quantity, 0);
            showToast(`เพิ่ม ${product.model} ลงตะกร้าเรียบร้อย`);
        }

        function openCartModal() { renderCartItems(); openModal('cartModal'); }
        function renderCartItems() {
            const list = document.getElementById('cartItemList');
            if (state.cart.length === 0) { list.innerHTML = `<div class="text-center py-8 text-xs text-slate-500 font-mono">ไม่มีสินค้าในตะกร้า</div>`; return; }
            list.innerHTML = state.cart.map(i => `
                <div class="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                    <div>
                        <div class="font-bold text-white">${i.brand} ${i.model}</div>
                        <div class="text-slate-400 font-mono">${i.price.toLocaleString()} ฿ x ${i.quantity}</div>
                    </div>
                </div>
            `).join('');
            const total = state.cart.reduce((s, i) => s + i.price * i.quantity, 0);
            document.getElementById('summarySubtotal').innerText = `${total.toLocaleString()} ฿`;
            document.getElementById('summaryTotal').innerText = `${total.toLocaleString()} ฿`;
        }

        function openSpinModal() { openModal('spinModal'); }
        async function doSpin() {
            const res = await fetch('/api/catalog/spin-wheel', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                document.getElementById('spinResult').innerHTML = `<span class="text-amber-400 font-bold">${data.prize.label}</span><br>โค้ด: <b>${data.prize.code}</b>`;
            }
        }

        function handleSlipUpload(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(evt) { state.slipBase64 = evt.target.result; }
            reader.readAsDataURL(file);
        }

        async function submitCheckout() {
            if (state.cart.length === 0) return;
            const payload = { items: state.cart, slip_image: state.slipBase64 };
            const res = await fetch('/api/orders/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (data.success) { showToast(`สั่งซื้อสำเร็จ! ออเดอร์: ${data.order.order_no}`); state.cart = []; closeModal('cartModal'); }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ==============================================================================
# 6. SEED DATABASE & MAIN RUNNER
# ==============================================================================
def seed_database():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(email="admin@smashlab.com").first():
            db.session.add(User(name="System Admin", email="admin@smashlab.com", password_hash=generate_password_hash("admin1234"), role="admin"))

        if Product.query.count() == 0:
            products = [
                Product(brand="YONEX", model="ASTROX 88D PRO", category="POWER", price=6290, color_hex="#f59e0b", badge="HOT", description="ไม้ตบสายพลังยอดนิยม พลังทำลายล้างสูง", image_url=VectorAssetService.generate_racket_svg("YONEX", "ASTROX 88D", "POWER", "#f59e0b")),
                Product(brand="VICTOR", model="THRUSTER RYUGA II", category="POWER", price=5890, color_hex="#ef4444", badge="BEST", description="ไม้บุกสายโหด ตอบสนองเกมตบได้รวดเร็ว", image_url=VectorAssetService.generate_racket_svg("VICTOR", "RYUGA II", "POWER", "#ef4444")),
                Product(brand="YONEX", model="NANOFLARE 800 PRO", category="SPEED", price=6190, color_hex="#06b6d4", badge="NEW", description="ไม้สายสปีด ดาดลูกและเล่นหน้าตาข่ายยอดเยี่ยม", image_url=VectorAssetService.generate_racket_svg("YONEX", "NANOFLARE 800", "SPEED", "#06b6d4")),
                Product(brand="LI-NING", model="HALBERTEC 8000", category="CONTROL", price=6090, color_hex="#10b981", badge="POPULAR", description="ไม้สายคอนโทรล วางลูกแม่นยำและเสถียรสูง", image_url=VectorAssetService.generate_racket_svg("LI-NING", "HALBERTEC", "CONTROL", "#10b981"))
            ]
            db.session.add_all(products)

        if MatchmakingPost.query.count() == 0:
            today_str = datetime.now().strftime('%Y-%m-%d')
            db.session.add(MatchmakingPost(court_location="SMASH LAB Court 2", play_date=today_str, play_time="19:00 - 21:00 น.", level="มือใหม่ / ออกกำลังกาย", players_needed=2, contact_name="คุณตั้ม", phone="081-234-5678", note="เล่นสนุกๆ เอาเหงื่อครับ"))

        db.session.commit()

if __name__ == '__main__':
    seed_database()
    print("==================================================")
    print(" SMASH LAB ENTERPRISE V7 RUNNING SUCCESSFULLY")
    print(" URL: http://127.0.0.1:5000")
    print("==================================================")
    Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
 