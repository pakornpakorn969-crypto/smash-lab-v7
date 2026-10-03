from app import app, db, Racket

with app.app_context():
    rackets = Racket.query.all()
    for racket in rackets:
        # หากยังไม่มีรูป ให้ใส่รูปภาพ Placeholder ชั่วคราว
        if not racket.image_url:
            racket.image_url = 'https://placehold.co/600x300/e2e8f0/1e293b?text=Racket+Image'
            
        # หมายเหตุ: หากเก็บรูปไว้ในเครื่องที่โฟลเดอร์ static/images/ ให้ใช้แบบนี้แทน:
        # racket.image_url = f'/static/images/{racket.id}.jpg'

    db.session.commit()
    print("อัปเดตรูปภาพใส่ฐานข้อมูลเรียบร้อยแล้ว!")