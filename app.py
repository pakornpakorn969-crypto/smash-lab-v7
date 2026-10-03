import os
import datetime
import uuid
import webbrowser
from threading import Timer
from flask import Flask, render_template_string, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ==========================================
# INITIALIZE FLASK APP & DATABASE
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smash-lab-v7-pro-max-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smashlab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB Max
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# Helper Function: File Upload Handler
def save_uploaded_file(file_obj):
    if not file_obj or file_obj.filename == '':
        return None
    filename = secure_filename(file_obj.filename)
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_obj.save(filepath)
    return f"/static/uploads/{unique_name}"

# Helper Function: Line Notify / Webhook Simulator
def send_system_notification(title, message):
    log_msg = f"🔔 [NOTIFICATION - {title}] {message} ({datetime.datetime.now().strftime('%H:%M:%S')})"
    print(log_msg)

# ==========================================
# 1. DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    points = db.Column(db.Integer, default=500)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Racket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    model_name = db.Column(db.String(120), nullable=False)
    series = db.Column(db.String(80))
    price = db.Column(db.Float, nullable=False)
    weight = db.Column(db.String(20), default='4U')
    balance = db.Column(db.String(50), default='Head Heavy')
    stiffness = db.Column(db.String(50), default='Medium')
    max_tension = db.Column(db.Integer, default=28)
    stock = db.Column(db.Integer, default=10)
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(500), default='https://images.unsplash.com/photo-1626225967045-94408422617d?w=600&auto=format&fit=crop&q=80')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    racket_id = db.Column(db.Integer, db.ForeignKey('racket.id'), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=10)
    icon = db.Column(db.String(10), default='🏸')
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(500), default='https://images.unsplash.com/photo-1613918431703-863a8a3891d4?w=600&auto=format&fit=crop&q=80')

class StringingQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    racket = db.Column(db.String(120), nullable=False)
    spec = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='รอขึ้นเอ็น')
    ticket_code = db.Column(db.String(50), default=lambda: f"ST-{uuid.uuid4().hex[:6].upper()}")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    court_name = db.Column(db.String(80), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    time_slot = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    booking_code = db.Column(db.String(50), default=lambda: f"BK-{uuid.uuid4().hex[:6].upper()}")

class CommunityGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    time_slot = db.Column(db.String(80), nullable=False)
    level = db.Column(db.String(80), nullable=False)
    members_count = db.Column(db.Integer, default=1)
    max_members = db.Column(db.Integer, default=6)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    items_summary = db.Column(db.Text, nullable=False)
    slip_filename = db.Column(db.String(255))
    status = db.Column(db.String(50), default='รอตรวจสอบสลิป')
    order_code = db.Column(db.String(50), default=lambda: f"ORD-{uuid.uuid4().hex[:6].upper()}")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ==========================================
# 2. SEED INITIAL DATA
# ==========================================
def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@smashlab.com', role='admin', points=9999)
            admin.set_password('admin123')
            db.session.add(admin)

        if not User.query.filter_by(username='somchai').first():
            user = User(username='somchai', email='somchai@gmail.com', role='user', points=500)
            user.set_password('123456')
            db.session.add(user)

        if Racket.query.count() == 0:
            db.session.add_all([
                Racket(brand='YONEX', model_name='ASTROX 88D PRO', series='Astrox', price=6290, weight='4U', balance='Head Heavy', stiffness='Extra Stiff', max_tension=28, stock=8, description='ไม้ตบหนัก สายบุกตบจากแดนหลัง พลังทำลายล้างสูง', image_url='https://images.unsplash.com/photo-1626225967045-94408422617d?w=600&auto=format&fit=crop&q=80'),
                Racket(brand='YONEX', model_name='NANOFLARE 1000 Z', series='Nanoflare', price=6590, weight='4U', balance='Head Light', stiffness='Extra Stiff', max_tension=28, stock=5, description='ความเร็วลูกสูงสุด สแมชและสวนกลับได้รวดเร็วปานสายฟ้า', image_url='https://images.unsplash.com/photo-1521537634581-0dced2efa2a3?w=600&auto=format&fit=crop&q=80'),
                Racket(brand='YONEX', model_name='ARCSABER 11 PRO', series='Arcsaber', price=6190, weight='4U', balance='Even Balance', stiffness='Stiff', max_tension=27, stock=6, description='ไม้คอนโทรลระดับตำนาน การตัดลูกและวางลูกแม่นยำที่สุด', image_url='https://images.unsplash.com/photo-1613918431703-863a8a3891d4?w=600&auto=format&fit=crop&q=80'),
                Racket(brand='VICTOR', model_name='THRUSTER RYUGA II', series='Thruster', price=5890, weight='4U', balance='Head Heavy', stiffness='Stiff', max_tension=31, stock=7, description='ไม้ประจำตัว Lee Zii Jia ตบหนัก ก้านดีด คอนโทรลง่าย', image_url='https://images.unsplash.com/photo-1627042633145-b780d842ba45?w=600&auto=format&fit=crop&q=80'),
                Racket(brand='VICTOR', model_name='AURASPEED 90K II', series='Auraspeed', price=5690, weight='4U', balance='Head Light', stiffness='Stiff', max_tension=30, stock=5, description='เน้นเกมเร็ว สวนกลับลูกดาด ดักตีหน้าเน็ตได้อย่างยอดเยี่ยม', image_url='https://images.unsplash.com/photo-1530915534664-4ac6423ca938?w=600&auto=format&fit=crop&q=80'),
                Racket(brand='LI-NING', model_name='AXFORCE 90 DRAGON', series='Axforce', price=6690, weight='4U', balance='Head Heavy', stiffness='Stiff', max_tension=30, stock=4, description='ไม้สายรุกระดับท็อป เทคโนโลยีคาร์บอนเกรดการบิน', image_url='https://images.unsplash.com/photo-1622163642988-1ea32b0da6b9?w=600&auto=format&fit=crop&q=80')
            ])

        if Product.query.count() == 0:
            db.session.add_all([
                Product(name='ลูกแบดมินตัน RSL Silver (1 หลอด)', price=780, stock=15, icon='🏸', description='ลูกขนไก่เกรดแข่งขัน ทนทาน วิถีแม่นยำ', image_url='https://images.unsplash.com/photo-1613918431703-863a8a3891d4?w=600&auto=format&fit=crop&q=80'),
                Product(name='รองเท้าแบด YONEX POWER CUSHION', price=4290, stock=4, icon='👟', description='ซับแรงกระแทกเยี่ยม ยึดเกาะพื้นสนามดีเยี่ยม', image_url='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&auto=format&fit=crop&q=80'),
                Product(name='กริปยางพันด้าม VS Overgrip (แพ็ค 3)', price=120, stock=25, icon='🎗️', description='กริปพันด้ามแบบเหนียว นุ่ม ซับเหงื่อได้ดี', image_url='https://images.unsplash.com/photo-1521537634581-0dced2efa2a3?w=600&auto=format&fit=crop&q=80')
            ])

        if CommunityGroup.query.count() == 0:
            db.session.add_all([
                CommunityGroup(host_name='โค้ชต้อม', title='ก๊วน SMASH HARD', location='สนาม Smash BKK', time_slot='วันนี้ 19:00 - 21:00 น.', level='มือกลาง - มือหนัก', members_count=4, max_members=6),
                CommunityGroup(host_name='คุณแจ็ค', title='ก๊วนมือใหม่ เน้นออกกำลังกาย', location='สนาม Winner', time_slot='พรุ่งนี้ 18:00 - 20:00 น.', level='มือใหม่', members_count=5, max_members=6)
            ])

        db.session.commit()

init_db()

# ==========================================
# 3. HTML TEMPLATE WITH SINGLE-PAGE APP LOGIC
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMASH LAB V7 PRO MAX - Complete Badminton Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        * { font-family: 'Kanit', sans-serif; }
        body { background-color: #f8fafc; color: #0f172a; overflow-x: hidden; }
        .glow-cyan-text { color: #0284c7; }
        .btn-glow-cyan {
            background-color: #0284c7; color: #ffffff;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .btn-glow-cyan:hover {
            background-color: #0369a1;
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5);
            transform: translateY(-1px);
        }
        .sidebar-active {
            background: linear-gradient(90deg, rgba(2, 132, 199, 0.12) 0%, rgba(2, 132, 199, 0.02) 100%);
            border-left: 4px solid #0284c7;
            color: #0284c7 !important;
            font-weight: 700;
        }
        .toast-notification { animation: slideIn 0.3s ease-out forwards; }
        @keyframes slideIn {
            from { transform: translateY(-100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @media print {
            body * { visibility: hidden; }
            #printable-receipt-modal, #printable-receipt-modal * { visibility: visible; }
            #printable-receipt-modal { position: absolute; left: 0; top: 0; width: 100%; }
            .no-print { display: none !important; }
        }
    </style>
</head>
<body class="min-h-screen antialiased selection:bg-sky-500 selection:text-white bg-slate-50">

    <div id="toast-container" class="fixed top-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"></div>

    <!-- LANDING PAGE -->
    <div id="landing-page" class="flex flex-col min-h-screen justify-between transition-all duration-300">
        <header class="w-full px-8 py-4 flex justify-between items-center border-b border-slate-200 bg-white/90 backdrop-blur-md fixed top-0 z-40 shadow-sm">
            <div class="flex items-center gap-3 cursor-pointer" onclick="showLanding()">
                <div class="w-10 h-10 bg-sky-600 rounded-xl flex items-center justify-center font-black text-white text-xl shadow-md">SL</div>
                <div class="flex items-center gap-2">
                    <span class="text-2xl font-black tracking-wider text-slate-900">SMASH <span class="text-sky-600">LAB</span></span>
                    <span class="text-[10px] font-black px-2 py-0.5 rounded bg-sky-100 text-sky-700 border border-sky-200">V7 PRO MAX</span>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <div id="header-user-info" class="hidden flex items-center gap-3">
                    <button onclick="openProfileModal()" class="flex items-center gap-2 px-4 py-1.5 bg-slate-100 border border-slate-200 rounded-full text-xs font-bold text-slate-700 hover:bg-slate-200">
                        <span id="user-display-tag">👤 คุณสมชาย (500 pts)</span>
                    </button>
                    <button onclick="logout()" class="px-3 py-1.5 text-xs text-rose-600 border border-rose-200 rounded-full hover:bg-rose-50 font-bold">ออกจากระบบ</button>
                </div>
                <div id="header-auth-btns" class="flex items-center gap-3">
                    <button onclick="openModal('login-modal')" class="px-6 py-2 text-xs font-bold text-sky-600 border border-sky-300 bg-sky-50 rounded-full hover:bg-sky-100 transition">เข้าสู่ระบบ</button>
                    <button onclick="openModal('register-modal')" class="px-6 py-2 text-xs font-bold bg-sky-600 text-white rounded-full hover:bg-sky-700 shadow-md transition">สมัครสมาชิก</button>
                </div>
            </div>
        </header>

        <main class="pt-36 pb-16 px-6 max-w-6xl mx-auto flex flex-col items-center text-center my-auto">
            <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-xs font-semibold mb-8 shadow-sm">
                <span>⚡ Real File Upload • Court Overlap Protect • Dynamic PromptPay • Printable Receipt</span>
            </div>
            <h1 class="text-4xl md:text-6xl font-black tracking-tight mb-6 leading-[1.25] text-slate-900">
                ระบบจัดการแบดมินตันครบวงจร<br>
                สมบูรณ์แบบระดับองค์กร <span class="glow-cyan-text font-black">SMASH LAB V7 PRO MAX</span>
            </h1>
            <p class="text-slate-600 text-sm md:text-base max-w-2xl mb-10 leading-relaxed font-normal">
                อัปโหลดไฟล์สลิปจริง ป้องกันการจองสนามเวลาซ้ำ คูปองแต้ม พิมพ์ใบเสร็จ<br class="hidden md:block">
                พร้อมระบบจัดการหลังบ้าน คิวขึ้นเอ็น และก๊วนแบดมินตัน
            </p>
            <div class="flex justify-center gap-4 mb-16">
                <button onclick="showApp('rackets')" class="btn-glow-cyan px-8 py-3.5 rounded-full text-sm font-extrabold flex items-center gap-2 shadow-lg">
                    <span>🏸 เข้าสู่ระบบใช้งาน</span>
                </button>
                <button onclick="showApp('studio')" class="px-8 py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-full text-sm font-bold transition">
                    <span>🎨 3D Custom Studio</span>
                </button>
            </div>
        </main>
    </div>

    <!-- WORKSPACE APP VIEW -->
    <div id="app-page" class="hidden flex min-h-screen bg-slate-50">
        <!-- SIDEBAR -->
        <aside class="w-64 bg-white border-r border-slate-200 flex flex-col justify-between shrink-0 fixed top-0 bottom-0 left-0 z-30 shadow-sm">
            <div>
                <div class="p-5 border-b border-slate-100">
                    <div class="flex items-center gap-3 cursor-pointer" onclick="showLanding()">
                        <div class="w-9 h-9 bg-sky-600 rounded-xl flex items-center justify-center font-black text-white text-lg shadow-sm">SL</div>
                        <div>
                            <div class="text-base font-black tracking-wider text-slate-900 leading-none">SMASH <span class="text-sky-600">LAB</span></div>
                            <span class="text-[10px] text-sky-600 font-extrabold tracking-wider block mt-1">V7 PRO MAX</span>
                        </div>
                    </div>
                </div>
                <nav id="sidebar-nav" class="mt-4 px-3 space-y-1">
                    <div class="px-3 py-1.5 text-[11px] font-extrabold text-slate-400 uppercase tracking-wider">เมนูหลัก</div>
                    <button onclick="switchTab('rackets', this)" id="nav-rackets" class="w-full sidebar-active flex items-center gap-3 px-3 py-2.5 text-xs font-bold transition text-left rounded-lg"><span class="text-base">🏸</span> ไม้แบดมินตัน (RACKETS)</button>
                    <button onclick="switchTab('studio', this)" id="nav-studio" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">🎨</span> 3D STUDIO</button>
                    <button onclick="switchTab('aimatcher', this)" id="nav-aimatcher" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">🤖</span> AI MATCHER</button>
                    <button onclick="switchTab('booking', this)" id="nav-booking" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">📅</span> จองสนาม</button>
                    <button onclick="switchTab('stringing', this)" id="nav-stringing" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">🧵</span> คิวขึ้นเอ็น</button>
                    <button onclick="switchTab('community', this)" id="nav-community" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">👥</span> ก๊วนแบด</button>
                    <button onclick="switchTab('catalog', this)" id="nav-catalog" class="w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg"><span class="text-base">🛍</span> CATALOG & STOCK</button>
                    <button onclick="switchTab('admin', this)" id="nav-admin" class="w-full hidden flex items-center gap-3 px-3 py-2.5 text-amber-700 bg-amber-50 hover:bg-amber-100 text-xs font-bold transition text-left rounded-lg border border-amber-200 mt-2"><span class="text-base">👑</span> ADMIN DASHBOARD</button>
                </nav>
            </div>
            <div class="p-3 border-t border-slate-100 space-y-2 bg-slate-50/50">
                <button onclick="openProfileModal()" class="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-bold transition"><span>👤</span> โปรไฟล์ / ประวัติการสั่งซื้อ</button>
                <button onclick="switchTab('cart', this)" id="nav-cart" class="w-full flex items-center justify-between px-3 py-2.5 rounded-xl bg-white text-slate-700 hover:bg-slate-100 text-xs transition border border-slate-200 shadow-sm">
                    <span class="flex items-center gap-2 font-semibold">🛒 ตะกร้าสินค้า</span>
                    <span id="cart-badge-count" class="bg-sky-600 text-white text-[10px] font-black w-4 h-4 rounded-full flex items-center justify-center">0</span>
                </button>
                <button onclick="showLanding()" class="w-full text-center text-[11px] text-slate-400 hover:text-slate-600 pt-1 transition block">← ออกสู่หน้าปก</button>
            </div>
        </aside>

        <!-- MAIN CANVAS -->
        <main class="ml-64 flex-1 p-8 min-h-screen bg-slate-50">
            
            <!-- VIEW 1: RACKETS -->
            <div id="view-rackets" class="view-content space-y-6">
                <header class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-200 gap-4">
                    <div>
                        <h1 class="text-2xl font-black text-slate-900 tracking-wide">🏸 คลังไม้แบดมินตันรวมทุกแบรนด์</h1>
                        <p class="text-xs font-medium text-slate-500 mt-0.5">ค้นหา เช็กสเปกเชิงลึก ดูรูปภาพ และสั่งซื้อไม้แบดมินตันแท้</p>
                    </div>
                    <button onclick="openModal('add-racket-modal')" class="btn-glow-cyan px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 shrink-0">
                        <span>➕ เพิ่มไม้แบดมินตัน</span>
                    </button>
                </header>

                <div class="flex flex-col md:flex-row gap-4 justify-between items-center bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                    <div class="flex flex-wrap gap-2" id="brand-filter-group">
                        <button onclick="filterBrand('ALL', this)" class="brand-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-sky-600 text-white shadow-sm">ทั้งหมด</button>
                        <button onclick="filterBrand('YONEX', this)" class="brand-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200">YONEX</button>
                        <button onclick="filterBrand('VICTOR', this)" class="brand-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200">VICTOR</button>
                        <button onclick="filterBrand('LI-NING', this)" class="brand-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200">LI-NING</button>
                    </div>
                    <div class="w-full md:w-64">
                        <input type="text" id="racket-search-input" onkeyup="searchRackets()" placeholder="🔍 ค้นหารุ่น เช่น Astrox, Ryuga..." class="w-full bg-slate-50 border border-slate-300 text-slate-800 rounded-xl p-2.5 text-xs focus:outline-none focus:border-sky-500">
                    </div>
                </div>

                <div id="rackets-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>
            </div>

            <!-- VIEW 2: 3D STUDIO -->
            <div id="view-studio" class="view-content hidden space-y-6">
                <header class="flex justify-between items-center pb-4 border-b border-slate-200">
                    <div>
                        <h1 class="text-2xl font-black text-slate-900 tracking-wide">3D Interactive Customizer</h1>
                        <p class="text-[11px] font-bold text-slate-400 mt-0.5">POWERED BY THREE.JS WEBGL ENGINE</p>
                    </div>
                </header>
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div class="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-4 flex flex-col justify-between min-h-[500px] relative shadow-sm">
                        <div class="z-10 flex justify-between items-center mb-2">
                            <span class="bg-slate-100 text-slate-700 border border-slate-200 px-3 py-1 rounded-xl text-xs font-semibold flex items-center gap-2">
                                <span class="text-sky-600">🖱️</span> หมุน 360° / สโครลเพื่อซูม
                            </span>
                            <button onclick="reset3DCamera()" class="text-xs bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded-lg text-slate-600 font-bold">🎯 รีเซ็ตมุมมอง</button>
                        </div>
                        <div id="three-canvas-container" class="w-full h-[420px] bg-gradient-to-b from-slate-900 to-slate-800 rounded-xl flex items-center justify-center relative overflow-hidden"></div>
                    </div>
                    
                    <div class="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm space-y-4">
                        <div class="space-y-4">
                            <div>
                                <label class="text-xs text-slate-700 font-bold block mb-1">โมเดลไม้ตั้งต้น</label>
                                <select id="model-select" onchange="update3DModelPrice(this)" class="w-full bg-slate-50 border border-slate-300 text-slate-800 rounded-xl p-2.5 text-xs font-semibold">
                                    <option value="6290">YONEX - ASTROX 88D PRO</option>
                                    <option value="5890">VICTOR - THRUSTER RYUGA II</option>
                                    <option value="6690">LI-NING - AXFORCE 90 DRAGON</option>
                                </select>
                            </div>
                            <div class="grid grid-cols-3 gap-3">
                                <div>
                                    <label class="text-[11px] text-slate-700 font-bold block mb-1">สีเฟรม 3D</label>
                                    <input type="color" id="frame-color-input" value="#0284c7" onchange="update3DFrameColor(this.value)" class="w-full h-9 rounded-xl border border-slate-300 cursor-pointer">
                                </div>
                                <div>
                                    <label class="text-[11px] text-slate-700 font-bold block mb-1">สีเอ็น 3D</label>
                                    <input type="color" id="string-color-input" value="#ffffff" onchange="update3DStringColor(this.value)" class="w-full h-9 rounded-xl border border-slate-300 cursor-pointer">
                                </div>
                                <div>
                                    <label class="text-[11px] text-slate-700 font-bold block mb-1">สีด้ามจับ 3D</label>
                                    <input type="color" id="grip-color-input" value="#334155" onchange="update3DGripColor(this.value)" class="w-full h-9 rounded-xl border border-slate-300 cursor-pointer">
                                </div>
                            </div>
                            <div class="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-1.5">
                                <div class="flex justify-between text-xs"><span class="text-slate-500">รุ่นที่คัสตอม:</span><span id="display-model-name" class="font-bold text-slate-900">YONEX ASTROX 88D PRO</span></div>
                                <div class="flex justify-between text-xs pt-2 border-t border-slate-200"><span class="text-slate-500">ราคาสรุป:</span><span id="display-price" class="font-black text-sky-600 text-xl">6,290 ฿</span></div>
                            </div>
                        </div>
                        <button onclick="addCustomRacketToCart()" class="w-full btn-glow-cyan py-3.5 rounded-xl font-bold text-xs">เพิ่มคัสตอม 3D ลงตะกร้า</button>
                    </div>
                </div>
            </div>

            <!-- VIEW 3: AI MATCHER -->
            <div id="view-aimatcher" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">🤖 AI Racket Matcher</h1></header>
                <div class="bg-white p-6 rounded-2xl border border-slate-200 max-w-2xl mx-auto space-y-5 shadow-sm">
                    <div>
                        <label class="text-xs text-slate-700 font-bold block mb-2">1. สไตล์การเล่นหลักของคุณ</label>
                        <select id="ai-style" class="w-full bg-slate-50 border border-slate-300 text-slate-800 rounded-xl p-3 text-xs">
                            <option value="smash">เน้นเกมตบหนัก รุกต่อเนื่อง (Power Smash)</option>
                            <option value="control">เน้นคอนโทรล วางลูกแม่นยำ (Control & Placement)</option>
                            <option value="speed">เน้นดักตบหน้าเน็ต เกมไว (Speed & Fast Drive)</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs text-slate-700 font-bold block mb-2">2. งบประมาณที่ตั้งไว้</label>
                        <select id="ai-budget" class="w-full bg-slate-50 border border-slate-300 text-slate-800 rounded-xl p-3 text-xs">
                            <option value="high">มากกว่า 5,000 บาท (ระดับ Flagship/Pro)</option>
                            <option value="low">ต่ำกว่า 2,500 บาท (เริ่มต้น/คุ้มค่า)</option>
                        </select>
                    </div>
                    <button onclick="calculateAIMatch()" class="w-full btn-glow-cyan py-3 rounded-xl font-bold text-xs">⚡ คำนวณหาไม้ที่เหมาะกับคุณ</button>
                    <div id="ai-result" class="hidden mt-4 p-4 bg-sky-50 border border-sky-200 rounded-xl space-y-2"></div>
                </div>
            </div>

            <!-- VIEW 4: BOOKING WITH OVERLAP PROTECTION -->
            <div id="view-booking" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">📅 จองสนามแบดมินตัน (ระบบป้องกันการจองซ้ำ)</h1></header>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">เลือกสนามและเวลารับบริการ</h2>
                        <select id="booking-court" onchange="checkBookedSlots()" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                            <option value="Smash Lab Court A (Rubber)">Smash Lab Court A (ยางแข่งขัน)</option>
                            <option value="Smash Lab Court B (Rubber)">Smash Lab Court B (ยางแข่งขัน)</option>
                            <option value="Smash Lab Court C (Wood)">Smash Lab Court C (พื้นไม้ปาร์เก้)</option>
                        </select>
                        <input type="date" id="booking-date" onchange="checkBookedSlots()" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                        <select id="booking-time" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                            <option value="17:00 - 18:00">17:00 - 18:00 (200 ฿)</option>
                            <option value="18:00 - 19:00">18:00 - 19:00 (250 ฿)</option>
                            <option value="19:00 - 20:00">19:00 - 20:00 (250 ฿)</option>
                            <option value="20:00 - 21:00">20:00 - 21:00 (250 ฿)</option>
                        </select>
                        <button onclick="submitBooking()" class="w-full btn-glow-cyan py-3 rounded-xl font-bold text-xs">ยืนยันการจองสนาม</button>
                    </div>
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">รายการจองสนามทั้งหมด</h2>
                        <div id="booking-list" class="space-y-3 text-xs text-slate-600"></div>
                    </div>
                </div>
            </div>

            <!-- VIEW 5: STRINGING QUEUE -->
            <div id="view-stringing" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">🧵 คิวขึ้นเอ็นไม้แบดมินตัน</h1></header>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">ส่งไม้ขึ้นเอ็น</h2>
                        <input type="text" id="stringing-racket" placeholder="ชื่อรุ่นไม้ (เช่น Yonex Astrox 88D)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                        <input type="text" id="stringing-spec" placeholder="สเปกเอ็น & ความตึง (เช่น BG65 26 LBS สีขาว)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                        <button onclick="submitStringing()" class="w-full btn-glow-cyan py-3 rounded-xl font-bold text-xs">บันทึกคิวขึ้นเอ็น</button>
                    </div>
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">สถานะคิวขึ้นเอ็นทั้งหมด</h2>
                        <div id="stringing-list" class="space-y-3 text-xs text-slate-600"></div>
                    </div>
                </div>
            </div>

            <!-- VIEW 6: COMMUNITY -->
            <div id="view-community" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">👥 ก๊วนแบดมินตัน หาเพื่อนตีแบด</h1></header>
                <div id="community-grid" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
            </div>

            <!-- VIEW 7: CATALOG -->
            <div id="view-catalog" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">🛍 อุปกรณ์เสริม & สินค้าทั่วไป</h1></header>
                <div id="product-grid" class="grid grid-cols-1 md:grid-cols-3 gap-6"></div>
            </div>

            <!-- VIEW 8: CART & FILE UPLOAD CHECKOUT -->
            <div id="view-cart" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200"><h1 class="text-2xl font-black text-slate-900">🛒 ตะกร้าสินค้าและการชำระเงิน</h1></header>
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div class="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">รายการสินค้าในตะกร้า</h2>
                        <div id="cart-items" class="divide-y divide-slate-100"></div>
                        <div class="flex justify-between items-center pt-4 font-bold text-slate-900">
                            <span>ราคารวมทั้งหมด:</span>
                            <span id="cart-total-price" class="text-sky-600 text-xl font-black">0 ฿</span>
                        </div>
                    </div>
                    
                    <div class="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">📱 ชำระเงินผ่าน Dynamic PromptPay</h2>
                        <div class="bg-slate-50 p-4 rounded-xl text-center space-y-3 border border-slate-200">
                            <img id="qr-code-img" src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=PROMPTPAY" class="w-40 h-40 mx-auto rounded-lg shadow-sm">
                            <div class="text-xs font-bold text-slate-700">พร้อมเพย์: 089-999-9999 (สแมช LAB จำกัด)</div>
                        </div>
                        <div>
                            <label class="text-xs font-bold text-slate-700 block mb-1">แนบไฟล์ภาพสลิปโอนเงินจริง (รูปจากเครื่อง)</label>
                            <input type="file" id="slip-file-input" accept="image/*" class="w-full bg-slate-50 border border-slate-300 p-2 rounded-xl text-xs">
                        </div>
                        <button onclick="checkoutCartWithFile()" class="w-full btn-glow-cyan py-3.5 rounded-xl font-bold text-xs">ยืนยันการชำระเงิน</button>
                    </div>
                </div>
            </div>

            <!-- VIEW 9: ADMIN DASHBOARD -->
            <div id="view-admin" class="view-content hidden space-y-6">
                <header class="pb-4 border-b border-slate-200">
                    <h1 class="text-2xl font-black text-slate-900">👑 Admin Management Dashboard</h1>
                    <p class="text-xs text-slate-500">จัดการคำสั่งซื้อ ตรวจสอบสลิปภาพ และอัปเดตสถานะคิวขึ้นเอ็น</p>
                </header>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">🧾 ตรวจสอบคำสั่งซื้อ & สลิปไฟล์</h2>
                        <div id="admin-orders-list" class="space-y-3 text-xs"></div>
                    </div>
                    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <h2 class="font-bold text-sm text-slate-800">🧵 จัดการคิวขึ้นเอ็น</h2>
                        <div id="admin-stringing-list" class="space-y-3 text-xs"></div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- MODALS -->
    <!-- Modal Add Racket with Real File Upload -->
    <div id="add-racket-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h3 class="text-lg font-bold text-slate-900">➕ เพิ่มไม้แบดมินตันใหม่</h3>
            <div class="space-y-3">
                <input type="text" id="add-brand" placeholder="แบรนด์ (เช่น YONEX, VICTOR)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                <input type="text" id="add-model" placeholder="ชื่อรุ่น (เช่น ASTROX 99 PRO)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                <input type="number" id="add-price" placeholder="ราคา (บาท)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
                <div>
                    <label class="text-[10px] text-slate-500 block mb-1">เลือกไฟล์รูปภาพไม้แบดมินตันจากเครื่อง:</label>
                    <input type="file" id="add-image-file" accept="image/*" class="w-full bg-slate-50 border border-slate-300 p-2 rounded-xl text-xs">
                </div>
                <textarea id="add-desc" placeholder="คำอธิบายสเปกไม้" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs h-20"></textarea>
            </div>
            <div class="flex gap-2">
                <button onclick="closeModal('add-racket-modal')" class="w-1/2 py-2 bg-slate-100 rounded-xl text-xs font-bold text-slate-600">ยกเลิก</button>
                <button onclick="addNewRacketWithFile()" class="w-1/2 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700">บันทึกข้อมูล</button>
            </div>
        </div>
    </div>

    <!-- Modal Login -->
    <div id="login-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-xl">
            <h3 class="text-lg font-bold text-slate-900">เข้าสู่ระบบ</h3>
            <input type="text" id="login-username" placeholder="Username (somchai หรือ admin)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <input type="password" id="login-password" placeholder="Password (123456 หรือ admin123)" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <div class="flex justify-between items-center text-xs">
                <button onclick="openResetPasswordModal()" class="text-sky-600 font-bold hover:underline">ลืมรหัสผ่าน?</button>
            </div>
            <div class="flex gap-2">
                <button onclick="closeModal('login-modal')" class="w-1/2 py-2 bg-slate-100 rounded-xl text-xs font-bold text-slate-600">ยกเลิก</button>
                <button onclick="login()" class="w-1/2 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700">เข้าสู่ระบบ</button>
            </div>
        </div>
    </div>

    <!-- Modal Reset Password -->
    <div id="reset-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-xl">
            <h3 class="text-lg font-bold text-slate-900">กู้คืนรหัสผ่าน</h3>
            <input type="text" id="reset-username" placeholder="Username ของคุณ" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <input type="password" id="reset-new-password" placeholder="ตั้งรหัสผ่านใหม่" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <div class="flex gap-2">
                <button onclick="closeModal('reset-modal')" class="w-1/2 py-2 bg-slate-100 rounded-xl text-xs font-bold text-slate-600">ยกเลิก</button>
                <button onclick="resetPassword()" class="w-1/2 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700">รีเซ็ตรหัสผ่าน</button>
            </div>
        </div>
    </div>

    <!-- Modal Register -->
    <div id="register-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-xl">
            <h3 class="text-lg font-bold text-slate-900">สมัครสมาชิก</h3>
            <input type="text" id="reg-username" placeholder="Username" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <input type="email" id="reg-email" placeholder="Email" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <input type="password" id="reg-password" placeholder="Password" class="w-full bg-slate-50 border border-slate-300 p-2.5 rounded-xl text-xs">
            <div class="flex gap-2">
                <button onclick="closeModal('register-modal')" class="w-1/2 py-2 bg-slate-100 rounded-xl text-xs font-bold text-slate-600">ยกเลิก</button>
                <button onclick="register()" class="w-1/2 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold hover:bg-sky-700">ลงทะเบียน</button>
            </div>
        </div>
    </div>

    <!-- Modal Racket Detail & Review -->
    <div id="racket-detail-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div id="racket-detail-content" class="bg-white rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-xl relative max-h-[90vh] overflow-y-auto"></div>
    </div>

    <!-- Modal Printable Receipt -->
    <div id="printable-receipt-modal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl p-6 max-w-md w-full space-y-4 shadow-xl relative text-xs">
            <div class="text-center border-b pb-3 border-slate-200">
                <h2 class="text-lg font-black text-slate-900">SMASH LAB BADMINTON</h2>
                <p class="text-[10px] text-slate-500">ใบเสร็จรับเงิน / เอกสารการสั่งซื้อ</p>
            </div>
            <div id="receipt-details-content" class="space-y-2"></div>
            <div class="flex gap-2 pt-3 border-t border-slate-200 no-print">
                <button onclick="closeModal('printable-receipt-modal')" class="w-1/2 py-2 bg-slate-100 rounded-xl font-bold text-slate-600">ปิด</button>
                <button onclick="window.print()" class="w-1/2 py-2 bg-sky-600 text-white rounded-xl font-bold hover:bg-sky-700">🖨️ พิมพ์ใบเสร็จ</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;
        let cart = [];
        let racketsData = [];
        let scene, camera, renderer, racketGroup, frameMesh, stringMesh, gripMesh;
        const defaultFallbackImage = 'https://images.unsplash.com/photo-1626225967045-94408422617d?w=600&auto=format&fit=crop&q=80';

        function showLanding() {
            document.getElementById('landing-page').classList.remove('hidden');
            document.getElementById('app-page').classList.add('hidden');
        }

        function showApp(tab = 'rackets') {
            document.getElementById('landing-page').classList.add('hidden');
            document.getElementById('app-page').classList.remove('hidden');
            switchTab(tab, document.getElementById('nav-' + tab));
        }

        function switchTab(viewId, element) {
            document.querySelectorAll('.view-content').forEach(el => el.classList.add('hidden'));
            const targetView = document.getElementById('view-' + viewId);
            if (targetView) targetView.classList.remove('hidden');

            document.querySelectorAll('#sidebar-nav button').forEach(btn => {
                if(btn.id !== 'nav-admin') {
                    btn.className = 'w-full flex items-center gap-3 px-3 py-2.5 text-slate-600 hover:text-sky-600 hover:bg-slate-100 text-xs font-semibold transition text-left rounded-lg';
                }
            });
            if (element && element.id !== 'nav-admin') {
                element.className = 'w-full sidebar-active flex items-center gap-3 px-3 py-2.5 text-xs font-bold transition text-left rounded-lg';
            }

            if (viewId === 'studio' && !scene) {
                setTimeout(init3DStudio, 100);
            } else if (viewId === 'admin') {
                loadAdminData();
            }
        }

        function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        function showToast(msg, isError = false) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast-notification px-4 py-3 rounded-xl text-xs font-bold shadow-lg pointer-events-auto flex items-center justify-between ${isError ? 'bg-rose-600 text-white' : 'bg-slate-900 text-white'}`;
            toast.innerHTML = `<span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        // Fetch & Render Rackets
        async function fetchRackets() {
            const res = await fetch('/api/rackets');
            racketsData = await res.json();
            renderRackets(racketsData);
        }

        function renderRackets(items) {
            const grid = document.getElementById('rackets-grid');
            if (!grid) return;
            grid.innerHTML = items.map(item => `
                <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div class="h-48 overflow-hidden bg-slate-100 relative">
                        <img src="${item.image_url || defaultFallbackImage}" 
                             onerror="this.onerror=null; this.src='${defaultFallbackImage}';" 
                             alt="${item.model_name}" 
                             class="w-full h-full object-cover">
                        <span class="absolute top-3 left-3 bg-slate-900/80 text-white text-[10px] px-2 py-0.5 rounded-md font-bold">${item.brand}</span>
                    </div>
                    <div class="p-4 space-y-2 flex-1 flex flex-col justify-between">
                        <div>
                            <h3 class="font-extrabold text-slate-900 text-sm">${item.model_name}</h3>
                            <p class="text-xs text-slate-500 line-clamp-2 mt-1">${item.description || ''}</p>
                            <div class="mt-3 flex flex-wrap gap-1 text-[10px] text-slate-600">
                                <span class="bg-slate-100 px-2 py-0.5 rounded">🏋️ ${item.weight}</span>
                                <span class="bg-slate-100 px-2 py-0.5 rounded">⚖️ ${item.balance}</span>
                                <span class="bg-slate-100 px-2 py-0.5 rounded">⚡ ${item.stiffness}</span>
                            </div>
                        </div>
                        <div class="pt-3 border-t border-slate-100 flex items-center justify-between mt-3">
                            <span class="font-black text-sky-600 text-base">${item.price.toLocaleString()} ฿</span>
                            <div class="flex gap-2">
                                <button onclick="openRacketModal(${item.id})" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-bold text-slate-700">รายละเอียด/รีวิว</button>
                                <button onclick="addToCart('${item.model_name}', ${item.price})" class="px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold">ใส่ตะกร้า</button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        async function addNewRacketWithFile() {
            const brand = document.getElementById('add-brand').value;
            const model_name = document.getElementById('add-model').value;
            const price = document.getElementById('add-price').value;
            const description = document.getElementById('add-desc').value;
            const fileInput = document.getElementById('add-image-file');

            if (!brand || !model_name || !price) {
                return showToast('กรุณากรอกข้อมูลสำคัญให้ครบถ้วน', true);
            }

            const formData = new FormData();
            formData.append('brand', brand);
            formData.append('model_name', model_name);
            formData.append('price', price);
            formData.append('description', description);
            if (fileInput.files[0]) {
                formData.append('image_file', fileInput.files[0]);
            }

            const res = await fetch('/api/rackets', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                showToast('เพิ่มไม้แบดมินตันเรียบร้อย!');
                closeModal('add-racket-modal');
                fetchRackets();
            }
        }

        // Court Overlap Protection Checker
        async function checkBookedSlots() {
            const court = document.getElementById('booking-court').value;
            const date = document.getElementById('booking-date').value;
            if (!court || !date) return;

            const res = await fetch(`/api/bookings/check?court_name=${encodeURIComponent(court)}&booking_date=${date}`);
            const bookedTimes = await res.json();

            const selectTime = document.getElementById('booking-time');
            Array.from(selectTime.options).forEach(opt => {
                if (bookedTimes.includes(opt.value)) {
                    opt.disabled = true;
                    opt.text = opt.value + ' (ถูกจองแล้ว ❌)';
                } else {
                    opt.disabled = false;
                    opt.text = opt.value + ' (ว่าง ✅)';
                }
            });
        }

        async function submitBooking() {
            if (!currentUser) return showToast('กรุณาเข้าสู่ระบบก่อนทำการจอง', true);
            const court = document.getElementById('booking-court').value;
            const date = document.getElementById('booking-date').value;
            const time = document.getElementById('booking-time').value;
            if (!date) return showToast('กรุณาเลือกวันที่', true);

            const res = await fetch('/api/bookings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ court_name: court, booking_date: date, time_slot: time, price: 250 })
            });

            const data = await res.json();
            if (res.ok) {
                showToast('จองสนามเรียบร้อย!');
                loadBookings();
                checkBookedSlots();
            } else {
                showToast(data.message || 'การจองล้มเหลว', true);
            }
        }

        // Real File Checkout
        async function checkoutCartWithFile() {
            if (!currentUser) return showToast('กรุณาเข้าสู่ระบบก่อนชำระเงิน', true);
            if (cart.length === 0) return showToast('ตะกร้าสินค้าว่างเปล่า', true);
            const fileInput = document.getElementById('slip-file-input');
            if (!fileInput.files[0]) return showToast('กรุณาเลือกไฟล์สลิปชำระเงิน', true);

            const total = cart.reduce((sum, item) => sum + item.price, 0);
            const summary = cart.map(c => c.name).join(', ');

            const formData = new FormData();
            formData.append('total', total);
            formData.append('summary', summary);
            formData.append('slip_file', fileInput.files[0]);

            const res = await fetch('/api/checkout', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                showToast('อัปโหลดสลิปชำระเงินเรียบร้อย! รอแอดมินอนุมัติ');
                cart = [];
                fileInput.value = '';
                updateCartBadge();
            }
        }

        // Review Modal
        async function openRacketModal(id) {
            const item = racketsData.find(r => r.id === id);
            if (!item) return;

            const res = await fetch(`/api/reviews/${id}`);
            const reviews = await res.json();

            const content = document.getElementById('racket-detail-content');
            content.innerHTML = `
                <button onclick="closeModal('racket-detail-modal')" class="absolute top-3 right-3 text-slate-400 hover:text-slate-600 font-bold">✕</button>
                <div class="h-48 rounded-xl overflow-hidden mb-3">
                    <img src="${item.image_url || defaultFallbackImage}" onerror="this.onerror=null; this.src='${defaultFallbackImage}';" class="w-full h-full object-cover">
                </div>
                <span class="text-xs font-bold text-sky-600">${item.brand}</span>
                <h2 class="text-xl font-black text-slate-900">${item.model_name}</h2>
                <p class="text-xs text-slate-600">${item.description}</p>
                
                <div class="pt-4 border-t border-slate-200 space-y-3">
                    <h3 class="font-bold text-sm text-slate-800">⭐ รีวิวจากผู้ใช้งาน (${reviews.length})</h3>
                    <div class="space-y-2 max-h-32 overflow-y-auto">
                        ${reviews.length === 0 ? '<p class="text-xs text-slate-400">ยังไม่มีรีวิว</p>' : reviews.map(r => `
                            <div class="p-2 bg-slate-50 rounded-lg text-xs border border-slate-100">
                                <div class="flex justify-between font-bold text-slate-700"><span>${r.user_name}</span><span class="text-amber-500">${'★'.repeat(r.rating)}</span></div>
                                <p class="text-slate-600 mt-1">${r.comment}</p>
                            </div>
                        `).join('')}
                    </div>

                    <div class="bg-sky-50/50 p-3 rounded-xl space-y-2 border border-sky-100">
                        <span class="text-xs font-bold text-slate-700 block">เขียนรีวิวไม้นี้</span>
                        <select id="review-rating" class="w-full text-xs p-2 rounded-lg border border-slate-300">
                            <option value="5">⭐⭐⭐⭐⭐ (5/5)</option>
                            <option value="4">⭐⭐⭐⭐ (4/5)</option>
                        </select>
                        <input type="text" id="review-comment" placeholder="พิมพ์ความคิดเห็นของคุณ..." class="w-full text-xs p-2 rounded-lg border border-slate-300">
                        <button onclick="submitReview(${item.id})" class="w-full py-2 bg-sky-600 text-white rounded-lg text-xs font-bold hover:bg-sky-700">ส่งรีวิว</button>
                    </div>
                </div>

                <div class="flex justify-between items-center pt-2">
                    <span class="text-2xl font-black text-sky-600">${item.price.toLocaleString()} ฿</span>
                    <button onclick="addToCart('${item.model_name}', ${item.price}); closeModal('racket-detail-modal');" class="btn-glow-cyan px-5 py-2 rounded-xl text-xs font-bold">ใส่ตะกร้า</button>
                </div>
            `;
            openModal('racket-detail-modal');
        }

        async function submitReview(racketId) {
            if (!currentUser) return showToast('กรุณาเข้าสู่ระบบก่อน', true);
            const rating = parseInt(document.getElementById('review-rating').value);
            const comment = document.getElementById('review-comment').value;
            if (!comment) return showToast('กรุณากรอกข้อความรีวิว', true);

            const res = await fetch('/api/reviews', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ racket_id: racketId, rating, comment })
            });

            if (res.ok) {
                showToast('บันทึกรีวิวเรียบร้อย!');
                openRacketModal(racketId);
            }
        }

        // Printable Receipt Generator
        function printReceipt(orderCode, summary, amount, date) {
            const content = document.getElementById('receipt-details-content');
            content.innerHTML = `
                <div class="flex justify-between"><span class="text-slate-500">รหัสคำสั่งซื้อ:</span><span class="font-bold">${orderCode}</span></div>
                <div class="flex justify-between"><span class="text-slate-500">วันที่:</span><span>${date}</span></div>
                <div class="flex justify-between"><span class="text-slate-500">ผู้สั่งซื้อ:</span><span>${currentUser ? currentUser.username : 'Customer'}</span></div>
                <div class="pt-2 border-t border-slate-100">
                    <span class="text-slate-500 block mb-1">รายการสินค้า:</span>
                    <p class="font-bold text-slate-800">${summary}</p>
                </div>
                <div class="flex justify-between text-sm font-black pt-2 border-t border-slate-200">
                    <span>ยอดรวมทั้งสิ้น:</span>
                    <span class="text-sky-600">${amount.toLocaleString()} ฿</span>
                </div>
            `;
            openModal('printable-receipt-modal');
        }

        // 3D Studio
        function init3DStudio() {
            const container = document.getElementById('three-canvas-container');
            if (!container) return;

            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 12);

            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
            scene.add(ambientLight);

            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(5, 10, 7);
            scene.add(dirLight);

            racketGroup = new THREE.Group();

            const frameGeo = new THREE.TorusGeometry(2, 0.08, 16, 100);
            const frameMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.5, roughness: 0.2 });
            frameMesh = new THREE.Mesh(frameGeo, frameMat);
            frameMesh.scale.set(0.8, 1.1, 1);
            frameMesh.position.y = 2;
            racketGroup.add(frameMesh);

            const stringGeo = new THREE.CylinderGeometry(0.01, 0.01, 3.8, 8);
            const stringMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
            stringMesh = new THREE.Group();
            for (let i = -1.2; i <= 1.2; i += 0.3) {
                const lineV = new THREE.Mesh(stringGeo, stringMat);
                lineV.position.set(i, 2, 0);
                stringMesh.add(lineV);
                const lineH = new THREE.Mesh(stringGeo, stringMat);
                lineH.rotation.z = Math.PI / 2;
                lineH.position.set(0, 2 + i * 1.2, 0);
                lineH.scale.set(1, 0.7, 1);
                stringMesh.add(lineH);
            }
            racketGroup.add(stringMesh);

            const shaftGeo = new THREE.CylinderGeometry(0.06, 0.06, 3.5, 16);
            const shaftMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.6 });
            const shaftMesh = new THREE.Mesh(shaftGeo, shaftMat);
            shaftMesh.position.y = -0.8;
            racketGroup.add(shaftMesh);

            const gripGeo = new THREE.CylinderGeometry(0.12, 0.14, 2, 16);
            const gripMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.8 });
            gripMesh = new THREE.Mesh(gripGeo, gripMat);
            gripMesh.position.y = -3.2;
            racketGroup.add(gripMesh);

            scene.add(racketGroup);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            function animate() {
                requestAnimationFrame(animate);
                racketGroup.rotation.y += 0.005;
                controls.update();
                renderer.render(scene, camera);
            }
            animate();
        }

        function reset3DCamera() { if (camera) camera.position.set(0, 0, 12); }
        function update3DFrameColor(color) { if (frameMesh) frameMesh.material.color.set(color); }
        function update3DStringColor(color) { if (stringMesh) stringMesh.children.forEach(c => c.material.color.set(color)); }
        function update3DGripColor(color) { if (gripMesh) gripMesh.material.color.set(color); }

        function update3DModelPrice(select) {
            document.getElementById('display-model-name').innerText = select.options[select.selectedIndex].text;
            document.getElementById('display-price').innerText = parseInt(select.value).toLocaleString() + ' ฿';
        }

        function addCustomRacketToCart() {
            const name = document.getElementById('display-model-name').innerText + ' (3D Custom)';
            const price = parseInt(document.getElementById('model-select').value);
            addToCart(name, price);
        }

        function calculateAIMatch() {
            const style = document.getElementById('ai-style').value;
            let match = "YONEX ASTROX 88D PRO";
            let reason = "ไม้สายตบพลังทำลายล้างสูง เหมาะกับสายบุกและผู้เล่นที่ชอบเกมรุกหนัก";
            if (style === 'control') { match = "YONEX ARCSABER 11 PRO"; reason = "ไม้เน้นการควบคุมการวางลูก"; }
            const resDiv = document.getElementById('ai-result');
            resDiv.classList.remove('hidden');
            resDiv.innerHTML = `<div class="text-xs font-bold text-sky-800">🏸 ไม้แนะนำ:</div><div class="text-base font-black text-slate-900">${match}</div><div class="text-xs text-slate-600 mt-1">${reason}</div>`;
        }

        // Cart
        function addToCart(name, price) { cart.push({ name, price }); updateCartBadge(); showToast(`เพิ่ม "${name}" ลงในตะกร้าแล้ว`); }
        function updateCartBadge() { document.getElementById('cart-badge-count').innerText = cart.length; renderCart(); }
        function renderCart() {
            const container = document.getElementById('cart-items');
            if (!container) return;
            if (cart.length === 0) {
                container.innerHTML = `<div class="py-6 text-center text-xs text-slate-400">ยังไม่มีสินค้าในตะกร้า</div>`;
                document.getElementById('cart-total-price').innerText = '0 ฿';
                return;
            }
            let total = 0;
            container.innerHTML = cart.map((item, idx) => {
                total += item.price;
                return `<div class="py-3 flex justify-between items-center text-xs"><div><div class="font-bold text-slate-800">${item.name}</div><div class="text-sky-600 font-bold">${item.price.toLocaleString()} ฿</div></div><button onclick="removeFromCart(${idx})" class="text-rose-500 font-bold hover:underline">ลบ</button></div>`;
            }).join('');
            document.getElementById('cart-total-price').innerText = total.toLocaleString() + ' ฿';
            const qrImg = document.getElementById('qr-code-img');
            if (qrImg) qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=PROMPTPAY-AMOUNT-${total}`;
        }
        function removeFromCart(index) { cart.splice(index, 1); updateCartBadge(); }

        // Admin Loader
        async function loadAdminData() {
            if (!currentUser || currentUser.role !== 'admin') return;

            const resOrders = await fetch('/api/admin/orders');
            const orders = await resOrders.json();
            const ordersList = document.getElementById('admin-orders-list');
            ordersList.innerHTML = orders.map(o => `
                <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                    <div class="flex justify-between font-bold"><span>ผู้สั่ง: ${o.user_name} (${o.order_code})</span><span class="text-sky-600">${o.total_amount.toLocaleString()} ฿</span></div>
                    <p class="text-slate-500 text-[11px]">${o.items_summary}</p>
                    ${o.slip_filename ? `<a href="${o.slip_filename}" target="_blank" class="text-sky-600 underline font-bold text-[10px] block">🔍 ดูไฟล์สลิปรูปภาพจริง</a>` : ''}
                    <div class="flex justify-between items-center pt-2">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${o.status === 'ชำระเงินสำเร็จ' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">${o.status}</span>
                        ${o.status !== 'ชำระเงินสำเร็จ' ? `<button onclick="approveOrder(${o.id})" class="px-3 py-1 bg-emerald-600 text-white rounded-lg text-[10px] font-bold">อนุมัติสลิป</button>` : ''}
                    </div>
                </div>
            `).join('');

            const resStringing = await fetch('/api/stringing');
            const queues = await resStringing.json();
            const stringingList = document.getElementById('admin-stringing-list');
            stringingList.innerHTML = queues.map(q => `
                <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                    <div class="flex justify-between font-bold"><span>${q.racket} [${q.ticket_code}]</span><span class="text-sky-600">${q.status}</span></div>
                    <p class="text-slate-500 text-[11px]">${q.spec} (ลูกค้า: ${q.user_name})</p>
                    <div class="flex gap-2 pt-2">
                        <button onclick="updateStringingStatus(${q.id}, 'กำลังขึ้นเอ็น')" class="px-2.5 py-1 bg-amber-500 text-white rounded-lg text-[10px] font-bold">กำลังขึ้นเอ็น</button>
                        <button onclick="updateStringingStatus(${q.id}, 'เสร็จสิ้นพร้อมรับ')" class="px-2.5 py-1 bg-emerald-600 text-white rounded-lg text-[10px] font-bold">เสร็จสิ้น</button>
                    </div>
                </div>
            `).join('');
        }

        async function approveOrder(orderId) {
            const res = await fetch(`/api/admin/orders/approve/${orderId}`, { method: 'POST' });
            if (res.ok) { showToast('อนุมัติสลิปชำระเงินสำเร็จ!'); loadAdminData(); }
        }

        async function updateStringingStatus(queueId, status) {
            const res = await fetch(`/api/admin/stringing/status/${queueId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            if (res.ok) { showToast('อัปเดตสถานะขึ้นเอ็นเรียบร้อย!'); loadAdminData(); }
        }

        // Auth
        async function login() {
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (res.ok) { currentUser = data.user; updateUserUI(); closeModal('login-modal'); showToast('เข้าสู่ระบบสำเร็จ'); }
            else { showToast(data.message, true); }
        }

        function openResetPasswordModal() { closeModal('login-modal'); openModal('reset-modal'); }

        async function resetPassword() {
            const username = document.getElementById('reset-username').value;
            const new_password = document.getElementById('reset-new-password').value;
            const res = await fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, new_password })
            });
            if (res.ok) { showToast('รีเซ็ตรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่'); closeModal('reset-modal'); openModal('login-modal'); }
            else { showToast('ไม่พบ Username นี้', true); }
        }

        async function register() {
            const username = document.getElementById('reg-username').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-password').value;
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            if (res.ok) { closeModal('register-modal'); showToast('สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ'); }
        }

        async function logout() { await fetch('/api/logout'); currentUser = null; updateUserUI(); showToast('ออกจากระบบแล้ว'); }

        async function checkSession() {
            const res = await fetch('/api/me');
            if (res.ok) { const data = await res.json(); currentUser = data.user; updateUserUI(); }
        }

        function updateUserUI() {
            const userInfo = document.getElementById('header-user-info');
            const authBtns = document.getElementById('header-auth-btns');
            const adminNav = document.getElementById('nav-admin');

            if (currentUser) {
                userInfo.classList.remove('hidden');
                authBtns.classList.add('hidden');
                document.getElementById('user-display-tag').innerText = `👤 ${currentUser.username} (${currentUser.points} pts)`;
                if (currentUser.role === 'admin') adminNav.classList.remove('hidden');
                else adminNav.classList.add('hidden');
            } else {
                userInfo.classList.add('hidden');
                authBtns.classList.remove('hidden');
                adminNav.classList.add('hidden');
            }
        }

        async function openProfileModal() {
            if (!currentUser) return showToast('กรุณาเข้าสู่ระบบก่อน', true);
            const res = await fetch('/api/my-orders');
            const myOrders = await res.json();
            
            if (myOrders.length > 0) {
                const latest = myOrders[0];
                printReceipt(latest.order_code, latest.items_summary, latest.total_amount, latest.created_at);
            } else {
                showToast(`ผู้ใช้: ${currentUser.username} | คะแนน: ${currentUser.points} pts (ยังไม่มีประวัติการสั่งซื้อ)`);
            }
        }

        // Submits
        async function loadBookings() {
            const res = await fetch('/api/bookings');
            if (!res.ok) return;
            const data = await res.json();
            const list = document.getElementById('booking-list');
            if (!list) return;
            list.innerHTML = data.map(b => `
                <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <div class="font-bold text-slate-800">${b.court_name} (${b.booking_code})</div>
                    <div class="text-[11px] text-slate-500">${b.booking_date} | ${b.time_slot}</div>
                </div>
            `).join('');
        }

        async function submitStringing() {
            if (!currentUser) return showToast('กรุณาเข้าสู่ระบบก่อน', true);
            const racket = document.getElementById('stringing-racket').value;
            const spec = document.getElementById('stringing-spec').value;
            if (!racket || !spec) return showToast('กรุณากรอกข้อมูลให้ครบถ้วน', true);

            const res = await fetch('/api/stringing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ racket, spec })
            });
            if (res.ok) { showToast('บันทึกคิวขึ้นเอ็นเรียบร้อย!'); loadStringing(); }
        }

        async function loadStringing() {
            const res = await fetch('/api/stringing');
            if (!res.ok) return;
            const data = await res.json();
            const list = document.getElementById('stringing-list');
            if (!list) return;
            list.innerHTML = data.map(s => `
                <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 flex justify-between items-center">
                    <div>
                        <div class="font-bold text-slate-800">${s.racket} [${s.ticket_code}]</div>
                        <div class="text-[11px] text-slate-500">${s.spec} (ผู้ส่ง: ${s.user_name})</div>
                    </div>
                    <span class="px-2 py-1 bg-sky-100 text-sky-700 rounded text-[10px] font-bold">${s.status}</span>
                </div>
            `).join('');
        }

        async function loadCommunity() {
            const res = await fetch('/api/community');
            if (!res.ok) return;
            const data = await res.json();
            const grid = document.getElementById('community-grid');
            if (!grid) return;
            grid.innerHTML = data.map(c => `
                <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-black text-slate-900 text-base">${c.title}</h3>
                            <p class="text-xs text-slate-500">📍 ${c.location} | ⏰ ${c.time_slot}</p>
                        </div>
                        <span class="px-2 py-1 bg-amber-50 border border-amber-200 text-amber-700 rounded text-[10px] font-bold">${c.level}</span>
                    </div>
                    <div class="flex justify-between items-center pt-2 text-xs">
                        <span class="text-slate-600 font-semibold">สมาชิก: ${c.members_count}/${c.max_members} คน</span>
                        <button onclick="joinCommunity(${c.id})" class="px-4 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl font-bold">เข้าร่วมก๊วน</button>
                    </div>
                </div>
            `).join('');
        }

        async function joinCommunity(id) {
            const res = await fetch(`/api/community/join/${id}`, { method: 'POST' });
            if (res.ok) { showToast('เข้าร่วมก๊วนเรียบร้อย!'); loadCommunity(); }
        }

        async function loadProducts() {
            const res = await fetch('/api/products');
            if (!res.ok) return;
            const data = await res.json();
            const grid = document.getElementById('product-grid');
            if (!grid) return;
            grid.innerHTML = data.map(p => `
                <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-3 flex flex-col justify-between">
                    <div class="h-40 bg-slate-100 rounded-xl overflow-hidden relative">
                        <img src="${p.image_url || defaultFallbackImage}" onerror="this.onerror=null; this.src='${defaultFallbackImage}';" class="w-full h-full object-cover">
                        <span class="absolute top-2 left-2 text-xl">${p.icon}</span>
                    </div>
                    <div>
                        <h3 class="font-bold text-slate-900 text-sm">${p.name}</h3>
                        <p class="text-xs text-slate-500 mt-1">${p.description}</p>
                    </div>
                    <div class="flex justify-between items-center pt-2">
                        <span class="font-black text-sky-600 text-base">${p.price.toLocaleString()} ฿</span>
                        <button onclick="addToCart('${p.name}', ${p.price})" class="px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold">ใส่ตะกร้า</button>
                    </div>
                </div>
            `).join('');
        }

        window.addEventListener('DOMContentLoaded', () => {
            fetchRackets();
            checkSession();
            loadBookings();
            loadStringing();
            loadCommunity();
            loadProducts();
            
            const today = new Date().toISOString().split('T')[0];
            const dateInput = document.getElementById('booking-date');
            if(dateInput) {
                dateInput.value = today;
                checkBookedSlots();
            }
        });
    </script>
</body>
</html>
"""

# ==========================================
# 4. FLASK API ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        return jsonify({'message': 'Login successful', 'user': {'id': user.id, 'username': user.username, 'points': user.points, 'role': user.role}})
    return jsonify({'message': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}), 401

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.json or {}
    user = User.query.filter_by(username=data.get('username')).first()
    if user:
        user.set_password(data.get('new_password'))
        db.session.commit()
        return jsonify({'message': 'Password reset successful'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'message': 'Username หรือ Email ถูกใช้งานแล้ว'}), 400
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Register successful'})

@app.route('/api/logout')
def api_logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})

@app.route('/api/me')
def api_me():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'user': None}), 401
    user = User.query.get(user_id)
    if not user: return jsonify({'user': None}), 401
    return jsonify({'user': {'id': user.id, 'username': user.username, 'points': user.points, 'role': user.role}})

@app.route('/api/rackets', methods=['GET', 'POST'])
def handle_rackets():
    if request.method == 'POST':
        brand = request.form.get('brand', 'OTHER').upper()
        model_name = request.form.get('model_name')
        price = float(request.form.get('price', 0))
        description = request.form.get('description', '')
        
        image_url = save_uploaded_file(request.files.get('image_file'))
        if not image_url:
            image_url = 'https://images.unsplash.com/photo-1626225967045-94408422617d?w=600&auto=format&fit=crop&q=80'

        new_racket = Racket(brand=brand, model_name=model_name, price=price, image_url=image_url, description=description)
        db.session.add(new_racket)
        db.session.commit()
        send_system_notification("NEW RACKET", f"เพิ่มไม้แบดมินตันใหม่: {model_name}")
        return jsonify({'message': 'Racket added successfully'})

    rackets = Racket.query.all()
    return jsonify([{
        'id': r.id, 'brand': r.brand, 'model_name': r.model_name, 'series': r.series,
        'price': r.price, 'weight': r.weight, 'balance': r.balance, 'stiffness': r.stiffness,
        'max_tension': r.max_tension, 'stock': r.stock, 'description': r.description, 'image_url': r.image_url
    } for r in rackets])

@app.route('/api/reviews/<int:racket_id>', methods=['GET'])
def get_reviews(racket_id):
    reviews = Review.query.filter_by(racket_id=racket_id).order_by(Review.id.desc()).all()
    return jsonify([{'id': r.id, 'user_name': r.user_name, 'rating': r.rating, 'comment': r.comment} for r in reviews])

@app.route('/api/reviews', methods=['POST'])
def add_review():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'Unauthorized'}), 401
    user = User.query.get(user_id)
    data = request.json or {}
    review = Review(racket_id=data.get('racket_id'), user_name=user.username, rating=data.get('rating', 5), comment=data.get('comment', ''))
    db.session.add(review)
    db.session.commit()
    return jsonify({'message': 'Review added successfully'})

@app.route('/api/products')
def get_products():
    products = Product.query.all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': p.price, 'stock': p.stock, 'icon': p.icon, 'description': p.description, 'image_url': p.image_url} for p in products])

# Booking API with Overlap Protection
@app.route('/api/bookings/check')
def check_bookings():
    court_name = request.args.get('court_name')
    booking_date = request.args.get('booking_date')
    bookings = Booking.query.filter_by(court_name=court_name, booking_date=booking_date).all()
    return jsonify([b.time_slot for b in bookings])

@app.route('/api/bookings', methods=['GET', 'POST'])
def handle_bookings():
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id: return jsonify({'message': 'Unauthorized'}), 401
        data = request.json or {}
        
        court_name = data.get('court_name')
        booking_date = data.get('booking_date')
        time_slot = data.get('time_slot')

        # CHECK OVERLAP
        existing = Booking.query.filter_by(court_name=court_name, booking_date=booking_date, time_slot=time_slot).first()
        if existing:
            return jsonify({'message': 'ช่วงเวลานี้ถูกจองไปแล้ว กรุณาเลือกเวลาอื่น'}), 400

        booking = Booking(user_id=user_id, court_name=court_name, booking_date=booking_date, time_slot=time_slot, price=data.get('price', 250))
        db.session.add(booking)
        db.session.commit()
        send_system_notification("NEW BOOKING", f"มีการจองสนาม {court_name} วันที่ {booking_date} เวลา {time_slot}")
        return jsonify({'message': 'Booking created'})
    
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return jsonify([{'id': b.id, 'court_name': b.court_name, 'booking_date': b.booking_date, 'time_slot': b.time_slot, 'price': b.price, 'booking_code': b.booking_code} for b in bookings])

@app.route('/api/stringing', methods=['GET', 'POST'])
def handle_stringing():
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id: return jsonify({'message': 'Unauthorized'}), 401
        user = User.query.get(user_id)
        data = request.json or {}
        queue = StringingQueue(user_id=user_id, user_name=user.username, racket=data.get('racket'), spec=data.get('spec'))
        db.session.add(queue)
        db.session.commit()
        send_system_notification("STRINGING QUEUE", f"คิวขึ้นเอ็นใหม่จาก {user.username}: {data.get('racket')}")
        return jsonify({'message': 'Stringing queue added'})
    
    queues = StringingQueue.query.order_by(StringingQueue.id.desc()).all()
    return jsonify([{'id': q.id, 'user_name': q.user_name, 'racket': q.racket, 'spec': q.spec, 'status': q.status, 'ticket_code': q.ticket_code} for q in queues])

@app.route('/api/community')
def get_community():
    groups = CommunityGroup.query.all()
    return jsonify([{'id': g.id, 'host_name': g.host_name, 'title': g.title, 'location': g.location, 'time_slot': g.time_slot, 'level': g.level, 'members_count': g.members_count, 'max_members': g.max_members} for g in groups])

@app.route('/api/community/join/<int:group_id>', methods=['POST'])
def join_community(group_id):
    group = CommunityGroup.query.get(group_id)
    if group and group.members_count < group.max_members:
        group.members_count += 1
        db.session.commit()
        return jsonify({'message': 'Joined successfully'})
    return jsonify({'message': 'Group full or not found'}), 400

@app.route('/api/checkout', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'message': 'กรุณาเข้าสู่ระบบก่อน'}), 401
    
    total = float(request.form.get('total', 0))
    summary = request.form.get('summary', '')
    slip_path = save_uploaded_file(request.files.get('slip_file'))

    order = Order(user_id=user_id, total_amount=total, items_summary=summary, slip_filename=slip_path)
    db.session.add(order)
    
    user = User.query.get(user_id)
    if user: user.points += int(total * 0.1)
    db.session.commit()

    send_system_notification("ORDER & SLIP", f"คำสั่งซื้อใหม่จาก {user.username}: {total} บาท (แนบสลิปเรียบร้อย)")
    return jsonify({'message': 'Order completed successfully'})

@app.route('/api/my-orders')
def my_orders():
    user_id = session.get('user_id')
    if not user_id: return jsonify([])
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()
    return jsonify([{'id': o.id, 'order_code': o.order_code, 'total_amount': o.total_amount, 'items_summary': o.items_summary, 'status': o.status, 'created_at': o.created_at.strftime('%Y-%m-%d %H:%M')} for o in orders])

# ADMIN ROUTES
@app.route('/api/admin/orders')
def admin_orders():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != 'admin': return jsonify([]), 403
    orders = Order.query.order_by(Order.id.desc()).all()
    res = []
    for o in orders:
        u = User.query.get(o.user_id)
        res.append({'id': o.id, 'order_code': o.order_code, 'user_name': u.username if u else 'Unknown', 'total_amount': o.total_amount, 'items_summary': o.items_summary, 'slip_filename': o.slip_filename, 'status': o.status})
    return jsonify(res)

@app.route('/api/admin/orders/approve/<int:order_id>', methods=['POST'])
def approve_order(order_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != 'admin': return jsonify({'message': 'Forbidden'}), 403
    order = Order.query.get(order_id)
    if order:
        order.status = 'ชำระเงินสำเร็จ'
        db.session.commit()
        return jsonify({'message': 'Approved'})
    return jsonify({'message': 'Not found'}), 404

@app.route('/api/admin/stringing/status/<int:queue_id>', methods=['POST'])
def update_stringing_status(queue_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != 'admin': return jsonify({'message': 'Forbidden'}), 403
    data = request.json or {}
    queue = StringingQueue.query.get(queue_id)
    if queue:
        queue.status = data.get('status', 'กำลังดำเนินการ')
        db.session.commit()
        return jsonify({'message': 'Status updated'})
    return jsonify({'message': 'Not found'}), 404

# ==========================================
# 5. SERVER RUNNER & AUTO-OPEN BROWSER
# ==========================================
def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1, open_browser).start()
    
    app.run(debug=True, port=5000)