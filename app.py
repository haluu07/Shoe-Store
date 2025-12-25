from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file 
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, TextAreaField, FileField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, EqualTo, Email
from flask_wtf.file import FileAllowed
from flask_migrate import Migrate
from functools import wraps
import os
from datetime import datetime
import logging
import pandas as pd
from io import BytesIO

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Thay bằng key bí mật của bạn
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shoes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

# Khởi tạo Flask-Migrate
migrate = Migrate(app, db)

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    images = db.relationship('ProductImage', backref='product', lazy=True)  # Định nghĩa quan hệ với ProductImage

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('order_items', lazy=True))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('cart_items', lazy=True))
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='uix_1'),)

# Forms

class UserEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    is_admin = BooleanField('Admin Role')
    submit = SubmitField('Update')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    description = TextAreaField('Description')
    category = SelectField('Category', choices=[('Adidas', 'Adidas'), ('Nike', 'Nike'), ('Jordan', 'Jordan')], validators=[DataRequired()])
    image = FileField('Main Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])  # Hình ảnh chính
    thumbnails = FileField('Thumbnails (Multiple Images)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')], render_kw={'multiple': True})  # Hình ảnh phụ
    submit = SubmitField('Save')

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/cart')
@login_required
def cart():
    cart_items = current_user.cart_items
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash('Sản phẩm đã được thêm vào giỏ hàng!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Sản phẩm đã được xóa khỏi giỏ hàng!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    quantity = request.form.get('quantity', type=int)
    if quantity <= 0:
        return remove_from_cart(product_id)
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity = quantity
        db.session.commit()
    
    # Tính tổng giá mới của giỏ hàng
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.quantity * item.product.price for item in cart_items)

    return jsonify({
        'message': 'Cập nhật số lượng thành công!',
        'total': total
    })

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = current_user.cart_items
    if not cart_items:
        flash('Giỏ hàng của bạn đang trống.', 'error')
        return redirect(url_for('cart'))
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('checkout.html', total=total)

