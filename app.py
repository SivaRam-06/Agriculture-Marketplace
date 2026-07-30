import os
from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DecimalField, IntegerField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-agriculture-marketplace'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['JSON_SORT_KEYS'] = False
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['BOOTSTRAP_SERVE_LOCAL'] = True

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

wishlist = db.Table(
    'wishlist',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='buyer')
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    products = db.relationship('Product', backref='farmer', lazy=True)
    orders = db.relationship('Order', backref='buyer', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='buyer', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, order_by='Notification.created_at.desc()')
    wishlist = db.relationship('Product', secondary=wishlist, lazy='dynamic', back_populates='wishlisted_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_farmer(self):
        return self.role == 'farmer'

    @property
    def is_buyer(self):
        return self.role == 'buyer'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='category', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(50), default='kg')
    location = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    organic = db.Column(db.Boolean, default=False)
    certification = db.Column(db.String(100), nullable=True)
    delivery_radius = db.Column(db.Integer, default=50)
    minimum_order = db.Column(db.Integer, default=1)
    stock_status = db.Column(db.String(20), default='in_stock')
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)
    wishlisted_by = db.relationship('User', secondary=wishlist, lazy='dynamic', back_populates='wishlist')

    @property
    def final_price(self):
        if self.discount:
            return float(self.price) * (1 - self.discount / 100)
        return float(self.price)

    @property
    def rating(self):
        if not self.reviews:
            return 0
        return sum(r.rating for r in self.reviews) / len(self.reviews)


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(20), default='Pending')
    status = db.Column(db.String(20), default='Pending')
    delivery_address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    label = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)


class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(min=8, max=15)])
    role = SelectField('Role', choices=[('buyer', 'Buyer'), ('farmer', 'Farmer')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')

    def validate_confirm_password(self, field):
        if field.data != self.password.data:
            raise ValidationError('Passwords do not match.')


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')


class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')], validators=[DataRequired()])
    comment = TextAreaField('Review', validators=[DataRequired()])
    submit = SubmitField('Submit Review')


class ProductForm(FlaskForm):
    name = StringField('Crop Name', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = DecimalField('Price', validators=[DataRequired()])
    discount = IntegerField('Discount (%)', default=0)
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    unit = StringField('Unit', default='kg')
    location = StringField('Location', validators=[DataRequired()])
    district = StringField('District', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    organic = BooleanField('Organic')
    certification = StringField('Certification')
    delivery_radius = IntegerField('Delivery Radius (km)', default=50)
    minimum_order = IntegerField('Minimum Order', default=1)
    stock_status = SelectField('Stock Status', choices=[('in_stock', 'In Stock'), ('limited', 'Limited'), ('out_of_stock', 'Out of Stock')], default='in_stock')
    is_featured = BooleanField('Featured')
    images = FileField('Images')
    submit = SubmitField('Save Crop')


class CheckoutForm(FlaskForm):
    address = TextAreaField('Shipping Address', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=8, max=15)])
    payment_method = SelectField('Payment Method', choices=[('Cash on Delivery', 'Cash on Delivery'), ('UPI', 'UPI'), ('Credit Card', 'Credit Card'), ('Debit Card', 'Debit Card')], validators=[DataRequired()])
    submit = SubmitField('Place Order')


class AddressForm(FlaskForm):
    label = StringField('Label', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=8, max=15)])
    submit = SubmitField('Save Address')


@app.before_request
def before_request():
    pass


@app.context_processor
def inject_globals():
    categories = Category.query.order_by(Category.name).all()
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    notification_count = 0
    if current_user.is_authenticated:
        notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return dict(categories=categories, cart_count=cart_count, notification_count=notification_count)


