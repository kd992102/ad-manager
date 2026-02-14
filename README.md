# Flask AD Manager (Active Directory Web Portal)

一個基於 Python Flask 與 LDAP3 的輕量級 Active Directory Web 管理介面。
專為資訊管理人員設計，解決了傳統 ADUC (Active Directory Users and Computers) 無法跨平台操作的痛點，並整合了 DNS 紀錄管理功能。

## 🚀 主要功能 (Features)

* **使用者管理 (User Management)**
    * 檢視使用者狀態 (啟用/停用)
    * 新增使用者 (自動產生 UPN)
    * **重置密碼** (具備權限委派邏輯)
    * 刪除使用者
* **群組管理 (Group Management)**
    * 檢視群組成員
    * 新增/移除群組成員
* **電腦管理 (Computer Management)**
    * 支援指定 **OU (Organizational Unit)** 放置邏輯
    * 自動補全 `dNSHostName` 與 `servicePrincipalName` (解決 ADUC 顯示異常問題)
* **DNS 管理 (AD-Integrated DNS)**
    * **技術亮點**：直接透過 LDAP 操作 `dnsRecord` 屬性，無需 PowerShell 或 WinRM。
    * 支援 **A Record** 與 **CNAME Record** 新增/刪除。
    * 實作微軟 DNS 二進位封包結構 (MS-DNSP) 封裝與解析。
* **安全性 (Security)**
    * Flask-Login 登入驗證
    * CSRF 防護 (Flask-WTF)
    * 敏感資料隔離 (.env)

## 🛠️ 使用工具 (Tools)

* **Backend**: Python 3.9+, Flask, LDAP3
* **Frontend**: Bootstrap 5, Jinja2
* **Infrastructure**: Docker, Docker Compose

## ⚙️ 安裝與執行 (Installation)

### 1. Clone 專案
```bash
git clone [https://github.com/kd992102/ad-manager.git](https://github.com/kd992102/ad-manager.git)
cd ad-manager