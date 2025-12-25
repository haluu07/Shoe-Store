"""
Script để tạo tài khoản admin cho Shoe Store
Chạy script này để tạo một tài khoản quản trị viên mới
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    """Tạo tài khoản admin mới"""
    print("=" * 50)
    print("TẠO TÀI KHOẢN ADMIN CHO SHOE STORE")
    print("=" * 50)
    print()
    
    # Nhập thông tin
    name = input("Nhập tên đầy đủ: ").strip()
    email = input("Nhập email: ").strip()
    username = input("Nhập username: ").strip()
    password = input("Nhập password: ").strip()
    
    # Xác nhận password
    confirm_password = input("Xác nhận password: ").strip()
    
    # Kiểm tra password khớp
    if password != confirm_password:
        print("\n❌ Lỗi: Password không khớp!")
        return
    
    # Kiểm tra các trường bắt buộc
    if not all([name, email, username, password]):
        print("\n❌ Lỗi: Vui lòng điền đầy đủ thông tin!")
        return
    
    with app.app_context():
        # Kiểm tra username đã tồn tại chưa
        if User.query.filter_by(username=username).first():
            print(f"\n❌ Lỗi: Username '{username}' đã tồn tại!")
            return
        
        # Kiểm tra email đã tồn tại chưa
        if User.query.filter_by(email=email).first():
            print(f"\n❌ Lỗi: Email '{email}' đã được sử dụng!")
            return
        
        try:
            # Tạo user admin mới
            admin = User(
                name=name,
                email=email,
                username=username,
                password=generate_password_hash(password),
                is_admin=True
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print("\n" + "=" * 50)
            print("✅ TẠO ADMIN THÀNH CÔNG!")
            print("=" * 50)
            print(f"Tên: {name}")
            print(f"Email: {email}")
            print(f"Username: {username}")
            print(f"Quyền: Admin")
            print("\nBạn có thể đăng nhập với tài khoản này ngay bây giờ!")
            print("=" * 50)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Lỗi khi tạo admin: {str(e)}")

if __name__ == '__main__':
    create_admin()

