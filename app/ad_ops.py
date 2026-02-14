# app/ad_ops.py
import struct
import socket
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, NONE
from flask import current_app
import ssl
import sys
from ldap3.utils.conv import escape_filter_chars
from flask import current_app, session # <--- 引入 session

def log(msg):
    # 寫入 stderr 而不是 stdout，確保 Docker logs 看得到
    sys.stderr.write(f"[DEBUG_DNS] {msg}\n")
    sys.stderr.flush()

def get_ad_connection():
    """
    建立 AD 連線
    策略：優先使用 Session 中的「當前登入者」身分，失敗則回退到 .env 設定(可選)
    """
    # 1. 預設先抓 .env 的 (作為 fallback)
    server_addr = current_app.config.get('AD_SERVER')
    bind_user = current_app.config.get('AD_USER')
    bind_pass = current_app.config.get('AD_PASS')
    
    # 2. 【關鍵修改】檢查 Session 是否有登入者憑證
    if 'ad_user_account' in session and 'ad_user_password' in session:
        current_user = session['ad_user_account']
        current_pass = session['ad_user_password']
        
        # 處理 UPN 格式 (確保 user@domain)
        domain = current_app.config.get('AD_DOMAIN')
        if '@' not in current_user and domain:
            bind_user = f"{current_user}@{domain}"
        else:
            bind_user = current_user
            
        bind_pass = current_pass
        # log(f"使用當前登入者身分連線: {bind_user}") # Debug 用
    
    # SSL Context (保持不變)
    tls_ctx = ssl.create_default_context()
    tls_ctx.check_hostname = False
    tls_ctx.verify_mode = ssl.CERT_NONE

    server = Server(server_addr, use_ssl=True, tls=None, get_info=NONE)
    
    # 使用決定好的 bind_user/bind_pass 進行連線
    conn = Connection(server, user=bind_user, password=bind_pass, authentication='SIMPLE', auto_bind=True)
    return conn

def _get_domain_suffix(dn):
    config_domain = current_app.config.get('AD_DOMAIN')
    if config_domain:
        return config_domain
    parts = dn.split(',')
    dc_parts = [p.split('=')[1] for p in parts if p.lower().strip().startswith('dc=')]
    if not dc_parts:
        return "local" 
    return '.'.join(dc_parts)

# --- 核心搜尋功能 ---

def find_dn_by_name(conn, name, type='user'):
    base_dn = current_app.config.get('AD_BASEDN')
    if type == 'user':
        search_filter = f'(&(objectClass=user)(sAMAccountName={name})(!(objectClass=computer)))'
    elif type == 'group':
        search_filter = f'(&(objectClass=group)(cn={name}))'
    else:
        return None
    conn.search(base_dn, search_filter, attributes=['distinguishedName'])
    if conn.entries:
        return conn.entries[0].distinguishedName.value
    return None

# --- DNS 管理功能 ---

def get_dns_zones():
    """取得 DNS 區域 (過濾版)"""
    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    target_domain = _get_domain_suffix(base_dn)
    
    if 'dc=' in base_dn.lower():
        domain_root = base_dn.lower()[base_dn.lower().find('dc='):]
    else:
        return []

    search_paths = [
        f"DC=DomainDnsZones,{domain_root}", 
        f"CN=MicrosoftDNS,DC=DomainDnsZones,{domain_root}",
        f"CN=MicrosoftDNS,CN=System,{domain_root}"
    ]
    
    found_zones = []
    found_names = set()

    for path in search_paths:
        try:
            conn.search(path, '(objectClass=dnsZone)', attributes=['dc', 'distinguishedName'])
            for entry in conn.entries:
                zone_name = str(entry.dc)
                if zone_name.lower() == target_domain.lower() and zone_name not in found_names:
                    found_zones.append(entry)
                    found_names.add(zone_name)
        except Exception:
            continue
    return found_zones

