from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
# 引入 ad_ops 所有功能 (包含我們剛修好的 DNS 功能)
from app.ad_ops import *
from flask_login import login_required  # <--- 必須有這一行

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required # <--- 2. 這裡一定要加！這就是「鎖頭
def index():
    # 1. 取得選擇的參數 (群組 or DNS區域)
    selected_group_name = request.args.get('selected_group')
    selected_zone_dn = request.args.get('selected_zone') # <--- [新增] 接收 DNS 區域參數
    
    # 初始化變數
    group_members = []
    dns_records = []  # <--- [新增]
    users, groups, computers, zones = [], [], [], [] # <--- [新增] zones 初始化

    try:
        # 讀取基本資料
        users = get_all_users()
        groups = get_all_groups()
        computers = get_all_computers()
        zones = get_dns_zones() # <--- [關鍵修正] 呼叫後端抓取 DNS 區域！
        
        # 2. 如果有選取群組，就去抓成員
        if selected_group_name:
            group_members = get_group_members_with_details(selected_group_name)
            
        # 3. [新增] 如果有選取 DNS 區域，就去抓紀錄
        if selected_zone_dn:
            dns_records = get_dns_records(selected_zone_dn)
            
    except Exception as e:
        flash(f"讀取 AD 資料失敗: {str(e)}", "danger")
        # 發生錯誤時保持空陣列，避免頁面崩潰
        users, groups, computers, zones = [], [], [], []
        
    # 4. 把資料傳給前端
    return render_template('dashboard.html', 
                           users=users, 
                           groups=groups, 
                           computers=computers,
                           zones=zones,           # <--- [關鍵修正] 把區域列表傳給 HTML
                           selected_group=selected_group_name,
                           group_members=group_members,
                           selected_zone=selected_zone_dn, # <--- [新增] 傳回選取的區域 DN
                           dns_records=dns_records)        # <--- [新增] 傳回紀錄列表

# --- 使用者操作 ---
@bp.route('/user/add', methods=['POST'])
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    
    success, msg = create_ad_user(username, password, firstname, lastname)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index'))

@bp.route('/object/delete', methods=['POST'])
def delete_object():
    dn = request.form.get('dn')
    success, msg = delete_ad_object(dn)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index'))

# --- 群組操作 ---
@bp.route('/group/manage', methods=['POST'])
def manage_group():
    action = request.form.get('action')
    group_name = request.form.get('group_name')
    username = request.form.get('username')
    
    # 這裡 ad_ops 裡面的函式名稱要對應你的版本
    # 如果是用 simple 名稱版，請確保 ad_ops 裡有 manage_group_member
    if action == 'add':
        success, msg = manage_group_member('add', group_name, username)
    elif action == 'remove':
        success, msg = manage_group_member('remove', group_name, username)
    else:
        success, msg = False, "無效的操作"
    
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index', selected_group=group_name) + '#groups')

# --- 電腦操作 ---
@bp.route('/computer/add', methods=['POST'])
def add_computer():
    name = request.form.get('computer_name')
    success, msg = create_computer(name)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index') + '#computers')

# --- DNS 操作 ---
@bp.route('/dns/add', methods=['POST'])
def add_dns_record():
    zone_dn = request.form.get('zone_dn')
    hostname = request.form.get('hostname')
    record_type = request.form.get('record_type') # A or CNAME
    
    if record_type == 'A':
        value = request.form.get('ip_address')
    else:
        value = request.form.get('target_fqdn')
    
    success, msg = create_dns_record(zone_dn, hostname, record_type, value)
    flash(msg, "success" if success else "danger")
    # 導向回該 DNS 區域並切換到 #dns 分頁
    return redirect(url_for('dashboard.index', selected_zone=zone_dn) + '#dns')

# [新增] 刪除 DNS 紀錄路由 (原本漏掉了)
@bp.route('/dns/delete', methods=['POST'])
def delete_dns():
    record_dn = request.form.get('record_dn')
    zone_dn = request.form.get('zone_dn') # 為了導向回去
    
    success, msg = delete_dns_record(record_dn)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index', selected_zone=zone_dn) + '#dns')

@bp.route('/user/reset_password', methods=['POST'])
@login_required # 確保只有登入者能操作
def reset_password():
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    
    success, msg = reset_user_password(username, new_password)
    flash(msg, "success" if success else "danger")
    return redirect(url_for('dashboard.index'))