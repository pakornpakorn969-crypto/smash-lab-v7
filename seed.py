from app import create_app, db, User, Product, Coupon
from werkzeug.security import generate_password_hash

app = create_app()

def seed_database():
    with app.app_context():
        # สร้างตารางทั้งหมดหากยังไม่มี
        db.create_all()
        print("Creating database tables...")

        # 1. สร้างบัญชี Admin
        if not User.query.filter_by(email="admin@smashlab.com").first():
            admin = User(
                name="System Admin",
                email="admin@smashlab.com",
                password_hash=generate_password_hash("admin1234"),
                role="admin"
            )
            db.session.add(admin)
            print("Created Default Admin account")

        # 2. สร้างบัญชี Customer
        if not User.query.filter_by(email="user@smashlab.com").first():
            user = User(
                name="Pro Customer",
                email="user@smashlab.com",
                password_hash=generate_password_hash("user1234"),
                role="customer"
            )
            db.session.add(user)
            print("Created Default Customer account")

        # 3. สร้างสินค้าตัวอย่าง (Badminton Rackets)
        if Product.query.count() == 0:
            products = [
                Product(brand="Yonex", model="Astrox 100 ZZ", price=6890, stock=15, image="yonex_astrox100zz.jpg"),
                Product(brand="Yonex", model="Nanoflare 1000 Z", price=6790, stock=10, image="yonex_nf1000z.jpg"),
                Product(brand="Victor", model="Thruster Ryuga II", price=5990, stock=8, image="victor_ryuga2.jpg"),
                Product(brand="Li-Ning", model="Halbertec 9000", price=6490, stock=12, image="lining_hb9000.jpg")
            ]
            db.session.add_all(products)
            print("Seeded Default Products")

        # 4. สร้างโค้ดส่วนลด
        if Coupon.query.count() == 0:
            coupons = [
                Coupon(code="SMASH10", discount_type="percent", value=10.0, min_spend=0),
                Coupon(code="PRO500", discount_type="fixed", value=500.0, min_spend=3000)
            ]
            db.session.add_all(coupons)
            print("Seeded Default Coupons")

        db.session.commit()
        print("Database Seeding Completed Successfully!")

if __name__ == "__main__":
    seed_database()