def get_dns_records(zone_dn):
    """取得指定區域內的 DNS 紀錄 (過濾掉系統紀錄與底線開頭的 SRV 紀錄)"""
    conn = get_ad_connection()
    
    # 搜尋條件：排除 tombstone (已刪除) 的紀錄
    search_filter = '(&(objectClass=dnsNode)(!(dNSTombstoned=TRUE)))'
    
    conn.search(zone_dn, search_filter, attributes=['name', 'dnsRecord', 'distinguishedName'])
    
    records = []
    # 定義要隱藏的系統保留名稱 (小寫比對)
    hidden_names = ['@', 'domaindnszones', 'forestdnszones']

    for entry in conn.entries:
        # 取得名稱並去除空白
        name = str(entry.name).strip()
        name_lower = name.lower()

        # ---【過濾邏輯開始】---
        
        # 1. 過濾系統保留字 (@, DomainDnsZones...)
        if name_lower in hidden_names:
            continue
            
        # 2. 過濾 AD 系統紀錄 (所有以 _ 開頭的，如 _msdcs, _ldap, _kerberos)
        # 這些是 SRV 紀錄，管理者通常不需要動它們
        if name.startswith('_'):
            continue
            
        # ---【過濾邏輯結束】---

        rec_type = "Unknown"
        if entry.dnsRecord:
            try:
                raw_data = entry.dnsRecord.values[0] if isinstance(entry.dnsRecord.values, list) else entry.dnsRecord.value
                
                # 確保長度足夠解析 Type
                if len(raw_data) > 2:
                    type_id = raw_data[2]
                    if type_id == 1: 
                        rec_type = "A (Host)"
                    elif type_id == 5: 
                        rec_type = "CNAME (Alias)"
            except:
                pass
        
        # 只顯示我們認得的紀錄 (A 和 CNAME)，如果要顯示 Unknown 但非系統紀錄，就把這行 if 拿掉
        # 建議保留這行，這樣介面最乾淨，只會看到您手動建的資料
        if rec_type == "Unknown":
            continue

        records.append({
            'name': name,
            'type': rec_type,
            'dn': str(entry.distinguishedName)
        })
        
    return sorted(records, key=lambda x: x['name'])

# --- DNS 封包與寫入 ---

def _encode_dns_name(name):
    """CNAME 編碼"""
    # 【修正 2】: 加入 .strip() 清除前後空白，避免 Bad Parameter
    parts = name.strip().strip('.').split('.')
    encoded = b''
    for part in parts:
        if part: # 避免空字串
            encoded += struct.pack('B', len(part)) + part.encode('ascii')
    encoded += b'\x00'
    return encoded

def _create_dns_record_bytes(record_type, data_content, ttl=3600):
    """
    建立 DNS 二進位封包 (CNAME 修正版)
    修正: CNAME 必須包含 2 bytes 前綴 [總長度][標籤數量]
    """
    try:
        data_bytes = b''
        
        if record_type == 1: # A Record
            data_bytes = socket.inet_aton(data_content)
            
        elif record_type == 5: # CNAME Record
            # 1. 取得標準 DNS Wire Format (例如: 08 armytest ...)
            raw_cname = _encode_dns_name(data_content)
            
            # 2. 計算 AD 要求的 Metadata
            # (A) 總長度
            cname_total_len = len(raw_cname)
            
            # (B) 標籤數量 (Label Count)
            # 例如 "armytest.army.mil.tw" -> 4 個標籤
            # 我們重新解析字串來計算比較穩
            parts = [p for p in data_content.strip().strip('.').split('.') if p]
            label_count = len(parts)
            
            # 3. 組合前綴: [Length(1B)] [Count(1B)]
            # 注意：AD 裡的 CNAME data 開頭必須是這兩個 byte
            prefix = struct.pack('BB', cname_total_len, label_count)
            
            data_bytes = prefix + raw_cname

        else:
            raise ValueError("不支援的紀錄類型")

        data_len = len(data_bytes)
        
        # --- 建構 Header (24 bytes) ---
        # Part 1: Len, Type, Ver, Rank, Flags, Serial
        part1 = struct.pack('<HHBBHI', 
                           data_len, record_type, 5, 0xF0, 0, 0)
        
        # Part 2: TTL (Big Endian)
        part2 = struct.pack('>I', ttl)
        
        # Part 3: Reserved, Timestamp
        part3 = struct.pack('<II', 0, 0)
        
        return part1 + part2 + part3 + data_bytes

    except Exception as e:
        raise ValueError(f"DNS 封包建立失敗: {e}")

