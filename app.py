from flask import Flask, render_template_string, jsonify, request
import sqlite3
import os
import json
import webbrowser
import threading
import time
from datetime import datetime

app = Flask(__name__)
DB_NAME = "smashlab.db"

# ==================== DATABASE INITIALIZATION ====================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, role TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS rackets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT, name TEXT, price INTEGER, style TEXT, balance TEXT, flex TEXT, desc TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT, total_price INTEGER, items_json TEXT, created_at TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, user TEXT, action TEXT, details TEXT
    )''')

    # Seed Default Data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES ('Admin Master', 'admin@smashlab.com', 'admin123', 'admin')")
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES ('User Pilot', 'user@smashlab.com', '123456', 'user')")

    cursor.execute("SELECT COUNT(*) FROM rackets")
    if cursor.fetchone()[0] == 0:
        default_rackets = [
            ('Yonex', 'Astrox 100 ZZ', 6890, 'power', 'Head Heavy', 'Extra Stiff', 'ตัวท็อปสายตบ ตบปักหนักแน่นสูงสุด'),
            ('Yonex', 'Nanoflare 1000 Z', 6590, 'speed', 'Head Light', 'Extra Stiff', 'หน้าไม้วิ่งไว สปีดสวิงเร็วที่สุด'),
            ('Victor', 'Thruster Ryuga II', 6200, 'power', 'Head Heavy', 'Stiff', 'สายบุกตบหนัก ก้านสะท้านน้อย'),
            ('Li-Ning', 'Halbertec 9000', 6900, 'control', 'Even Balance', 'Medium-Stiff', 'แม่นยำสูง วางลูกสั่งได้ดั่งใจ'),
            ('VS', 'Titan 1000', 1490, 'power', 'Head Heavy', 'Flexible', 'ไม้คุ้มค่า ตีง่าย ช่วยส่งแรงถึงหลังคอร์ด')
        ]
        cursor.executemany("INSERT INTO rackets (brand, name, price, style, balance, flex, desc) VALUES (?, ?, ?, ?, ?, ?, ?)", default_rackets)

    conn.commit()
    conn.close()

def add_log(action, details, user="Guest User"):
    conn = get_db()
    conn.cursor().execute(
        "INSERT INTO logs (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user, action, details)
    )
    conn.commit()
    conn.close()

# Initialize DB on Startup
init_db()

# ==================== HTML / FRONTEND TEMPLATE ====================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="th" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMASH LAB // FLASK + SQLITE + PROMPTPAY SYSTEM</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700;800&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #020617; color: #f8fafc; font-family: 'Kanit', sans-serif; overflow-x: hidden; }
        #cyberBg { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; pointer-events: none; }
        .cyber-glass { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(20px); border: 1px solid rgba(56, 189, 248, 0.2); box-shadow: 0 0 35px rgba(2, 6, 23, 0.8); }
        .grid-bg { background-size: 40px 40px; background-image: linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px); }
        ::-webkit-scrollbar { width: 5px; } ::-webkit-scrollbar-track { background: #020617; } ::-webkit-scrollbar-thumb { background: #06b6d4; border-radius: 10px; }
    </style>
</head>
<body class="grid-bg min-h-screen relative selection:bg-cyan-500 selection:text-black">
    <canvas id="cyberBg"></canvas>

    <div class="relative z-20">
        <!-- NAVBAR -->
        <nav class="bg-slate-950/80 backdrop-blur-2xl border-b border-cyan-500/20 sticky top-0 z-40">
            <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
                <div class="flex items-center gap-3 cursor-pointer" onclick="switchTab('cover')">
                    <div class="bg-gradient-to-tr from-cyan-500 via-emerald-400 to-teal-300 text-slate-950 p-2.5 rounded-xl shadow-lg shadow-cyan-500/30">
                        <i class="fa-solid fa-atom text-2xl"></i>
                    </div>
                    <div>
                        <div class="font-[Orbitron] font-black text-xl tracking-wider text-white">SMASH<span class="text-cyan-400">LAB</span></div>
                        <div class="text-[9px] text-emerald-400 font-mono uppercase">FLASK + SQLITE ACTIVE</div>
                    </div>
                </div>

                <div class="hidden lg:flex items-center gap-1 bg-slate-900/90 p-1.5 rounded-2xl border border-slate-800">
                    <button onclick="switchTab('cover')" class="px-4 py-2 rounded-xl text-xs font-semibold text-cyan-400 hover:text-white"><i class="fa-solid fa-house mr-1"></i>หน้าปก</button>
                    <button onclick="switchTab('racket')" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"><i class="fa-solid fa-brain mr-1 text-cyan-400"></i>วิเคราะห์ไม้</button>
                    <button onclick="switchTab('catalog')" class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"><i class="fa-solid fa-database mr-1 text-purple-400"></i>คลังสินค้า</button>
                    <button onclick="switchTab('admin')" id="tab-admin" class="hidden px-4 py-2 rounded-xl text-xs font-bold bg-rose-500 text-white"><i class="fa-solid fa-shield-halved mr-1"></i>หลังบ้าน (Admin)</button>
                </div>

                <div class="flex items-center gap-3">
                    <button onclick="openCartModal()" class="relative bg-slate-900 border border-slate-800 text-cyan-400 px-3.5 py-2 rounded-xl text-xs font-bold">
                        <i class="fa-solid fa-cart-shopping text-base"></i>
                        <span id="cartCountBadge" class="absolute -top-1.5 -right-1.5 bg-rose-500 text-white text-[10px] w-5 h-5 rounded-full flex items-center justify-center font-bold">0</span>
                    </button>
                    <div id="authSection"></div>
                </div>
            </div>
        </nav>

        <main class="max-w-7xl mx-auto px-4 py-8">
            <!-- COVER SECTION -->
            <div id="content-cover" class="space-y-8 py-6 text-center">
                <div class="cyber-glass p-8 md:p-16 rounded-3xl space-y-6 border border-cyan-500/30">
                    <span class="px-4 py-1.5 rounded-full bg-cyan-950 border border-cyan-500/50 text-cyan-400 text-xs font-mono"><i class="fa-solid fa-server mr-1"></i> FLASK ENGINE & SQLITE CONNECTED</span>
                    <h1 class="text-4xl md:text-6xl font-black text-white font-[Orbitron]">SMASH LAB <span class="text-cyan-400">E-COMMERCE SYSTEM</span></h1>
                    <p class="text-slate-300 text-base max-w-2xl mx-auto">ระบบวิเคราะห์ไม้แบดมินตัน สั่งซื้อสินค้า และชำระเงินอัตโนมัติด้วย PromptPay QR Code</p>
                    <div class="flex justify-center gap-4 pt-4">
                        <button onclick="switchTab('racket')" class="bg-gradient-to-r from-cyan-500 to-emerald-400 text-slate-950 font-black px-8 py-3.5 rounded-xl text-sm font-[Orbitron]"><i class="fa-solid fa-bolt mr-1"></i> START ANALYSIS</button>
                        <button onclick="switchTab('catalog')" class="bg-slate-900 text-white font-bold px-8 py-3.5 rounded-xl text-sm border border-slate-800"><i class="fa-solid fa-store mr-1"></i> BROWSE STORE</button>
                    </div>
                </div>
            </div>

            <!-- ANALYZER SECTION -->
            <div id="content-racket" class="hidden space-y-8">
                <div class="cyber-glass p-6 md:p-8 rounded-3xl space-y-6">
                    <h3 class="text-xl font-bold text-white border-b border-slate-800 pb-4"><i class="fa-solid fa-sliders text-cyan-400"></i> เลือกสไตล์การเล่นของคุณ</h3>
                    <form class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-xs font-mono text-cyan-400 mb-2">1. Playstyle Archetype</label>
                            <select id="playstyle" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-100">
                                <option value="power">Power Smasher (สายบุกตบหนัก)</option>
                                <option value="speed">Speed Drive (สายสปีด ดักหน้าไม้)</option>
                                <option value="control">Precision Control (สายคอนโทรล)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-mono text-cyan-400 mb-2">2. Wrist Skill Level</label>
                            <select id="skill" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-100">
                                <option value="beginner">Beginner (มือใหม่)</option>
                                <option value="advanced">Advanced (มือเก๋า)</option>
                            </select>
                        </div>
                        <div class="md:col-span-2">
                            <button type="button" onclick="analyzeRacket()" class="w-full bg-cyan-500 text-slate-950 font-black py-4 rounded-xl font-[Orbitron]"><i class="fa-solid fa-microchip mr-2"></i> EXECUTE ANALYSIS</button>
                        </div>
                    </form>
                </div>

                <div id="racketResult" class="hidden cyber-glass p-6 rounded-3xl space-y-6">
                    <h3 class="text-xl font-bold text-white"><i class="fa-solid fa-chart-pie text-cyan-400"></i> ไม้แบดมินตันแนะนำสำหรับคุณ:</h3>
                    <div id="racketListCards" class="grid grid-cols-1 md:grid-cols-3 gap-4"></div>
                </div>
            </div>

            <!-- CATALOG SECTION -->
            <div id="content-catalog" class="hidden space-y-6">
                <div class="cyber-glass p-6 md:p-8 rounded-3xl space-y-6">
                    <h2 class="text-2xl font-bold text-white"><i class="fa-solid fa-store text-purple-400 mr-2"></i>คลังสินค้าไม้แบดมินตัน</h2>
                    <div id="catalogGrid" class="grid grid-cols-1 md:grid-cols-3 gap-4"></div>
                </div>
            </div>

            <!-- ADMIN SECTION -->
            <div id="content-admin" class="hidden space-y-8">
                <div class="cyber-glass p-6 md:p-8 rounded-3xl space-y-6 border border-rose-500/40">
                    <h2 class="text-2xl font-black text-white border-b border-slate-800 pb-4">ศูนย์จัดการหลังบ้าน & SQLite Logs</h2>
                    
                    <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                        <h3 class="text-sm font-bold text-emerald-400"><i class="fa-solid fa-plus-circle mr-1"></i> เพิ่มไม้แบดรุ่นใหม่</h3>
                        <form onsubmit="handleAddRacket(event)" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <input type="text" id="addBrand" required placeholder="แบรนด์" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                            <input type="text" id="addName" required placeholder="ชื่อรุ่น" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                            <input type="number" id="addPrice" required placeholder="ราคา (บาท)" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                            <select id="addStyle" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                                <option value="power">Power</option>
                                <option value="speed">Speed</option>
                                <option value="control">Control</option>
                            </select>
                            <input type="text" id="addBalance" required placeholder="บาลานซ์" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                            <input type="text" id="addFlex" required placeholder="ความแข็งก้าน" class="bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-white">
                            <button type="submit" class="md:col-span-3 bg-emerald-500 text-slate-950 font-bold py-2.5 rounded-xl text-xs">บันทึกลง SQLite Database</button>
                        </form>
                    </div>

                    <div class="space-y-3">
                        <h3 class="text-sm font-bold text-cyan-400"><i class="fa-solid fa-list-check"></i> ประวัติกิจกรรมในระบบ (SQLite Logs)</h3>
                        <div class="overflow-x-auto rounded-2xl border border-slate-800">
                            <table class="w-full text-left text-xs text-slate-300">
                                <thead class="bg-slate-950 text-amber-400">
                                    <tr><th class="p-3">เวลา</th><th class="p-3">ผู้ใช้งาน</th><th class="p-3">กิจกรรม</th><th class="p-3">รายละเอียด</th></tr>
                                </thead>
                                <tbody id="adminLogsTable" class="divide-y divide-slate-800 bg-slate-950/80 font-mono"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- CART & PROMPTPAY CHECKOUT MODAL -->
    <div id="cartModal" class="hidden fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4">
        <div class="cyber-glass p-8 rounded-3xl max-w-lg w-full relative border border-cyan-500/40 space-y-6">
            <button onclick="closeCartModal()" class="absolute top-4 right-4 text-slate-400"><i class="fa-solid fa-xmark text-xl"></i></button>
            <h3 class="text-2xl font-black text-white font-[Orbitron] flex items-center gap-2"><i class="fa-solid fa-cart-shopping text-cyan-400"></i> ตะกร้าสินค้า</h3>
            
            <div id="cartItemsList" class="space-y-3 max-h-60 overflow-y-auto"></div>

            <div class="border-t border-slate-800 pt-4 flex justify-between items-center font-bold text-white text-lg">
                <span>ราคารวมทั้งหมด:</span>
                <span id="cartTotalPrice" class="text-amber-400 font-[Orbitron]">0 ฿</span>
            </div>

            <!-- PROMPTPAY QR AREA -->
            <div id="promptPayArea" class="hidden bg-slate-950 p-4 rounded-2xl border border-cyan-500/30 text-center space-y-3">
                <span class="text-xs text-cyan-400 font-mono font-bold block">PROMPTPAY QR CODE PAYMENT</span>
                <img id="qrCodeImg" src="" alt="PromptPay QR Code" class="mx-auto w-48 h-48 bg-white p-2 rounded-xl border-2 border-cyan-400">
                <p class="text-xs text-slate-400">สแกนจ่ายผ่านแอปธนาคารใดก็ได้ทันที</p>
                <button onclick="confirmOrderPayment()" class="w-full bg-emerald-500 text-slate-950 font-black py-3 rounded-xl text-xs font-[Orbitron]"><i class="fa-solid fa-circle-check mr-1"></i> ยืนยันชำระเงินเรียบร้อย</button>
            </div>

            <button id="checkoutBtn" onclick="generatePromptPayQR()" class="w-full bg-cyan-500 text-slate-950 font-black py-3 rounded-xl text-xs font-[Orbitron]"><i class="fa-solid fa-qrcode mr-1"></i> ดำเนินการชำระเงินด้วย PROMPTPAY</button>
        </div>
    </div>

    <!-- AUTH MODAL -->
    <div id="authModal" class="hidden fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4">
        <div class="cyber-glass p-8 rounded-3xl max-w-md w-full relative border border-cyan-500/40 space-y-4">
            <button onclick="closeAuthModal()" class="absolute top-4 right-4 text-slate-400"><i class="fa-solid fa-xmark text-xl"></i></button>
            <h3 class="text-2xl font-black text-white text-center font-[Orbitron]">LOGIN TO <span class="text-cyan-400">SMASH LAB</span></h3>
            <form onsubmit="handleLogin(event)" class="space-y-3">
                <input type="email" id="loginEmail" required placeholder="admin@smashlab.com" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white">
                <input type="password" id="loginPassword" required placeholder="••••••••" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white">
                <button type="submit" class="w-full bg-cyan-500 text-slate-950 font-black py-3 rounded-xl text-xs font-[Orbitron]">LOGIN</button>
            </form>
        </div>
    </div>

    <script>
        // CANVAS ANIMATION
        const canvas = document.getElementById('cyberBg'); const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();
        let particles = Array.from({length: 35}, () => ({ x: Math.random()*canvas.width, y: Math.random()*canvas.height, vx: (Math.random()-0.5)*0.8, vy: (Math.random()-0.5)*0.8 }));
        function anim() {
            ctx.clearRect(0,0,canvas.width,canvas.height);
            particles.forEach(p => {
                p.x += p.vx; p.y += p.vy;
                if(p.x<0||p.x>canvas.width) p.vx*=-1; if(p.y<0||p.y>canvas.height) p.vy*=-1;
                ctx.fillStyle = 'rgba(6,182,212,0.4)'; ctx.beginPath(); ctx.arc(p.x,p.y,2,0,Math.PI*2); ctx.fill();
            });
            requestAnimationFrame(anim);
        } anim();

        // STATE & CART
        let cart = [];
        let racketsDb = [];
        let currentUser = null;

        async function loadRackets() {
            const res = await fetch('/api/rackets');
            racketsDb = await res.json();
            renderCatalog();
        }

        async function loadLogs() {
            const res = await fetch('/api/logs');
            const logs = await res.json();
            document.getElementById('adminLogsTable').innerHTML = logs.map(l => `
                <tr><td class="p-3 text-slate-400 text-[11px]">${l.timestamp}</td><td class="p-3 font-bold text-white">${l.user}</td><td class="p-3 text-cyan-400">${l.action}</td><td class="p-3 text-slate-300">${l.details}</td></tr>
            `).join('');
        }

        function switchTab(tab) {
            ['cover','racket','admin','catalog'].forEach(t => {
                const el = document.getElementById(`content-${t}`);
                if(el) { if(t === tab) el.classList.remove('hidden'); else el.classList.add('hidden'); }
            });
            if(tab === 'admin') loadLogs();
        }

        function addToCart(racketId) {
            const item = racketsDb.find(r => r.id === racketId);
            if(item) {
                cart.push(item);
                updateCartBadge();
                alert(`เพิ่ม ${item.brand} ${item.name} ลงตะกร้าเรียบร้อย!`);
            }
        }

        function updateCartBadge() {
            document.getElementById('cartCountBadge').innerText = cart.length;
        }

        function openCartModal() {
            const list = document.getElementById('cartItemsList');
            if(cart.length === 0) {
                list.innerHTML = `<p class="text-slate-500 text-xs text-center py-4">ไม่มีสินค้าในตะกร้า</p>`;
            } else {
                list.innerHTML = cart.map((item, idx) => `
                    <div class="flex justify-between items-center bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs">
                        <div><strong class="text-cyan-400">${item.brand}</strong> <span class="text-white">${item.name}</span></div>
                        <div class="text-amber-400 font-bold">${item.price.toLocaleString()} ฿</div>
                    </div>
                `).join('');
            }
            const total = cart.reduce((sum, item) => sum + item.price, 0);
            document.getElementById('cartTotalPrice').innerText = `${total.toLocaleString()} ฿`;
            document.getElementById('promptPayArea').classList.add('hidden');
            document.getElementById('checkoutBtn').classList.remove('hidden');
            document.getElementById('cartModal').classList.remove('hidden');
        }

        function closeCartModal() { document.getElementById('cartModal').classList.add('hidden'); }

        function generatePromptPayQR() {
            if(cart.length === 0) { alert('ไม่มีสินค้าในตะกร้า'); return; }
            const total = cart.reduce((sum, item) => sum + item.price, 0);
            const mobileNumber = "0812345678"; // เบอร์ PromptPay สมมติ
            // Generate QR Code via Public API
            const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=PromptPay:${mobileNumber}:Amount:${total}`;
            document.getElementById('qrCodeImg').src = qrUrl;
            document.getElementById('promptPayArea').classList.remove('hidden');
            document.getElementById('checkoutBtn').classList.add('hidden');
        }

        async function confirmOrderPayment() {
            const total = cart.reduce((sum, item) => sum + item.price, 0);
            await fetch('/api/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_email: currentUser?currentUser.email:'guest@smashlab.com', total_price: total, items: cart })
            });
            alert('การชำระเงินสำเร็จ! บันทึกคำสั่งซื้อลงฐานข้อมูล SQLite เรียบร้อย');
            cart = [];
            updateCartBadge();
            closeCartModal();
        }

        function renderCatalog() {
            document.getElementById('catalogGrid').innerHTML = racketsDb.map(r => `
                <div class="bg-slate-950 p-5 rounded-2xl border border-slate-800 space-y-2">
                    <span class="text-[10px] text-cyan-400 font-mono font-bold">${r.brand}</span>
                    <h4 class="text-base font-bold text-white mt-1">${r.name}</h4>
                    <p class="text-xs text-amber-400 font-bold font-[Orbitron]">${r.price.toLocaleString()} ฿</p>
                    <p class="text-xs text-slate-400 mb-2">${r.desc}</p>
                    <button onclick="addToCart(${r.id})" class="w-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-bold py-2 rounded-xl text-xs hover:bg-cyan-500 hover:text-slate-950 transition"><i class="fa-solid fa-cart-plus mr-1"></i> เพิ่มลงตะกร้า</button>
                </div>
            `).join('');
        }

        async function handleAddRacket(e) {
            e.preventDefault();
            const newRacket = {
                brand: document.getElementById('addBrand').value,
                name: document.getElementById('addName').value,
                price: parseInt(document.getElementById('addPrice').value),
                style: document.getElementById('addStyle').value,
                balance: document.getElementById('addBalance').value,
                flex: document.getElementById('addFlex').value,
                desc: 'สินค้าลงทะเบียนผ่านระบบหลังบ้าน'
            };
            await fetch('/api/rackets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newRacket)
            });
            alert('เพิ่มลงฐานข้อมูล SQLite เรียบร้อย!');
            loadRackets();
        }

        function analyzeRacket() {
            const style = document.getElementById('playstyle').value;
            const rec = racketsDb.filter(r => r.style === style || style === 'allround').slice(0,3);
            document.getElementById('racketListCards').innerHTML = rec.map(r => `
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                    <span class="text-[10px] text-cyan-400 font-mono font-bold">${r.brand}</span>
                    <h5 class="text-sm font-bold text-white">${r.name}</h5>
                    <p class="text-xs text-amber-400 font-bold font-[Orbitron]">${r.price.toLocaleString()} ฿</p>
                    <button onclick="addToCart(${r.id})" class="w-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold py-1.5 rounded-lg text-xs"><i class="fa-solid fa-cart-plus mr-1"></i> สั่งซื้อรุ่นนี้</button>
                </div>
            `).join('');
            document.getElementById('racketResult').classList.remove('hidden');
        }

        function updateAuthUI() {
            const authSec = document.getElementById('authSection');
            if(currentUser) {
                authSec.innerHTML = `<span class="text-xs font-bold text-white">${currentUser.name}</span>`;
                if(currentUser.role === 'admin') document.getElementById('tab-admin').classList.remove('hidden');
            } else {
                authSec.innerHTML = `<button onclick="openAuthModal()" class="bg-cyan-500 text-slate-950 font-black px-4 py-2 rounded-xl text-xs font-[Orbitron]">LOGIN</button>`;
            }
        }
        function openAuthModal() { document.getElementById('authModal').classList.remove('hidden'); }
        function closeAuthModal() { document.getElementById('authModal').classList.add('hidden'); }
        async function handleLogin(e) {
            e.preventDefault();
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: document.getElementById('loginEmail').value, pass: document.getElementById('loginPassword').value })
            });
            const data = await res.json();
            if(data.success) {
                currentUser = data.user;
                updateAuthUI();
                closeAuthModal();
            } else alert('รหัสผ่านไม่ถูกต้อง (Admin: admin@smashlab.com / admin123)');
        }

        loadRackets();
        updateAuthUI();
    </script>
</body>
</html>"""

# ==================== FLASK REST API ROUTES ====================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/rackets', methods=['GET'])
def get_rackets():
    conn = get_db()
    rackets = conn.execute("SELECT * FROM rackets").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rackets])

@app.route('/api/rackets', methods=['POST'])
def add_racket():
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO rackets (brand, name, price, style, balance, flex, desc) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data['brand'], data['name'], data['price'], data['style'], data['balance'], data['flex'], data['desc'])
    )
    conn.commit()
    conn.close()
    add_log("ADD_PRODUCT", f"เพิ่มไม้แบดรุ่นใหม่ลง SQLite: {data['brand']} {data['name']}")
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (data['email'], data['pass'])).fetchone()
    conn.close()
    if user:
        user_dict = dict(user)
        add_log("AUTH_LOGIN", f"เข้าสู่ระบบสำเร็จ (Role: {user_dict['role']})", user_dict['name'])
        return jsonify({"success": True, "user": user_dict})
    return jsonify({"success": False})

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (user_email, total_price, items_json, created_at) VALUES (?, ?, ?, ?)",
        (data['user_email'], data['total_price'], json.dumps(data['items']), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    add_log("ORDER_CHECKOUT", f"สแกนชำระเงินด้วย PromptPay ยอดรวม: {data['total_price']:,} THB", data['user_email'])
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db()
    logs = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

if __name__ == '__main__':
    print("==================================================")
    print(" 🏸 SMASH LAB FLASK + SQLITE + PROMPTPAY SERVER ")
    print("==================================================")
    threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open("http://127.0.0.1:5000"))).start()
    app.run(debug=True, port=5000)