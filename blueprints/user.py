from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user,logout_user
from passlib.hash import sha256_crypt
from extentions import db
from models.Payment import Payment
from models.cart import Cart
from models.cart_item import CartItem
from models.product import Product
from models.user import User
import requests
import config

app = Blueprint("user", __name__)


@app.route('/user/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('user.dashboard'))
        return render_template('user/login.html')
    else:
        register = request.form.get('register', None)
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        phone = request.form.get('phone', None)
        address = request.form.get('address', None)

        if register != None:
            user = User.query.filter(User.username == username).first()
            if user != None:
                flash('نام کاربری دیگری انتخاب کنید')
                return redirect(url_for('user.login'))

            user = User(username=username, password=sha256_crypt.encrypt(password), phone=phone, address=address)
            db.session.add(user)
            db.session.commit()
            login_user(user)

            return redirect(url_for('user.dashboard'))

        else:
            user = User.query.filter(User.username == username).first()
            if user == None:
                flash('نام کاربری یا رمز اشتباه است')
                return redirect(url_for('user.login'))

            if sha256_crypt.verify(password, user.password):
                login_user(user)
                return redirect(url_for('user.dashboard'))
            else:
                flash('نام کاربری یا رمز اشتباه است')
                return redirect(url_for('user.login'))


@app.route('/add-to-cart', methods=['GET'])
@login_required
def add_to_cart():
    id = request.args.get('id')
    product = Product.query.filter(Product.id == id).first_or_404()

    cart = current_user.carts.filter(Cart.status == 'pending').first()
    if cart == None:
        cart = Cart()
        current_user.carts.append(cart)
        db.session.add(cart)

    cart_item = cart.cart_items.filter(CartItem.product == product).first()
    if cart_item == None:
        item = CartItem(quantity=1)
        item.price = product.price
        item.cart = cart
        item.product = product
        db.session.add(item)
    else:
        cart_item.quantity += 1

    db.session.commit()

    return redirect(url_for('user.cart'))


@app.route('/remove-from-cart', methods=['GET'])
@login_required
def remove_from_cart():
    id = request.args.get('id')
    cart_item = CartItem.query.filter(CartItem.id == id).first_or_404()
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
    else:
        db.session.delete(cart_item)

    db.session.commit()
    return redirect(url_for('user.cart'))


@app.route('/cart', methods=['GET'])
@login_required
def cart():
    cart = current_user.carts.filter(Cart.status == "pending").first()
    return render_template('user/cart.html', cart=cart)


@app.route('/payment', methods=['GET'])
@login_required
def payment():
    cart = current_user.carts.filter(Cart.status == 'pending').first()

    r = requests.post(config.PAYMENT_FIRST_REQUEST_URL,
                      data={
                          'api': config.PAYMENT_MERCHANT,
                          'amount': cart.total_price(),
                          'callback': config.PAYMENT_CALLBACK
                      })
    token = r.json()['result']['token']
    url = r.json()['result']['url']

    pay = Payment(price=cart.total_price(), token=token)
    pay.cart = cart
    db.session.add(pay)
    db.session.commit()

    return redirect(url)


@app.route('/verify', methods=['GET'])
@login_required
def verify():
    token = request.args.get('token')
    pay = Payment.query.filter(Payment.token == token).first_or_404()
    r = requests.post(config.PAYMENT_VERIFY_REQUEST_URL,
                      data={
                          'api': 'sandbox',
                          'amount': pay.price,
                          'token': token
                      })

    pay_status = bool(r.json()['success'])
    if pay_status:
        transaction_id = r.json()['result']['transaction_id']
        refid = r.json()['result']['refid']
        card_pan = r.json()['result']['card_pan']

        pay.card_pan = card_pan
        pay.transaction_id = transaction_id
        pay.refid = refid
        pay.status = 'success'
        pay.cart.status = 'paid'
        flash("پرداخت موفق آمیز بود")
    else:
        flash("پرداخت با خطا مواجه شد")
        pay.status = 'failed'

    db.session.commit()

    return redirect(url_for('user.dashboard'))


@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "GET":
        return render_template('user/dashboard.html')
    else:
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        phone = request.form.get('phone', None)
        address = request.form.get('address', None)

        if current_user.username != username:
            user = User.query.filter(User.username == username).first()
            if user != None:
                flash('نام کاربری از قبل انتخاب شده است')
                return redirect(url_for('user.dashboard'))
            else:
                current_user.username = username

        if password != None:
            current_user.password = sha256_crypt.encrypt(password)

        current_user.address = address
        current_user.phone = phone
        db.session.commit()

        flash('تغییرات با موفقیت ثبت شد')
        return redirect(url_for('user.dashboard'))


@app.route('/user/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash("با موفقیت خارج شدید")
    return redirect('/')



@app.route('/user/dashboard/order/<id>', methods=['GET'])
@login_required
def order(id):
    cart = current_user.carts.filter(Cart.id == id).first_or_404()
    return render_template('user/order.html', cart=cart)
