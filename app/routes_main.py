from flask import Blueprint, redirect, url_for, current_app

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # 判斷邏輯：
    # 1. 檢查關鍵設定是否存在 (AD_SERVER)
    ad_server = current_app.config.get('AD_SERVER')
    
    # 2. 如果沒有設定 -> 導向初始化精靈
        
    # 3. 如果有設定 -> 導向 Dashboard (會觸發 Login 驗證)
    return redirect(url_for('auth.login'))