@app.route('/complete_checkout', methods=['POST'])
@login_required
def complete_checkout():
    payment_method = request.form.get('payment_method')
    cart_items = current_user.cart_items
    if not cart_items:
        flash('Giỏ hàng của bạn đang trống.', 'error')
        return redirect(url_for('cart'))

    total = sum(item.product.price * item.quantity for item in cart_items)
    order = Order(user_id=current_user.id, total_amount=total)
    db.session.add(order)
    db.session.commit()

    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.product.price
        )
        db.session.add(order_item)
        db.session.delete(item)
    db.session.commit()
    return render_template('order_confirmation.html')  # Chuyển hướng đến trang order_confirmation.html

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        logger.debug(f"Yêu cầu POST nhận được: {request.form}")
        form_type = request.form.get('form_type')

        # Xử lý đăng nhập
        if form_type == 'login':
            logger.debug("Xử lý form đăng nhập...")
            if login_form.validate_on_submit():
                logger.debug("Form đăng nhập hợp lệ!")
                user = User.query.filter_by(username=login_form.username.data).first()
                if user:
                    if check_password_hash(user.password, login_form.password.data):
                        login_user(user)
                        logger.debug(f"User {user.username} đã đăng nhập thành công.")
                        flash('Đăng nhập thành công!', 'success')
                        return redirect(url_for('home'))
                    else:
                        flash('Mật khẩu không đúng.', 'error')
                        logger.debug("Mật khẩu không khớp.")
                else:
                    flash('Tên đăng nhập không tồn tại.', 'error')
                    logger.debug(f"Không tìm thấy user: {login_form.username.data}")
            else:
                flash(f"Lỗi form đăng nhập: {login_form.errors}", 'error')
                logger.debug(f"Form đăng nhập lỗi: {login_form.errors}")

        # Xử lý đăng ký
        elif form_type == 'register':
            logger.debug("Xử lý form đăng ký...")
            if register_form.validate_on_submit():
                logger.debug("Form đăng ký hợp lệ!")
                if User.query.filter_by(username=register_form.username.data).first():
                    flash('Tên đăng nhập đã tồn tại.', 'error')
                    logger.debug(f"Tên đăng nhập {register_form.username.data} đã tồn tại.")
                elif User.query.filter_by(email=register_form.email.data).first():
                    flash('Email đã được sử dụng.', 'error')
                    logger.debug(f"Email {register_form.email.data} đã tồn tại.")
                else:
                    try:
                        hashed_password = generate_password_hash(register_form.password.data)
                        user = User(
                            name=register_form.name.data,
                            email=register_form.email.data,
                            username=register_form.username.data,
                            password=hashed_password
                        )
                        db.session.add(user)
                        db.session.commit()
                        login_user(user)
                        logger.debug(f"User {user.username} đã đăng ký và đăng nhập thành công.")
                        flash('Đăng ký thành công!', 'success')
                        return redirect(url_for('home'))
                    except Exception as e:
                        db.session.rollback()
                        flash('Có lỗi xảy ra khi đăng ký. Vui lòng thử lại.', 'error')
                        logger.error(f"Lỗi khi lưu user: {e}")
            else:
                flash(f"Lỗi form đăng ký: {register_form.errors}", 'error')
                logger.debug(f"Form đăng ký lỗi: {register_form.errors}")

    return render_template('auth.html', login_form=login_form, register_form=register_form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất thành công!', 'success')
    return redirect(url_for('home'))

@app.route('/search_suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('q', '').strip()
    products = []

    if query:
        # Tìm kiếm sản phẩm
        products_query = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(5).all()
        products = [
            {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'image_url': product.image_url
            } for product in products_query
        ]

    return jsonify({
        'products': products
    })

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if query:
        # Tìm kiếm sản phẩm theo tên
        products = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
    else:
        products = Product.query.all()
    return render_template('search_results.html', products=products, query=query)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
        # Tính tổng doanh thu
        total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0

        # Tính doanh thu theo ngày
        orders_by_date = db.session.query(db.func.date(Order.order_date), db.func.sum(Order.total_amount)).group_by(db.func.date(Order.order_date)).all()
        dates = [str(date) for date, _ in orders_by_date] if orders_by_date else []
        amounts = [float(amount) for _, amount in orders_by_date] if orders_by_date else []

        # Lấy danh sách tất cả đơn hàng
        orders = Order.query.all()
    except Exception as e:
        logger.error(f"Lỗi khi truy vấn dữ liệu doanh thu: {e}")
        dates = []
        amounts = []
        total_revenue = 0
        orders = []
        flash('Có lỗi xảy ra khi tải dữ liệu doanh thu.', 'error')

    return render_template('admin_dashboard.html', total_revenue=total_revenue, dates=dates, amounts=amounts, orders=orders)

# Thêm vào đầu file app.py, sau phần import
@app.template_filter('format_number')
def format_number(value):
    return "{:,.3f}".format(value)

@app.template_filter('format_currency')
def format_currency(value):
    # Chia giá trị cho 1.000 để chuyển về đơn vị x 1.000 VNĐ
    display_value = value / 1000
    # Định dạng số với 0 chữ số thập phân
    return "{:,.0f}".format(display_value) + "VNĐ"

# Thêm filter zip vào Jinja2
@app.template_filter('zip')
def zip_filter(a, b):
    return zip(a, b)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        # Lưu hình ảnh chính
        main_image = form.image.data
        main_image_filename = None
        if main_image:
            main_image_filename = secure_filename(main_image.filename)
            main_image.save(os.path.join(app.config['UPLOAD_FOLDER'], main_image_filename))
        else:
            main_image_filename = None

        # Nhân giá với 1.000 để chuyển sang đơn vị 1.000 VNĐ
        price_in_vnd = form.price.data * 1000

        # Tạo sản phẩm mới
        product = Product(
            name=form.name.data,
            price=price_in_vnd,
            description=form.description.data,
            image_url=main_image_filename,
            category=form.category.data
        )
        db.session.add(product)
        db.session.commit()

        # Lưu các hình ảnh thumbnail
        thumbnails = request.files.getlist('thumbnails')  # Lấy danh sách các file thumbnail
        for index, thumbnail in enumerate(thumbnails[:4]):  # Giới hạn tối đa 4 hình ảnh
            if thumbnail and thumbnail.filename:  # Kiểm tra xem thumbnail có hợp lệ không
                thumbnail_filename = f"{product.id}_thumbnail_{index}_{secure_filename(thumbnail.filename)}"
                thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))
                product_image = ProductImage(
                    product_id=product.id,
                    image_url=thumbnail_filename
                )
                db.session.add(product_image)
                print(f"Saved thumbnail: {thumbnail_filename}")  # Debug để kiểm tra

        db.session.commit()
        flash('Add product success', 'success')

        # Chuyển hướng dựa trên danh mục
        if product.category == 'Adidas':
            return redirect(url_for('adidas'))
        elif product.category == 'Nike':
            return redirect(url_for('nike'))
        elif product.category == 'Jordan':
            return redirect(url_for('jordan'))
        return redirect(url_for('admin_products'))
    return render_template('add_product.html', form=form)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)

    # Đặt giá trị ban đầu cho form.price (chia cho 1000 để hiển thị đúng)
    if request.method == 'GET':
        form.price.data = product.price / 1000  # Chia giá trị trong DB cho 1000 để hiển thị

    if form.validate_on_submit():
        # Cập nhật thông tin cơ bản của sản phẩm
        product.name = form.name.data
        product.price = form.price.data * 1000  # Nhân giá với 1.000 để lưu vào DB
        product.description = form.description.data
        product.category = form.category.data

        # Xử lý ảnh chính (main image)
        main_image = form.image.data
        if main_image:
            # Xóa ảnh chính cũ nếu có
            if product.image_url:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            # Lưu ảnh chính mới
            main_image_filename = secure_filename(main_image.filename)
            main_image.save(os.path.join(app.config['UPLOAD_FOLDER'], main_image_filename))
            product.image_url = main_image_filename

        # Xử lý ảnh thumbnail
        thumbnails = request.files.getlist('thumbnails')  # Lấy danh sách các file thumbnail mới
        if thumbnails and thumbnails[0].filename:  # Kiểm tra xem có file nào được upload không
            # Xóa các ảnh thumbnail cũ
            for image in product.images:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_url)
                if os.path.exists(image_path):
                    os.remove(image_path)
                db.session.delete(image)

            # Lưu các ảnh thumbnail mới
            for index, thumbnail in enumerate(thumbnails[:4]):  # Giới hạn tối đa 4 ảnh
                if thumbnail and thumbnail.filename:
                    thumbnail_filename = f"{product.id}_thumbnail_{index}_{secure_filename(thumbnail.filename)}"
                    thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))
                    product_image = ProductImage(
                        product_id=product.id,
                        image_url=thumbnail_filename
                    )
                    db.session.add(product_image)
                    print(f"Saved new thumbnail: {thumbnail_filename}")  # Debug

        try:
            db.session.commit()
            flash('Product updated successfully.', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error occurred while updating product: {str(e)}', 'error')
            logger.error(f"Error updating product {id}: {e}")

    return render_template('edit_product.html', form=form, product=product)

@app.route('/admin/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        # Xóa các bản ghi trong order_item liên quan đến sản phẩm
        order_items = OrderItem.query.filter_by(product_id=product.id).all()
        for item in order_items:
            db.session.delete(item)

        # Xóa các bản ghi trong cart liên quan đến sản phẩm
        cart_items = Cart.query.filter_by(product_id=product.id).all()
        for item in cart_items:
            db.session.delete(item)

        # Xóa các ảnh thumbnail liên quan
        for image in product.images:
            # Xóa file ảnh thumbnail từ thư mục static/images
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_url)
            if os.path.exists(image_path):
                os.remove(image_path)
            db.session.delete(image)

        # Xóa ảnh chính nếu có
        if product.image_url:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_url)
            if os.path.exists(image_path):
                os.remove(image_path)

        # Xóa sản phẩm
        db.session.delete(product)
        db.session.commit()
        flash('Sản phẩm đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Có lỗi xảy ra khi xóa sản phẩm: {str(e)}', 'error')
        logger.error(f"Lỗi khi xóa sản phẩm {id}: {e}")
    return redirect(url_for('admin_products'))

