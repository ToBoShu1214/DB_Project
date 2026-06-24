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

本專案採用 Docker 全環境容器化，將後端 API、資料庫與資料庫管理工具完美整合，無需在本地安裝 Python 或手動設定環境。

### 1. 一鍵啟動所有服務

請確保你的電腦已安裝 Docker 與 Docker Desktop，並確認其處於 Running 狀態。接著在專案根目錄下開啟終端機，執行以下指令：

```bash
docker-compose up -d --build
```

這會自動建立並啟動以下三個服務：
- **後端 API (Python FastAPI)**: 可於 `http://localhost:8000` 存取
- **MariaDB 資料庫**: 運行於 port `3306` (帳密為 `mymy` / `myPassword`)
- **phpMyAdmin (資料庫網頁管理)**: 可於 `http://localhost:8082` 存取

### 2. 資料庫自動初始化

本專案已設定自動初始化腳本：
- `init.sql`：建立所有必要的資料表，並內建一組預設管理員帳號（**帳號**: `admin` / **密碼**: `admin`）。
- `seed.sql`：補上示範用的住民、家屬、生理數據等測試資料，避免登入後畫面空白。

這兩個腳本會在 `docker-compose up -d --build` **第一次建立資料庫資料卷 (volume) 時**依檔名順序自動執行（`init.sql` 先、`seed.sql` 後），不需要手動匯入。

你可以直接用 `admin` / `admin` 登入系統，或前往 `http://localhost:8082` (phpMyAdmin) 查看資料庫狀態。

> ⚠️ 這兩個腳本**只有在資料卷第一次建立時才會自動跑**。如果你已經 `docker-compose up` 過、本機已經有舊的資料卷，修改 `init.sql` / `seed.sql` 後不會自動套用，必須先清空重建：
> ```bash
> docker-compose down -v   # 清除容器與資料卷 (會清空資料庫內容)
> docker-compose up -d --build
> ```

### 3. 修改資料庫連線資訊

資料庫的連線設定（host / 資料庫名稱 / 帳號 / 密碼）**統一寫在 [`db_config.py`](db_config.py)**，`main.py` 會從這個檔案讀取，不需要改動主程式：

```python
DB_HOST = 'db-proj-db'   # 主機名稱，本機測試對應 docker-compose.yml 的服務名稱
DB_NAME = 'csieDBTeam23' # 資料庫名稱
DB_USER = 'mymy'         # 帳號
DB_PASS = 'myPassword'   # 密碼
```

- **本機用 Docker 測試**：這四個值要跟 [`docker-compose.yml`](docker-compose.yml) 裡 MariaDB 服務 (`db-proj-db`) 的 `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD` 一致。
- **上傳給老師正式跑分**：改成老師指派給你們這組的帳密（資料庫名稱規則為 `csieDBTeamXX`，例如第 1 組是 `csieDBTeam01`）。
- 改完 `DB_NAME` 後，如果是本機環境，記得依上面的方式 `docker-compose down -v` 後再 `up -d --build`，新的資料庫名稱才會生效。

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