def create_dns_record(zone_dn, hostname, record_type, value):

    safe_name = escape_filter_chars(hostname)
    
    # 2. 強制檢查輸入格式 (例如只允許英數與橫線)
    if not safe_name.replace('-', '').isalnum():
        return False, "名稱包含非法字元"

    conn = get_ad_connection()
    hostname = hostname.strip()
    # 確保 CNAME 目標值也去除空白
    value = value.strip() 
    
    new_record_dn = f"DC={hostname},{zone_dn}"
    
    try:
        type_code = 1 if record_type == 'A' else 5
        dns_blob = _create_dns_record_bytes(type_code, value)
        
        attrs = {
            'objectClass': ['top', 'dnsNode'],
            'dnsRecord': [dns_blob],    # 必須是清單
            'dNSTombstoned': 'FALSE'    # 必須是大寫字串
        }
        
        if conn.add(new_record_dn, attributes=attrs):
            return True, f"DNS 紀錄 {hostname} 建立成功"
        else:
            err_msg = conn.result['description']
            if "exists" in str(err_msg).lower():
                return False, f"建立失敗: 紀錄 {hostname} 已存在，請先刪除舊紀錄。"
            return False, f"建立失敗: {err_msg}"
            
    except Exception as e:
        return False, str(e)

def delete_dns_record(record_dn):
    return delete_ad_object(record_dn)

# --- 其他基本功能 (User/Group/Computer) ---
# 為了完整性，這裡保留其他功能，避免覆蓋時遺失

def get_all_users():
    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    conn.search(base_dn, '(&(objectClass=user)(!(objectClass=computer)))', attributes=['sAMAccountName', 'displayName', 'userPrincipalName', 'userAccountControl', 'distinguishedName'])
    return conn.entries

def create_ad_user(username, password, firstname, lastname):

    safe_name = escape_filter_chars(username)
    
    # 2. 強制檢查輸入格式 (例如只允許英數與橫線)
    if not safe_name.replace('-', '').isalnum():
        return False, "名稱包含非法字元"

    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    if base_dn.lower().strip().startswith('dc='):
        user_dn = f"cn={username},cn=Users,{base_dn}"
    else:
        user_dn = f"cn={username},{base_dn}"
    
    formatted_pwd = ('"%s"' % password).encode('utf-16-le')
    domain_suffix = _get_domain_suffix(base_dn)
    
    attrs = {
        'sAMAccountName': username,
        'userPrincipalName': f"{username}@{domain_suffix}",
        'givenName': firstname,
        'sn': lastname,
        'displayName': f"{firstname} {lastname}",
        'unicodePwd': formatted_pwd,
        'userAccountControl': 512, 
        'objectClass': ['top', 'person', 'organizationalPerson', 'user']
    }
    try:
        if conn.add(user_dn, attributes=attrs):
            return True, "使用者建立成功"
        else:
            return False, f"建立失敗: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def delete_ad_object(object_dn):
    conn = get_ad_connection()
    try:
        if conn.delete(object_dn):
            return True, "刪除成功"
        else:
            return False, f"刪除失敗: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def get_all_groups():
    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    conn.search(base_dn, '(objectClass=group)', attributes=['cn', 'description', 'distinguishedName'])
    return conn.entries

def get_group_members_with_details(group_name):
    conn = get_ad_connection()
    group_dn = find_dn_by_name(conn, group_name, 'group')
    if not group_dn: return []
    conn.search(group_dn, '(objectClass=group)', attributes=['member'])
    if not conn.entries: return []
    member_dns = conn.entries[0].member.values if 'member' in conn.entries[0] else []
    detailed_members = []
    for m_dn in member_dns:
        try:
            conn.search(m_dn, '(objectClass=*)', attributes=['sAMAccountName', 'displayName'])
            if conn.entries:
                entry = conn.entries[0]
                detailed_members.append({
                    'name': str(entry.sAMAccountName) if 'sAMAccountName' in entry else 'N/A',
                    'display': str(entry.displayName) if 'displayName' in entry else 'N/A',
                    'dn': m_dn
                })
        except: continue
    return detailed_members

def manage_group_member(action, group_name, username):
    conn = get_ad_connection()
    group_dn = find_dn_by_name(conn, group_name, 'group')
    user_dn = find_dn_by_name(conn, username, 'user')
    if not group_dn or not user_dn: return False, "找不到群組或使用者"
    try:
        if action == 'add':
            conn.extend.microsoft.add_members_to_groups([user_dn], [group_dn])
        elif action == 'remove':
            conn.extend.microsoft.remove_members_from_groups([user_dn], [group_dn])
        if conn.result['result'] == 0:
            return True, "更新成功"
        else:
            return False, f"更新失敗: {conn.result['description']}"
    except Exception as e:
        return False, str(e)

