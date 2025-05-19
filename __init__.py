from .routes import main, login_manager

def create_app():
    app = Flask(__name__)
    app.secret_key = 'ims_super_secret_456'
    app.register_blueprint(main)
    login_manager.init_app(app)
    return app

