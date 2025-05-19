from flask import Flask
from .routes import main, login_manager  # ✅ Import main and login_manager

def create_app():
    app = Flask(__name__)
    app.secret_key = 'ims_super_secret_456'  # 🔐 Use a strong secret key for sessions

    app.register_blueprint(main)
    login_manager.init_app(app)  # ✅ Init Flask-Login

    return app