def get_all_computers():
    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    conn.search(base_dn, '(objectClass=computer)', attributes=['cn', 'operatingSystem', 'distinguishedName'])
    return conn.entries

def create_computer(computer_name):

    safe_name = escape_filter_chars(computer_name)
    
    # 2. 強制檢查輸入格式 (例如只允許英數與橫線)
    if not safe_name.replace('-', '').isalnum():
        return False, "名稱包含非法字元"

    conn = get_ad_connection()
    base_dn = current_app.config.get('AD_BASEDN')
    
    # 嘗試解析網域 (例如從 dc=army,dc=mil... 解析出 army.mil.tw)
    domain = current_app.config.get('AD_DOMAIN')
    if not domain:
        domain = _get_domain_suffix(base_dn)

    computer_name = computer_name.upper() # 電腦名稱強制大寫
    
    # 1. 決定存放位置
    # 如果 base_dn 是 DC 開頭 (例如 DC=army,DC=mil...)，預設放到 CN=Computers
    # 如果 base_dn 已經指定了 OU (例如 OU=aceitc,DC=army...)，就直接用 base_dn
    if base_dn.lower().strip().startswith('dc='):
        comp_dn = f"CN={computer_name},CN=Computers,{base_dn}"
    else:
        comp_dn = f"CN={computer_name},{base_dn}"
    
    # 2. 設定屬性
    # 4096 = WORKSTATION_TRUST_ACCOUNT (工作站)
    # 32 = PASSWD_NOTREQD (不需要密碼，這對預先建立帳戶很重要)
    # 合計 = 4128
    uac_flags = 4128

    attrs = {
        'objectClass': ['top', 'person', 'organizationalPerson', 'user', 'computer'],
        'sAMAccountName': f"{computer_name}$",
        'userAccountControl': uac_flags,
        # 【關鍵修復】補上 DNS 名稱
        'dNSHostName': f"{computer_name}.{domain}",
        # 【關鍵修復】補上 SPN (Service Principal Name)
        'servicePrincipalName': [
            f"HOST/{computer_name}.{domain}",
            f"HOST/{computer_name}",
            f"RestrictedKrbHost/{computer_name}.{domain}",
            f"RestrictedKrbHost/{computer_name}"
        ],
        'displayName': f"{computer_name} (Web Created)"
    }
    
    try:
        if conn.add(comp_dn, attributes=attrs):
            return True, f"電腦 {computer_name} 建立成功"
        else:
            return False, f"建立失敗: {conn.result['description']}"
    except Exception as e:
        return False, str(e)
    
def verify_ad_login(username, password):
    """
    驗證使用者帳號密碼是否正確 (用於登入頁面)
    """
    server_addr = current_app.config.get('AD_SERVER')
    base_dn = current_app.config.get('AD_BASEDN')
    domain = current_app.config.get('AD_DOMAIN') # 例如 army.mil.tw
    
    # 組合 UPN (User Principal Name)
    if '@' not in username:
        user_upn = f"{username}@{domain}"
    else:
        user_upn = username

    try:
        # 嘗試用該帳號密碼建立連線
        server = Server(server_addr, use_ssl=True, tls=None, get_info=NONE)
        conn = Connection(server, user=user_upn, password=password, authentication='SIMPLE', auto_bind=True)
        
        # 如果 auto_bind 成功，代表密碼正確
        if conn.bound:
            conn.unbind()
            return True, "登入成功"
    except Exception as e:
        return False, f"登入失敗: {str(e)}"
    
    return False, "帳號或密碼錯誤"

def reset_user_password(username, new_password):
    """
    重置使用者密碼 (管理員操作)
    """
    conn = get_ad_connection() # 使用 .env 的管理員帳號連線
    user_dn = find_dn_by_name(conn, username, 'user')
    
    if not user_dn:
        return False, "找不到使用者"
        
    try:
        # AD 要求密碼必須用 quote 包起來並轉成 utf-16-le
        formatted_pwd = ('"%s"' % new_password).encode('utf-16-le')
        
        # 使用 LDAP 的 modify 操作來替換 unicodePwd
        conn.extend.microsoft.modify_password(user_dn, new_password)
        
        return True, "密碼重置成功"
    except Exception as e:
        return False, f"重置失敗: {str(e)}"