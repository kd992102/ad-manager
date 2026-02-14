import os
from flask import Flask
from flask_login import LoginManager
from flask_session import Session # 如果您有決定用 Server-Side Session
from flask_wtf.csrf import CSRFProtect # <--- 【關鍵修正 1】引入套件
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "請先登入以存取此頁面。"
login_manager.login_message_category = "warning"

# 初始化 CSRF 保護
csrf = CSRFProtect() # <--- 【關鍵修正 2】建立全域物件

def create_app():
    app = Flask(__name__)
    
    # --- 設定與 Config ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    
    # AD 設定
    app.config['AD_SERVER'] = os.getenv('AD_SERVER')
    app.config['AD_USER'] = os.getenv('AD_USER')
    app.config['AD_PASS'] = os.getenv('AD_PASSWORD')
    app.config['AD_BASEDN'] = os.getenv('AD_BASEDN')
    app.config['AD_DOMAIN'] = os.getenv('AD_DOMAIN')

    # Session 安全設定 (建議)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_TYPE'] = 'filesystem' # 如果有裝 Flask-Session 再開這行
    Session(app) # 如果有裝 Flask-Session 再開這行

    # 初始化套件
    login_manager.init_app(app)
    csrf.init_app(app) # <--- 這裡現在不會報錯了，因為上面有定義 csrf

    # --- 註冊 Blueprints ---
    from app.routes_dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes_auth import auth_bp
    app.register_blueprint(auth_bp)

    # 【新增】註冊 Setup 路由
    from app.routes_setup import bp as setup_bp
    app.register_blueprint(setup_bp)

    try:
        from app.routes_main import bp as main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass

    # --- User Loader ---
    from app.routes_auth import User
    @login_manager.user_loader
    def load_user(user_id):
        return User(id=user_id)

    return app