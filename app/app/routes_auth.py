# app/routes_auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session # <--- 新增 session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from app.ad_ops import verify_ad_login

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        success, msg = verify_ad_login(username, password)
        
        if success:
            user = User(id=username)
            login_user(user)
            
            # 【關鍵修改】將帳密存入 Session 以便後續操作使用
            # 注意：在生產環境中，建議搭配 Server-Side Session 以確保安全性
            session['ad_user_account'] = username
            session['ad_user_password'] = password
            
            return redirect(url_for('dashboard.index'))
        else:
            flash(msg, 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # 登出時務必清除 Session 中的敏感資料
    session.pop('ad_user_account', None)
    session.pop('ad_user_password', None)
    logout_user()
    return redirect(url_for('auth.login'))