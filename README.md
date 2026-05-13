# 🏥 智慧長照管理系統 (Smart Care Management System) - 開發者文檔

本專案是一個全方位的長照機構管理平台，具備**護理站行政管理**、**專業醫療數據監控**、以及**家屬安心入口**三大核心功能。

---

## 🛠️ 技術棧 (Tech Stack)

- **後端 (Backend):** Python 3.9+, FastAPI, Uvicorn
- **資料庫 (Database):** MySQL 8.0 (建議透過 Docker 部署)
- **前端 (Frontend):** HTML5, Vanilla JavaScript, Bootstrap 5, Chart.js
- **數據處理:** Pandas, Openpyxl (用於 Excel 批次匯入功能)

---

## 📂 專案資料夾結構

請確保你的資料夾與檔案路徑如下：

    project-root/
     ├── main.py                # FastAPI 後端主程式 (包含所有 API 路由)
     ├── docker-compose.yml     # Docker 資料庫設定檔 (見下方教學)
     └── frontend/              # 靜態網頁資料夾 (請勿更名)
          ├── index.html              # 系統入口 (身份選擇頁面)
          ├── staff_login.html        # 醫護人員登入/註冊頁面
          ├── family_login.html       # 家屬專屬登入/註冊頁面
          ├── dashboard.html          # 護理站/管理員主控台 (權限分流)
          ├── detail.html             # 住民詳細生理紀錄與醫囑清單 (專業版)
          └── family_dashboard.html   # 家屬端手機優化儀表板

---

## 🚀 環境建置與啟動步驟

### 1. 建立資料庫 (使用 Docker)

在專案根目錄建立 `docker-compose.yml` 並寫入以下內容，接著執行 `docker-compose up -d`：

    version: '3.8'
    services:
      db-db:
        image: mysql:8.0
        container_name: smart-care-db
        restart: always
        environment:
          MYSQL_ROOT_PASSWORD: rootPassword
          MYSQL_DATABASE: my-db
          MYSQL_USER: mymy
          MYSQL_PASSWORD: myPassword
        ports:
          - "3306:3306"
        command: --default-authentication-plugin=mysql_native_password

### 2. 資料庫初始化 (SQL Table)

請務必在資料庫中建立以下資料表，並注意關鍵欄位：
- **StaffAccount**: 加入 `IsApproved` (TINYINT, 預設 0), `Role` (VARCHAR)。
- **FamilyMember**: 加入 `Password` (預設 123456)。
- **HealthRecord**: 加入 `RecordTime` (DATETIME)。
- **MedicationRecord**: 加入 `IsTaken` (TINYINT, 預設 0)。

### 3. 安裝 Python 依賴套件

    pip install fastapi uvicorn pymysql pandas openpyxl python-multipart

### 4. 修改資料庫連線位址

由於 `main.py` 預設連線 `host='db-db'` (Docker 內網使用)，若是在**本地端**開發，請將 `main.py` 中的 `get_db_connection` 暫時修改為：
`host='127.0.0.1'`

### 5. 啟動伺服器

    uvicorn main:app --reload

啟動後請訪問：`http://localhost:8000`

---

## 🔑 系統測試與管理邏輯

### 🩺 醫護人員權限與審核機制
1. **管理員 (Admin)**：註冊時帳號名稱請設定為 `admin`，職稱選 `管理員`。後端會自動核准此帳號。
2. **普通員工**：註冊後狀態為「審核中」，無法登入。需由 `admin` 帳號進入主控台的「🩺 員工帳號管理」面板點擊核准。
3. **管理員權限**：僅管理員看得到「員工管理」與「全域家屬清單」標籤。

### 👨‍👩‍👧 家屬端入口
- **獨立分流**：家屬擁有獨立的 `family_login.html` 頁面，不可與醫護端混用。
- **家屬註冊**：家屬註冊時需填寫正確的**住民 ID** (如 #101)，註冊成功後即可查看該位長輩的所有數據。

### 📈 生理數據錄入
- 採用**清單式表格設計**，支援「新增一列」即時輸入。
- 支援**自訂日期時間**，方便補登過去的量測紀錄。
- 儲存後歷史數據將自動鎖定（唯讀），並即時更新上方的趨勢圖表。

---

## 📝 開發注意事項
- 修改 `main.py` 後伺服器會自動重載。
- 若前端 JS 修改後沒反應，請嘗試 `Ctrl + F5` 強制清除瀏覽器快取。
- 本系統涉及醫療隱私數據，請確保測試資料不包含真實個人資訊。
