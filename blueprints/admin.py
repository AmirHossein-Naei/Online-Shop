from flask import Blueprint, current_app, render_template, request, session, redirect, abort, url_for, flash
import config
from models.cart import Cart
from models.product import Product
from extentions import db
import os
from PIL import Image, ImageOps

app = Blueprint("admin", __name__)


@app.before_request
def before_request():
    if session.get('admin_login', None) == None and request.endpoint != "admin.login":
        abort(403)


@app.route('/admin/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get('username', None)
        password = request.form.get('password', None)

        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session['admin_login'] = username
            return redirect("/admin/dashboard")
        else:
            return redirect("/admin/login")
    else:
        return render_template("admin/login.html")


@app.route('/admin/dashboard', methods=["GET"])
def dashboard():
    carts = Cart.query.filter(Cart.status != "pending").all()
    return render_template("admin/dashboard.html", carts=carts)


@app.route('/admin/dashboard/order/<id>', methods=["GET", "POST"])
def order(id):
    cart = Cart.query.filter(Cart.id == id).first_or_404()

    if request.method == "GET":
        return render_template("admin/order.html", cart=cart)
    else:
        status = request.form.get('status')
        cart.status = status
        db.session.commit()
        flash("وضعیت سفارش با موفقیت تغییر کرد")
        return redirect(url_for('admin.order', id=id))

def pasi(file, product_id, size=500):

    cover_dir = os.path.join(current_app.root_path, 'static', 'cover')
    os.makedirs(cover_dir, exist_ok=True)
    
    image_path = os.path.join(cover_dir, f'{product_id}.jpg')
    
    img = Image.open(file.stream)
    
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    img_square = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
    
    img_square.save(image_path, 'JPEG', quality=95, optimize=True)
    
    return True


@app.route('/admin/dashboard/products', methods=["GET", "POST"])
def products():
    if request.method == "GET":
        products = Product.query.all()
        return render_template("admin/products.html", products=products)
    else:
        name = request.form.get('name', None)
        description = request.form.get('description', None)
        price = request.form.get('price', None)
        active = request.form.get('active', None)
        file = request.files.get('cover', None)

     
        if not name or not price:
            flash("نام و قیمت الزامی هستند!", "error")
            return redirect(url_for('admin.products'))

        p = Product(name=name, description=description, price=price)
        p.active = 1 if active else 0

        try:
            db.session.add(p)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("محصولی با این نام قبلاً ثبت شده است!", "error")
            return redirect(url_for('admin.products'))

        if file and file.filename:
            success = pasi(file, p.id)
            if not success:
                flash("خطا در پردازش تصویر! لطفاً دوباره تلاش کنید.", "error")

                db.session.delete(p)
                db.session.commit()
                return redirect(url_for('admin.products'))

        flash("محصول جدید با موفقیت اضافه شد!", "success")
        return render_template("admin/done.html")


@app.route('/admin/dashboard/edit-product/<id>', methods=["GET", "POST"])
def edit_product(id):
    product = Product.query.filter(Product.id == id).first_or_404()

    if request.method == "GET":
        return render_template("admin/edit-product.html", product=product)
    else:
        name = request.form.get('name', None)
        description = request.form.get('description', None)
        price = request.form.get('price', None)
        active = request.form.get('active', None)
        file = request.files.get('cover', None)


        if not name or not price:
            flash("نام و قیمت الزامی هستند!", "error")
            return redirect(url_for('admin.edit_product', id=id))

        product.name = name
        product.description = description
        product.price = price
        product.active = 1 if active else 0

        db.session.commit()

        if file and file.filename:

            oip = os.path.join(current_app.root_path, 'static', 'cover', f'{product.id}.jpg')
            if os.path.exists(oip):
                try:
                    os.remove(oip)
                except:
                    pass 
            
            success = pasi(file, product.id)
            if not success:
                flash("خطا در پردازش تصویر! لطفاً دوباره تلاش کنید.")
                return redirect(url_for('admin.edit_product', id=id))

        flash("تغییرات با موفقیت ثبت شد!")
        return redirect(url_for("admin.edit_product", id=id))