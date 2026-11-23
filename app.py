from flask import Flask, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect
from blueprints.general import app as general
from blueprints.user import app as user
from blueprints.admin import app as admin
import config
import extentions
from flask_login import LoginManager
from models.user import User
#this is just for test
print("heloo")
app = Flask(__name__)
app.register_blueprint(general)
app.register_blueprint(user)
app.register_blueprint(admin)

app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config['SECRET_KEY'] = config.SECRET_KEY
extentions.db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == user_id).first()


@login_manager.unauthorized_handler
def unauthorized():
    flash('وارد حساب کاربریتان شوید')
    return redirect(url_for('user.login'))


@app.context_processor
def inject_dict_for_all_templates():
    return dict(myconfig=config)


with app.app_context():
    extentions.db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
