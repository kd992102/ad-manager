# AD-Manager

**AD-Manager** 是一款專為 IT 管理員設計的輕量級網域管理入口網站。無需安裝 RSAT 或編寫複雜的 PowerShell 腳本，透過瀏覽器即可輕鬆執行日常 Active Directory 管理任務。

**AD-Manager** is a lightweight web portal for Active Directory management. It enables IT administrators to perform daily AD tasks through a browser without RSAT or complex PowerShell scripts.

---

## ✨ 核心功能 | Key Features

* **使用者管理 (User Management)**: 支援管理員權限委派，快速重置使用者密碼。
* **電腦物件管理 (Object Management)**: 輕鬆管理使用者、群組及電腦物件，支援指定 **OU (組織單位)** 部署，符合企業權限管理規範。
* **DNS管理 (DNS Management)**: 內建 **MS-DNSP** 協定實作，直接透過 LDAP 新增或刪除 A 與 CNAME 紀錄，無需依賴 WinRM 或 PowerShell。

---

## 🚀 快速上手 | Getting Started

### 1. 啟動服務
確保您的環境已安裝 Docker 與 Docker Compose，執行以下指令：

```bash
git clone [https://github.com/kd992102/ad-manager.git](https://github.com/kd992102/ad-manager.git)
cd ad-manager
docker compose up -d --build