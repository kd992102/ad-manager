# app/routes_auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session # <--- 新增 session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from ldap3.utils.conv import escape_filter_chars
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
        
        # 這裡的 success 現在包含了「密碼正確」且「具備管理權限」
        success, msg = verify_ad_login(username, password)
        
        if success:
            user = User(id=username)
            login_user(user)
            session['ad_user_account'] = username
            session['ad_user_password'] = password
            return redirect(url_for('dashboard.index'))
        else:
            # 如果是權限不足，msg 會顯示 "權限不足：您不具備 Domain Admins 權限"
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