def seed_data():
    if User.query.filter_by(email='admin@example.com').first():
        return
    admin = User(name='Admin User', email='admin@example.com', role='admin', is_verified=True)
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()

    categories = [
        ('Rice', 'rice', 'High quality rice cultivated with sustainable methods.'),
        ('Wheat', 'wheat', 'Fresh wheat harvested at optimal maturity.'),
        ('Maize', 'maize', 'Nutrient-rich maize for feed and food.'),
        ('Tomato', 'tomato', 'Premium tomatoes from greenhouse farms.'),
        ('Onion', 'onion', 'Fresh onions with strong storage life.'),
        ('Organic Products', 'organic-products', 'Certified organic produce.'),
    ]
    for name, slug, desc in categories:
        db.session.add(Category(name=name, slug=slug, description=desc))

    farmer = User(name='Ravi Kumar', email='farmer@example.com', role='farmer', phone='9876543210', city='Nagpur', address='Village Farm Road', is_verified=True)
    farmer.set_password('farmer123')
    buyer = User(name='Ananya Shah', email='buyer@example.com', role='buyer', phone='9123456780', city='Pune', address='Green Park Lane', is_verified=True)
    buyer.set_password('buyer123')
    db.session.add_all([farmer, buyer])
    db.session.flush()

    cats = Category.query.all()
    products = [
        Product(name='Basmati Rice', slug='basmati-rice', description='Premium aromatic rice with long grains.', price=Decimal('95.00'), discount=10, quantity=120, unit='kg', location='Nagpur', district='Nagpur', state='Maharashtra', organic=True, certification='Organic', delivery_radius=80, minimum_order=10, stock_status='in_stock', is_featured=True, farmer_id=farmer.id, category_id=cats[0].id),
        Product(name='Fresh Tomato', slug='fresh-tomato', description='Juicy tomatoes from local farms.', price=Decimal('40.00'), discount=5, quantity=90, unit='kg', location='Pune', district='Pune', state='Maharashtra', organic=False, certification='', delivery_radius=50, minimum_order=5, stock_status='limited', is_featured=True, farmer_id=farmer.id, category_id=cats[3].id),
        Product(name='Organic Wheat', slug='organic-wheat', description='Clean wheat for everyday use.', price=Decimal('70.00'), discount=8, quantity=60, unit='kg', location='Satara', district='Satara', state='Maharashtra', organic=True, certification='USDA', delivery_radius=60, minimum_order=8, stock_status='in_stock', is_featured=False, farmer_id=farmer.id, category_id=cats[1].id),
    ]
    db.session.add_all(products)
    db.session.flush()

    for product in products:
        db.session.add(ProductImage(filename='sample.jpg', product_id=product.id))

    db.session.add(Coupon(code='AGRI10', discount_percent=10, is_active=True))
    db.session.add(Notification(title='Welcome', message='Welcome to AgriMarket! Your account is ready.', user_id=buyer.id))
    db.session.commit()


