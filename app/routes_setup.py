import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ldap3 import Server, Connection, NONE
import ssl

bp = Blueprint('setup', __name__)

@bp.route('/setup', methods=['GET'])
def index():
    # 如果已經設定過了，就禁止進入 setup 頁面 (安全性考量)
    if current_app.config.get('AD_SERVER'):
        return redirect(url_for('dashboard.index'))
    return render_template('setup.html')

@bp.route('/setup/init', methods=['POST'])
def init_config():
    # 1. 獲取表單資料
    server_ip = request.form.get('ad_server')
    domain = request.form.get('ad_domain')
    basedn = request.form.get('ad_basedn')
    user = request.form.get('ad_user')
    password = request.form.get('ad_password')

    # 2. 測試連線 (不依賴 config，直接用輸入值測試)
    try:
        tls_ctx = ssl.create_default_context()
        tls_ctx.check_hostname = False
        tls_ctx.verify_mode = ssl.CERT_NONE
        
        server = Server(server_ip, use_ssl=True, tls=None, get_info=NONE)
        conn = Connection(server, user=user, password=password, authentication='SIMPLE')
        
        if not conn.bind():
            flash(f"連線失敗: {conn.result['description']}", "danger")
            return redirect(url_for('setup.index'))
        
        conn.unbind()
        
    except Exception as e:
        flash(f"連線發生錯誤: {str(e)}", "danger")
        return redirect(url_for('setup.index'))

    # 3. 連線成功，寫入 .env 檔案
    try:
        # 產生一個隨機的 SECRET_KEY
        import secrets
        secret_key = secrets.token_hex(16)

        env_content = f"""# AD Management System Configuration
AD_SERVER={server_ip}
AD_DOMAIN={domain}
AD_BASEDN={basedn}
AD_USER={user}
AD_PASSWORD={password}
SECRET_KEY={secret_key}
"""
        # 寫入專案根目錄的 .env
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        # 4. 更新當前執行的 App Config (讓使用者不用重啟就能立刻使用)
        current_app.config['AD_SERVER'] = server_ip
        current_app.config['AD_DOMAIN'] = domain
        current_app.config['AD_BASEDN'] = basedn
        current_app.config['AD_USER'] = user
        current_app.config['AD_PASS'] = password
        current_app.config['SECRET_KEY'] = secret_key
        
        flash("系統初始化成功！請登入。", "success")
        return redirect(url_for('auth.login'))

    except Exception as e:
        flash(f"設定檔寫入失敗: {str(e)}", "danger")
        return redirect(url_for('setup.index'))