# AD-Manager

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ed.svg)](https://www.docker.com/)

**AD-Manager** 是一款專為 IT 管理員設計的輕量級網域管理入口網站。無需安裝 RSAT 或編寫複雜的 PowerShell 腳本，透過瀏覽器即可輕鬆執行日常 Active Directory 管理任務。

**AD-Manager** is a lightweight web portal for Active Directory management. It enables IT administrators to perform daily AD tasks through a browser without RSAT or complex PowerShell scripts.



---

## ✨ 核心功能 | Key Features

* **密碼管理 (Password Management)**: 支援管理員權限委派，快速重置使用者密碼。
* **物件維護 (Object Management)**: 輕鬆管理使用者、群組及電腦物件，支援指定 **OU (組織單位)** 部署，符合企業權限管理規範。
* **DNS 引擎 (DNS Engine)**: 內建 **MS-DNSP** 協定實作，直接透過 LDAP 新增或刪除 A 與 CNAME 紀錄，無需依賴 WinRM 或 PowerShell。
* **自動化配置 (Auto-Provisioning)**: 自動補全電腦物件的 SPN 與 DNS 屬性，確保系統相容性。

---

## 🔒 資安設計 | Security

本專案遵循 **深度防禦 (Defense-in-Depth)** 原則開發，確保管理過程的安全與合規：
* **權限委派**: 支援以「當前登入者」身分執行連線，確保操作符合 AD 權限控管邏輯。
* **防護機制**: 全站啟用 CSRF 防護與 LDAP 注入過濾 (Injection Prevention)。
* **憑證安全**: 採用 Server-Side Session 儲存，敏感資料不留存於客戶端 Cookie。

---

## 🚀 快速上手 | Getting Started

### 1. 啟動服務
確保您的環境已安裝 Docker 與 Docker Compose，執行以下指令：

```bash
git clone [https://github.com/your-username/ad-manager.git](https://github.com/your-username/ad-manager.git)
cd ad-manager
docker compose up -d --build