@app.route('/')
def home():
    featured_products = Product.query.filter_by(is_active=True, is_featured=True).order_by(Product.created_at.desc()).limit(6).all()
    latest_products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(6).all()
    farmers = User.query.filter_by(role='farmer', is_verified=True).limit(6).all()
    return render_template('home.html', featured_products=featured_products, latest_products=latest_products, farmers=farmers)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Welcome back!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user.role == 'farmer':
                return redirect(url_for('farmer_dashboard'))
            return redirect(url_for('buyer_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data.lower(), phone=form.phone.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(name=form.name.data, email=form.email.data, subject=form.subject.data, message=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash('Thanks for reaching out. We will respond shortly.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/marketplace')
def marketplace():
    query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    organic_only = request.args.get('organic', type=int)
    page = request.args.get('page', 1, type=int)

    products_query = Product.query.filter_by(is_active=True)
    if query:
        products_query = products_query.filter(Product.name.ilike(f'%{query}%'))
    if category_id:
        products_query = products_query.filter_by(category_id=category_id)
    if organic_only:
        products_query = products_query.filter_by(organic=True)

    products = products_query.order_by(Product.created_at.desc()).paginate(page=page, per_page=9)
    return render_template('marketplace.html', products=products, query=query, category_id=category_id or '', organic_only=organic_only or 0)


@app.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    form = ReviewForm()
    reviews = product.reviews.order_by(Review.created_at.desc()).all()
    related = Product.query.filter(Product.id != product.id, Product.category_id == product.category_id, Product.is_active.is_(True)).limit(4).all()
    return render_template('product.html', product=product, form=form, reviews=reviews, related=related)


@app.route('/product/<slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(rating=int(form.rating.data), comment=form.comment.data, buyer_id=current_user.id, product_id=product.id)
        db.session.add(review)
        db.session.commit()
        flash('Review submitted successfully.', 'success')
    return redirect(url_for('product_detail', slug=slug))


@app.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    product = Product.query.get_or_404(product_id)
    if product in current_user.wishlist:
        current_user.wishlist.remove(product)
    else:
        current_user.wishlist.append(product)
    db.session.commit()
    return jsonify({'success': True, 'added': product in current_user.wishlist})


@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.quantity * item.product.final_price for item in items)
    tax = subtotal * 0.08
    delivery = 40 if subtotal > 0 else 0
    total = subtotal + tax + delivery
    return render_template('cart.html', items=items, subtotal=subtotal, tax=tax, delivery=delivery, total=total)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(item)
    db.session.commit()
    flash(f'{product.name} added to cart.', 'success')
    return redirect(request.referrer or url_for('marketplace'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    quantity = max(1, int(request.form.get('quantity', 1)))
    item.quantity = quantity
    db.session.commit()
    flash('Cart updated.', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))
    form = CheckoutForm()
    if form.validate_on_submit():
        subtotal = sum(item.quantity * item.product.final_price for item in items)
        tax = subtotal * 0.08
        delivery = 40 if subtotal > 0 else 0
        total = subtotal + tax + delivery
        order_number = f'AGR{datetime.utcnow().strftime("%Y%m%d%H%M%S")}'
        order = Order(order_number=order_number, buyer_id=current_user.id, total_amount=total, payment_method=form.payment_method.data, payment_status='Paid', status='Pending', delivery_address=form.address.data, phone=form.phone.data)
        db.session.add(order)
        db.session.flush()
        for item in items:
            db.session.add(OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, price=item.product.final_price))
        for item in items:
            db.session.delete(item)
        db.session.add(Notification(title='Order Confirmed', message=f'Your order {order_number} has been received.', user_id=current_user.id))
        db.session.commit()
        flash('Order placed successfully.', 'success')
        return redirect(url_for('orders'))
    form.address.data = current_user.address or ''
    form.phone.data = current_user.phone or ''
    return render_template('checkout.html', form=form, items=items)


@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)


@app.route('/notifications')
@login_required
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for note in notes:
        note.is_read = True
    db.session.commit()
    return render_template('notifications.html', notes=notes)


@app.route('/farmer/dashboard')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer' and current_user.role != 'admin':
        abort(403)
    products = Product.query.filter_by(farmer_id=current_user.id).order_by(Product.created_at.desc()).all()
    total_crops = len(products)
    available_stock = sum(p.quantity for p in products)
    completed_orders = OrderItem.query.join(Order).filter(Order.status == 'Delivered').count()
    revenue = sum(float(item.price * item.quantity) for item in OrderItem.query.join(Product).filter(Product.farmer_id == current_user.id).all())
    return render_template('farmer/dashboard.html', products=products, total_crops=total_crops, available_stock=available_stock, completed_orders=completed_orders, revenue=revenue)


@app.route('/farmer/product/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if current_user.role != 'farmer' and current_user.role != 'admin':
        abort(403)
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        product = Product(name=form.name.data, slug=form.name.data.lower().replace(' ', '-'), description=form.description.data, price=form.price.data, discount=form.discount.data or 0, quantity=form.quantity.data, unit=form.unit.data, location=form.location.data, district=form.district.data, state=form.state.data, organic=form.organic.data, certification=form.certification.data, delivery_radius=form.delivery_radius.data, minimum_order=form.minimum_order.data, stock_status=form.stock_status.data, is_featured=form.is_featured.data, farmer_id=current_user.id, category_id=form.category_id.data)
        db.session.add(product)
        db.session.flush()
        if form.images.data:
            filename = secure_filename(form.images.data.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.images.data.save(path)
            db.session.add(ProductImage(filename=filename, product_id=product.id))
        db.session.commit()
        flash('Crop added successfully.', 'success')
        return redirect(url_for('farmer_dashboard'))
    return render_template('farmer/product_form.html', form=form, title='Add Crop')


@app.route('/farmer/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'farmer' and current_user.role != 'admin':
        abort(403)
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != current_user.id and current_user.role != 'admin':
        abort(403)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    if form.validate_on_submit():
        product.name = form.name.data
        product.slug = form.name.data.lower().replace(' ', '-')
        product.description = form.description.data
        product.price = form.price.data
        product.discount = form.discount.data or 0
        product.quantity = form.quantity.data
        product.unit = form.unit.data
        product.location = form.location.data
        product.district = form.district.data
        product.state = form.state.data
        product.organic = form.organic.data
        product.certification = form.certification.data
        product.delivery_radius = form.delivery_radius.data
        product.minimum_order = form.minimum_order.data
        product.stock_status = form.stock_status.data
        product.is_featured = form.is_featured.data
        product.category_id = form.category_id.data
        db.session.commit()
        flash('Crop updated successfully.', 'success')
        return redirect(url_for('farmer_dashboard'))
    return render_template('farmer/product_form.html', form=form, title='Edit Crop', product=product)


@app.route('/farmer/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'farmer' and current_user.role != 'admin':
        abort(403)
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != current_user.id and current_user.role != 'admin':
        abort(403)
    db.session.delete(product)
    db.session.commit()
    flash('Crop removed.', 'info')
    return redirect(url_for('farmer_dashboard'))


@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if current_user.role != 'buyer' and current_user.role != 'admin':
        abort(403)
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    wishlist_products = current_user.wishlist.limit(6).all()
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('buyer/dashboard.html', orders=orders, wishlist_products=wishlist_products, cart_items=cart_items)


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    user_count = User.query.count()
    farmer_count = User.query.filter_by(role='farmer').count()
    buyer_count = User.query.filter_by(role='buyer').count()
    order_count = Order.query.count()
    revenue = sum(float(order.total_amount) for order in Order.query.all())
    latest_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', user_count=user_count, farmer_count=farmer_count, buyer_count=buyer_count, order_count=order_count, revenue=revenue, latest_users=latest_users)


@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(6).all()
    return jsonify([{'id': p.id, 'name': p.name, 'slug': p.slug} for p in products])


@app.route('/api/notifications')
def notifications_api():
    if not current_user.is_authenticated:
        return jsonify([])
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    return jsonify([{'title': n.title, 'message': n.message, 'read': n.is_read} for n in notes])


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


@app.route('/maintenance')
def maintenance():
    return render_template('maintenance.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