@app.route('/adidas')
def adidas():
    # Lấy danh sách sản phẩm thuộc danh mục Adidas (giả sử có trường category trong Product)
    products = Product.query.filter_by(category='Adidas').all()
    return render_template('adidas.html', products=products)

@app.route('/nike')
def nike():
    # Lấy danh sách sản phẩm thuộc danh mục Nike
    products = Product.query.filter_by(category='Nike').all()
    return render_template('nike.html', products=products)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/jordan')
def jordan():
    # Lấy danh sách sản phẩm thuộc danh mục Jordan
    products = Product.query.filter_by(category='Jordan').all()
    return render_template('jordan.html', products=products)

@app.route('/admin/orders/delete/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    try:
        # Xóa tất cả các OrderItem liên quan đến đơn hàng
        for item in order.items:
            db.session.delete(item)
        # Xóa đơn hàng
        db.session.delete(order)
        db.session.commit()
        flash('Đơn hàng đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Có lỗi xảy ra khi xóa đơn hàng: ' + str(e), 'error')
        logger.error(f"Lỗi khi xóa đơn hàng {order_id}: {e}")
    return redirect(url_for('admin_dashboard'))

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/blog')
def blog():
    # List of mock blog posts (can be replaced with data from a database)
    posts = [
        {
            'id': 1,
            'title': 'Top 5 Hottest Sneaker Models of 2025',
            'image_url': 'static/images/blog1.jpg',
            'date': '04/07/2025',
            'author': 'Linh Shoe Team',
            'excerpt': 'Discover the 5 sneaker models that are making waves in 2025, from design to style!'
        },
        {
            'id': 2,
            'title': 'How to Choose Shoes That Match Your Style',
            'image_url': 'static/images/blog2.jpg',
            'date': '04/07/2025',
            'author': 'Linh Shoe Team',
            'excerpt': 'A detailed guide on how to choose shoes that suit your personal style, from casual to elegant.'
        },
        {
            'id': 3,
            'title': 'The History of Adidas Originals Shoes',
            'image_url': 'static/images/blog3.jpg',
            'date': '04/07/2025',
            'author': 'Linh Shoe Team',
            'excerpt': 'Learn about the development journey of the Adidas Originals shoe line through the decades.'
        }
    ]
    return render_template('blog.html', posts=posts)
@app.route('/admin/export_orders_to_excel')
@login_required
@admin_required
def export_orders_to_excel():
    try:
        # Kiểm tra xem pandas và openpyxl đã được cài đặt chưa
        try:
            import pandas as pd
            import openpyxl
        except ImportError as e:
            logger.error(f"Thư viện cần thiết chưa được cài đặt: {e}")
            flash('Vui lòng cài đặt pandas và openpyxl để sử dụng tính năng xuất Excel.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Lấy danh sách đơn hàng
        orders = Order.query.all()
        if not orders:
            flash('Không có đơn hàng nào để xuất.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Tạo dữ liệu cho Excel với kiểm tra kỹ lưỡng
        data = {
            'ID Đơn Hàng': [],
            'Người Dùng': [],
            'Tổng Tiền': [],
            'Ngày Đặt Hàng': [],
            'Sản Phẩm': []
        }

        for order in orders:
            # Kiểm tra các trường bắt buộc
            if not hasattr(order, 'id') or order.id is None:
                logger.warning(f"Đơn hàng không có ID: {order}")
                continue

            # Thêm dữ liệu vào từng cột
            data['ID Đơn Hàng'].append(order.id)
            data['Người Dùng'].append(order.user.username if order.user and hasattr(order.user, 'username') else 'N/A')
            # Định dạng Tổng Tiền bằng filter format_currency
            total_amount = order.total_amount if order.total_amount is not None else 0.0
            data['Tổng Tiền'].append(app.jinja_env.filters['format_currency'](total_amount))
            data['Ngày Đặt Hàng'].append(order.order_date.strftime('%Y-%m-%d %H:%M:%S') if order.order_date else 'N/A')

            # Xử lý danh sách sản phẩm
            products_str = 'N/A'
            if order.items:
                try:
                    products_list = []
                    for item in order.items:
                        product_name = item.product.name if item.product and hasattr(item.product, 'name') else 'N/A'
                        quantity = item.quantity if item.quantity is not None else 0
                        # Định dạng Giá bằng filter format_currency
                        price = item.price if item.price is not None else 0.0
                        formatted_price = app.jinja_env.filters['format_currency'](price)
                        products_list.append(f"{product_name} (SL: {quantity}, Giá: {formatted_price})")
                    products_str = ', '.join(products_list) if products_list else 'N/A'
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý sản phẩm của đơn hàng {order.id}: {e}")
                    products_str = 'Lỗi khi lấy sản phẩm'
            data['Sản Phẩm'].append(products_str)

        # Debug dữ liệu trước khi tạo DataFrame
        logger.debug(f"Dữ liệu trước khi tạo DataFrame: {data}")

        # Kiểm tra xem dữ liệu có rỗng không
        if not data['ID Đơn Hàng']:
            flash('Không có đơn hàng hợp lệ để xuất.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Tạo DataFrame
        df = pd.DataFrame(data)

        # Tạo file Excel trong bộ nhớ
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Orders')
            # Lấy workbook và worksheet để định dạng
            workbook = writer.book
            worksheet = writer.sheets['Orders']
            # Định dạng cột Tổng Tiền và Sản Phẩm thành text để tránh Excel tự động định dạng
            for col in ['C', 'E']:  # Cột C: Tổng Tiền, Cột E: Sản Phẩm
                for cell in worksheet[f"{col}"]:
                    cell.number_format = '@'  # Định dạng text
        output.seek(0)

        # Gửi file về client
        return send_file(
            output,
            download_name="orders.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Lỗi khi xuất Excel: {e}")
        flash('Có lỗi xảy ra khi xuất file Excel.', 'error')
        return redirect(url_for('admin_dashboard'))
    
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# Route để chỉnh sửa người dùng
@app.route('/admin/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        # Kiểm tra email có bị trùng không (trừ email của chính user đang chỉnh sửa)
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user and existing_user.id != user.id:
            flash('Email đã được sử dụng bởi người dùng khác.', 'error')
            return render_template('edit_user.html', form=form, user=user)
        
        # Cập nhật thông tin người dùng
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        try:
            db.session.commit()
            flash('Thông tin người dùng đã được cập nhật thành công.', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra khi cập nhật người dùng: {str(e)}', 'error')
            logger.error(f"Lỗi khi cập nhật người dùng {id}: {e}")
    
    return render_template('edit_user.html', form=form, user=user)

# Thêm filter yesno
@app.template_filter('yesno')
def yesno_filter(value, yes_no_str):
    yes, no = yes_no_str.split(',')
    return yes if value else no

# Route để xóa người dùng
@app.route('/admin/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    # Không cho phép xóa chính mình
    if user.id == current_user.id:
        flash('Bạn không thể xóa chính mình!', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        # Xóa các bản ghi liên quan trong các bảng khác trước
        # Xóa giỏ hàng của người dùng
        Cart.query.filter_by(user_id=user.id).delete()
        # Xóa đơn hàng và các mục trong đơn hàng
        orders = Order.query.filter_by(user_id=user.id).all()
        for order in orders:
            OrderItem.query.filter_by(order_id=order.id).delete()
            db.session.delete(order)
        # Xóa người dùng
        db.session.delete(user)
        db.session.commit()
        flash('Người dùng đã được xóa thành công.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Có lỗi xảy ra khi xóa người dùng: {str(e)}', 'error')
        logger.error(f"Lỗi khi xóa người dùng {id}: {e}")
    
    return redirect(url_for('admin_users'))
    
if __name__ == '__main__':
    with app.app_context():
        logger.debug("Đang tạo database...")
        db.create_all()
        logger.debug("Database đã được tạo thành công!")
    app.run(debug=True)