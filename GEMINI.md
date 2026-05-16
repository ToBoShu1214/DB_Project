# 🏥 智慧長照管理系統 (Smart Care Management System) - 開發者文件

本文件旨在協助開發人員或 AI 助手快速理解專案結構、核心功能及資料庫設計規範。

---

## 🛠️ 技術棧 (Tech Stack)

- **後端 (Backend):** Python 3.9+, FastAPI, Uvicorn, PyMySQL
- **資料庫 (Database):** MySQL 8.0 / MariaDB (具備正式外鍵約束的關聯式架構)
- **前端 (Frontend):** HTML5, Vanilla JavaScript, Bootstrap 5, Chart.js
- **報表工具:** Pandas, Openpyxl (支援 Excel 匯入與匯出)
- **模擬器:** Python 腳本模擬 IoT 數據流

---

## 📂 專案結構與核心檔案

- `main.py`: **後端核心**。包含資料庫自動初始化、所有 RESTful API 路由及業務邏輯。
- `iot_simulator.py`: **IoT 模擬器**。模擬住民的生理數據與即時定位資訊。
- `frontend/`: **前端靜態資源**。
  - `index.html`: 系統進入點。
  - `staff_login.html` / `family_login.html`: 登入介面。
  - `dashboard.html`: **醫護/管理員主控台**。包含住民名單、地圖監控、員工管理等。
  - `detail.html`: **住民詳細資料頁**。提供醫護人員進行深度數據監控與紀錄錄入。
  - `family_dashboard.html`: **家屬安心門戶**。UI 對齊 `detail.html` 但僅具備唯讀權限。
- `docker-compose.yml` & `Dockerfile`: 容器化配置。

---

## 📊 資料庫架構 (Database Schema)

專案已從「字串儲存」重構為「關聯式架構」，並具備正式的外鍵約束 (Foreign Key)。

### 1. 核心業務表
- `ResidentIdentity`: 住民主表。關聯 `RoomID`, `StatusID`, `CareLevelID`。
- `HealthRecord`: 生理量測紀錄（血壓、心跳、血糖、血氧）。
- `MedicalOrder`: 醫師開立之醫囑。
- `MedicationRecord`: 給藥執行紀錄，與 `MedicalOrder` 關聯。
- `ResidentSighting`: 即時位置追蹤紀錄。
- `NursingNote`: 專業護理進接紀錄。
- `DailyCareRecord`: 日常照護（沐浴、換尿褲）紀錄。

### 2. 系統設定表 (System Options)
- `SystemRoom`: 房號管理。具備 `IsWard` 標記用以區分「病房」與「公共區域」。
- `SystemStatus`: 住民狀態管理（入住中、住院、請假、退宿）。
- `SystemCareLevel`: 照護等級管理（輕度、中度、重度）。
- `ChronicDisease`: 慢性病字典與預設警報閾值。

---

## 🚀 核心功能說明

### 1. 醫護管理端 (Staff/Admin)
- **全方位監控**：即時查看全院住民的分佈位置與生理異常警報。
- **臨床作業**：錄入護理紀錄、執行醫囑給藥、登記日常照護。
- **報表匯出**：一鍵產生全院給藥執行 Excel 報表。
- **權限控制**：管理員可審核員工帳號、管理家屬關聯。

### 2. 家屬安心門戶 (Family)
- **資訊透明**：查看與醫護端同等級的圖表化生理趨勢與照護紀錄。
- **唯讀保護**：無法修改任何醫療數據，僅限查看關聯之長輩資料。
- **定位追蹤**：隨時掌握長輩在院內的即時位置，增加安心感。

---

## 💡 開發指南與注意事項

### 如何新增房號或狀態？
直接在資料庫的 `SystemRoom` 或 `SystemStatus` 表中新增資料即可，前端選單會自動同步更新，**無需修改程式碼**。

### 房號過濾邏輯
在新增/編輯住民基本資料時，系統會自動根據 `SystemRoom.IsWard = 1` 進行過濾，僅顯示真正的居住病房。

### 資料庫初始化與升級
`main.py` 中的 `init_db()` 函數具備自動偵測與升級功能。新增欄位或表結構時，應在此函數中編寫遷移邏輯。

### 安全規範
- 前端 `localStorage` 儲存用戶身份，API 執行時應注意角色權限。
- 家屬端 API 需嚴格校驗其 `ResidentID` 權限。

---
*Last Updated: 2026-05-15*
