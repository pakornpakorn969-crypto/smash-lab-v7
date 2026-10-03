import pytest
from app import create_app, db, User, Product, Coupon, Order

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

# --- 1. AUTHENTICATION TESTS ---
def test_user_registration_and_login(client):
    # Register
    reg_res = client.post('/api/auth/register', json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    assert reg_res.status_code == 200
    assert reg_res.json["success"] is True

    # Login
    login_res = client.post('/api/auth/login', json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert login_res.status_code == 200
    assert login_res.json["user"]["email"] == "test@example.com"

# --- 2. CATALOG & COUPON TESTS ---
def test_get_catalog(client):
    res = client.get('/api/catalog/products')
    assert res.status_code == 200
    assert isinstance(res.json, list)

def test_coupon_validation(client):
    # Test valid coupon
    res = client.post('/api/catalog/coupons/validate', json={
        "code": "SMASH10",
        "subtotal": 5000
    })
    assert res.status_code == 200
    assert res.json["valid"] is True
    assert res.json["discount"] == 500

# --- 3. ORDER CREATION TESTS ---
def test_create_order(client):
    # Login user session
    client.post('/api/auth/login', json={"email": "user@smashlab.com", "password": "user1234"})
    
    order_data = {
        "items": [
            {"id": 1, "brand": "Yonex", "model": "Astrox 100 ZZ", "price": 6890, "quantity": 1}
        ],
        "discount_amount": 500,
        "coupon_code": "PRO500"
    }
    res = client.post('/api/orders/create', json=order_data)
    assert res.status_code == 201
    assert res.json["success"] is True
    assert res.json["order"]["total_price"] == 6390

# --- 4. ADMIN SECURITY TESTS ---
def test_admin_unauthorized_access(client):
    # User non-admin
    client.post('/api/auth/login', json={"email": "user@smashlab.com", "password": "user1234"})
    res = client.get('/api/admin/dashboard')
    assert res.status_code == 403

def test_admin_authorized_access(client):
    # Admin User
    client.post('/api/auth/login', json={"email": "admin@smashlab.com", "password": "admin1234"})
    res = client.get('/api/admin/dashboard')
    assert res.status_code == 200
    assert "total_orders" in res.json