from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import pymysql
from db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS
import pandas as pd
import io
import os
from urllib.parse import urlparse

app = FastAPI(title="智慧長照管理系統 API", version="6.1.0")

def get_db_connection():
    # 連線設定統一從 db_config.py 讀取，老師請修改該檔案
    try:
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3  # 3 秒沒連上就放棄，不要讓網頁轉圈
        )
    except Exception as e:
        print(f"❌ 資料庫連線失敗: {e}")
        raise e

# --- 資料模型 ---
class LoginRequest(BaseModel): Username: str; Password: str
class RegisterRequest(BaseModel): Username: str; Password: str; RealName: str; Role: str
class StaffFullData(BaseModel): Username: str; Password: str; RealName: str; Role: str; IsApproved: int

class FamilyLoginRequest(BaseModel): Phone: str; Password: str
class FamilyRegisterRequest(BaseModel): ResidentID: int; FullName: str; Relationship: str; Phone: str; Password: str

class ResidentData(BaseModel): 
    FullName: str; Sex: str; DateOfBirth: str; CareLevel: str; RoomNumber: str; Status: str
    BpThreshold: Optional[int] = 140
    Height: Optional[float] = None
    Weight: Optional[float] = None
    CDR: Optional[str] = None      # 失智等級
    CMS: Optional[str] = None      # 失能等級
    Allergies: Optional[str] = None # 過敏原
    IdentityNumber: Optional[str] = None # 身分證字號
    HealthCardNumber: Optional[str] = None # 健保卡號
    # 🚀 新增系統關聯 ID
    RoomID: Optional[int] = None
    StatusID: Optional[int] = None
    CareLevelID: Optional[int] = None

class VaccinationRecordData(BaseModel):
    ResidentID: int
    VaccineType: str  # 流感, 肺炎鏈球菌, COVID-19 等
    Brand: str        # 廠牌 (莫德納, BNT...)
    DoseDate: str     # 施打日期
    NextDoseDate: Optional[str] = None # 預計補打日

class FamilyMemberData(BaseModel): ResidentID: int; FullName: str; Relationship: str; Phone: str; IsEmergencyContact: int = 0

# 🚀 升級：加入 RecordTime 允許前端自訂時間，並新增血糖、血氧
class HealthRecordData(BaseModel): 
    ResidentID: int
    SystolicBP: int
    DiastolicBP: int
    HeartRate: int
    BloodSugar: Optional[float] = None
    BloodOxygen: Optional[int] = None
    RecordTime: Optional[str] = None 
    Notes: Optional[str] = None

class SightingData(BaseModel): ResidentID: int; Zone: str; X_Coordinate: float; Y_Coordinate: float

class DailyCareData(BaseModel):
    ResidentID: int
    StaffID: int
    RecordTime: str  # YYYY-MM-DD HH:MM:SS
    BathStatus: int  # 0 or 1
    DiaperCount: int
    WoundNote: Optional[str] = None

# 給藥模型 (用於舊的 API 相容)
class MedicationData(BaseModel): 
    ResidentID: int; MedName: str; Dosage: str; Schedule: str; Staff_ID: int

# 醫囑模型 (由醫師開立)
class MedicalOrderData(BaseModel):
    ResidentID: int
    DoctorID: int
    OrderContent: str  # 醫囑內容
    MedName: str
    Dosage: str
    Schedule: str      # 例如: "三餐飯後"

# 給藥執行模型 (由護理師/職員執行)
class MedicationUpdate(BaseModel): IsTaken: int; Staff_ID: int

class ChronicDiseaseData(BaseModel):
    DiseaseName: str
    DefaultBpThreshold: int

class StaffUpdateRequest(BaseModel): IsApproved: int; Role: str

# ==========================================
# 1. 系統權限 & 帳號管理
# ==========================================
@app.get("/api/status")
def status(): return {"status": "系統運作中"}

@app.post("/api/login")
def login(auth: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT StaffID, Username, RealName, Role, IsApproved FROM StaffAccount WHERE Username = %s AND Password = %s", (auth.Username, auth.Password))
    user = cursor.fetchone(); conn.close()
    if not user: raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    if user['IsApproved'] == 0: raise HTTPException(status_code=403, detail="帳號審核中，請聯繫管理員。")
    return {"status": "success", "user_info": user}

@app.post("/api/register")
def register(user: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM StaffAccount WHERE Username = %s", (user.Username,))
    if cursor.fetchone(): return {"status": "error", "message": "此帳號已被註冊"}
    is_approved = 1 if user.Username == 'admin' else 0
    cursor.execute("INSERT INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES (%s,%s,%s,%s,%s)", (user.Username, user.Password, user.RealName, user.Role, is_approved))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/api/staff")
def get_all_staff():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT StaffID, Username, RealName, Role, IsApproved, Password FROM StaffAccount ORDER BY StaffID DESC")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/staff")
def admin_create_staff(s: StaffFullData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES (%s,%s,%s,%s,%s)", (s.Username, s.Password, s.RealName, s.Role, s.IsApproved))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.put("/api/staff/{staff_id}")
def update_staff(staff_id: int, s: StaffFullData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE StaffAccount SET Username=%s, Password=%s, RealName=%s, Role=%s, IsApproved=%s WHERE StaffID=%s", (s.Username, s.Password, s.RealName, s.Role, s.IsApproved, staff_id))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.delete("/api/staff/{staff_id}")
def delete_staff(staff_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM StaffAccount WHERE StaffID=%s", (staff_id,))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.post("/api/family/login")
def family_login(auth: FamilyLoginRequest):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT FamilyID, ResidentID, FullName FROM FamilyMember WHERE Phone = %s AND Password = %s", (auth.Phone, auth.Password))
        user = cursor.fetchone(); conn.close()
        if user: return {"status": "success", "message": f"歡迎，{user['FullName']} 家屬", "user_info": user}
        raise HTTPException(status_code=401, detail="電話號碼或密碼錯誤")
    except Exception as e: return {"status": "error", "message": str(e)}

@app.post("/api/family/register")
def family_register(f: FamilyRegisterRequest):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT * FROM ResidentIdentity WHERE ResidentID = %s", (f.ResidentID,))
        if not cursor.fetchone(): return {"status": "error", "message": "找不到該住民編號"}
        cursor.execute("INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, Password) VALUES (%s,%s,%s,%s,%s)", (f.ResidentID, f.FullName, f.Relationship, f.Phone, f.Password))
        conn.commit(); conn.close()
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

# ==========================================
# 2. 住民管理 
# ==========================================
@app.get("/api/options/rooms")
def get_rooms():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM SystemRoom")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/options/statuses")
def get_statuses():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM SystemStatus")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/options/care-levels")
def get_care_levels():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM SystemCareLevel")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/residents")
def get_residents():
    conn = get_db_connection(); cursor = conn.cursor()
    # 🚀 使用 JOIN 取得關聯表的名稱，確保前端顯示正確
    cursor.execute("""
        SELECT ri.*, sr.RoomNumber as RoomNumberDisplay, ss.StatusName as StatusDisplay, scl.LevelName as CareLevelDisplay
        FROM ResidentIdentity ri
        LEFT JOIN SystemRoom sr ON ri.RoomID = sr.RoomID
        LEFT JOIN SystemStatus ss ON ri.StatusID = ss.StatusID
        LEFT JOIN SystemCareLevel scl ON ri.CareLevelID = scl.LevelID
        ORDER BY ri.ResidentID DESC
    """)
    data = cursor.fetchall(); conn.close()
    # 為了不破壞前端，將 Display 名稱覆蓋回原欄位名
    for r in data:
        if r['RoomNumberDisplay']: r['RoomNumber'] = r['RoomNumberDisplay']
        if r['StatusDisplay']: r['Status'] = r['StatusDisplay']
        if r['CareLevelDisplay']: r['CareLevel'] = r['CareLevelDisplay']
    return {"status": "success", "data": data}

@app.get("/api/residents/{res_id}")
def get_resident_single(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT ri.*, sr.RoomNumber as RoomNumberDisplay, ss.StatusName as StatusDisplay, scl.LevelName as CareLevelDisplay
        FROM ResidentIdentity ri
        LEFT JOIN SystemRoom sr ON ri.RoomID = sr.RoomID
        LEFT JOIN SystemStatus ss ON ri.StatusID = ss.StatusID
        LEFT JOIN SystemCareLevel scl ON ri.CareLevelID = scl.LevelID
        WHERE ri.ResidentID = %s
    """, (res_id,))
    data = cursor.fetchone(); conn.close()
    if data:
        if data['RoomNumberDisplay']: data['RoomNumber'] = data['RoomNumberDisplay']
        if data['StatusDisplay']: data['Status'] = data['StatusDisplay']
        if data['CareLevelDisplay']: data['CareLevel'] = data['CareLevelDisplay']
    return {"status": "success", "data": data}

@app.post("/api/residents/upload")
async def upload_excel(file: UploadFile = File(...)):
    contents = await file.read(); df = pd.read_excel(io.BytesIO(contents))
    conn = get_db_connection(); cursor = conn.cursor()
    for _, row in df.iterrows():
        # 這裡上傳暫時還是維持字串寫入舊欄位，或是嘗試尋找 ID
        cursor.execute("""
            INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, CareLevelID, RoomID, StatusID) 
            VALUES (%s,%s,%s,%s,%s,%s, 
                (SELECT LevelID FROM SystemCareLevel WHERE LevelName = %s LIMIT 1),
                (SELECT RoomID FROM SystemRoom WHERE RoomNumber = %s LIMIT 1),
                (SELECT StatusID FROM SystemStatus WHERE StatusName = %s LIMIT 1))
        """, (str(row['姓名']), str(row['性別']), row['出生年月日'].strftime('%Y-%m-%d'), str(row['照護等級']), str(row['房號']), str(row['目前狀態']),
              str(row['照護等級']), str(row['房號']), str(row['目前狀態'])))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.post("/api/residents/single")
def create_resident(res: ResidentData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, Height, Weight, CDR, CMS, Allergies, IdentityNumber, HealthCardNumber, RoomID, StatusID, CareLevelID) 
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (res.FullName, res.Sex, res.DateOfBirth, res.CareLevel, res.RoomNumber, res.Status, res.Height, res.Weight, res.CDR, res.CMS, res.Allergies, res.IdentityNumber, res.HealthCardNumber, res.RoomID, res.StatusID, res.CareLevelID))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.put("/api/residents/{res_id}")
def update_resident(res_id: int, res: ResidentData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE ResidentIdentity 
        SET FullName=%s, Sex=%s, DateOfBirth=%s, CareLevel=%s, RoomNumber=%s, Status=%s, BpThreshold=%s, Height=%s, Weight=%s, CDR=%s, CMS=%s, Allergies=%s,
            IdentityNumber=%s, HealthCardNumber=%s, RoomID=%s, StatusID=%s, CareLevelID=%s
        WHERE ResidentID=%s
    """, (res.FullName, res.Sex, res.DateOfBirth, res.CareLevel, res.RoomNumber, res.Status, res.BpThreshold, res.Height, res.Weight, res.CDR, res.CMS, res.Allergies, 
          res.IdentityNumber, res.HealthCardNumber, res.RoomID, res.StatusID, res.CareLevelID, res_id))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.delete("/api/residents/{res_id}")
def delete_resident(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM ResidentIdentity WHERE ResidentID=%s", (res_id,))
    conn.commit(); conn.close()
    return {"status": "success"}

# ==========================================
# 3. 家屬、健康、位置 
# ==========================================
@app.get("/api/family-members")
def get_all_family():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT f.*, r.FullName as ResidentName FROM FamilyMember f LEFT JOIN ResidentIdentity r ON f.ResidentID = r.ResidentID")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/residents/{res_id}/family")
def get_family(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM FamilyMember WHERE ResidentID=%s", (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/family-members")
def add_family(f: FamilyMemberData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, IsEmergencyContact) VALUES (%s,%s,%s,%s,%s)", (f.ResidentID, f.FullName, f.Relationship, f.Phone, f.IsEmergencyContact))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.put("/api/family-members/{f_id}")
def update_family(f_id: int, f: FamilyMemberData):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("""
            UPDATE FamilyMember 
            SET ResidentID=%s, FullName=%s, Relationship=%s, Phone=%s, IsEmergencyContact=%s 
            WHERE FamilyID=%s
        """, (f.ResidentID, f.FullName, f.Relationship, f.Phone, f.IsEmergencyContact, f_id))
        conn.commit(); conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/family-members/{f_id}")
def delete_family(f_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM FamilyMember WHERE FamilyID=%s", (f_id,))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/api/reports/health-summary/{res_id}")
def health_summary(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT AVG(SystolicBP) as AvgSystolic, AVG(DiastolicBP) as AvgDiastolic, AVG(HeartRate) as AvgHeartRate, COUNT(*) as TotalRecords FROM HealthRecord WHERE ResidentID=%s", (res_id,))
    data = cursor.fetchone(); conn.close()
    return {"status": "success", "summary": data}

@app.get("/api/residents/{res_id}/health-history")
def get_health_history(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT RecordTime, SystolicBP, DiastolicBP, HeartRate, Notes FROM HealthRecord WHERE ResidentID = %s ORDER BY RecordTime ASC LIMIT 10", (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

# 🚀 升級：處理前端傳來的 RecordTime，並支援血糖、血氧
@app.post("/api/health-records")
def add_health(h: HealthRecordData):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        if h.RecordTime:
            cursor.execute("""
                INSERT INTO HealthRecord (ResidentID, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, RecordTime, Notes) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (h.ResidentID, h.SystolicBP, h.DiastolicBP, h.HeartRate, h.BloodSugar, h.BloodOxygen, h.RecordTime, h.Notes))
        else:
            cursor.execute("""
                INSERT INTO HealthRecord (ResidentID, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, Notes) 
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (h.ResidentID, h.SystolicBP, h.DiastolicBP, h.HeartRate, h.BloodSugar, h.BloodOxygen, h.Notes))
        conn.commit(); conn.close()
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.get("/api/residents/{res_id}/medications")
def get_medications(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    # 🚀 邏輯優化：顯示「所有未服用」以及「今天才服用」的藥物紀錄
    cursor.execute("""
        SELECT * FROM MedicationRecord 
        WHERE ResidentID = %s 
        AND (IsTaken = 0 OR (IsTaken = 1 AND DATE(CreateTime) = CURDATE()))
        ORDER BY IsTaken ASC, CreateTime DESC
    """, (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/medications")
def add_medication(med: MedicationData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO MedicationRecord (ResidentID, MedName, Dosage, Schedule, Staff_ID, IsTaken) VALUES (%s, %s, %s, %s, %s, 0)", (med.ResidentID, med.MedName, med.Dosage, med.Schedule, med.Staff_ID))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/api/medications/{med_id}/status")
def update_med_status(med_id: int, update: MedicationUpdate):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE MedicationRecord SET IsTaken=%s, Staff_ID=%s WHERE RecordID=%s", (update.IsTaken, update.Staff_ID, med_id))
    conn.commit(); conn.close()
    return {"status": "success"}

# --- 疫苗紀錄 API ---
@app.get("/api/residents/{res_id}/vaccinations")
def get_vaccinations(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM VaccinationRecord WHERE ResidentID = %s ORDER BY DoseDate DESC", (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/residents/{res_id}/vaccinations")
def add_vaccination(res_id: int, v: VaccinationRecordData):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO VaccinationRecord (ResidentID, VaccineType, Brand, DoseDate, NextDoseDate) 
            VALUES (%s, %s, %s, %s, %s)
        """, (res_id, v.VaccineType, v.Brand, v.DoseDate, v.NextDoseDate))
        conn.commit(); conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/vaccinations/{v_id}")
def delete_vaccination(v_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM VaccinationRecord WHERE VaccineID = %s", (v_id,))
    conn.commit(); conn.close()
    return {"status": "success"}

@app.get("/api/residents/{res_id}/location")
def get_location(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT Zone, X_Coordinate, Y_Coordinate, Timestamp FROM ResidentSighting WHERE ResidentID=%s ORDER BY Timestamp DESC LIMIT 1", (res_id,))
    data = cursor.fetchone(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/residents/locations/all")
def get_all_locations():
    conn = get_db_connection(); cursor = conn.cursor()
    # 🚀 取得每位住民最新的一筆定位紀錄
    cursor.execute("""
        SELECT rs.ResidentID, ri.FullName, rs.Zone, rs.X_Coordinate, rs.Y_Coordinate, rs.Timestamp 
        FROM ResidentSighting rs
        JOIN ResidentIdentity ri ON rs.ResidentID = ri.ResidentID
        WHERE (rs.ResidentID, rs.Timestamp) IN (
            SELECT ResidentID, MAX(Timestamp)
            FROM ResidentSighting
            GROUP BY ResidentID
        )
    """)
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/sightings")
def create_sighting(sighting: SightingData):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO ResidentSighting (ResidentID, Zone, X_Coordinate, Y_Coordinate) VALUES (%s, %s, %s, %s)", (sighting.ResidentID, sighting.Zone, sighting.X_Coordinate, sighting.Y_Coordinate))
    conn.commit(); conn.close()
    return {"status": "success"}

# ==========================================
# 4. 醫療邏輯擴充：醫囑、慢性病、動態閾值
# ==========================================

@app.on_event("startup")
def init_db():
    """自動初始化新表格 (針對期末專題擴充)"""
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        
        # 1. 擴充 ResidentIdentity 增加欄位
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN BpThreshold INT DEFAULT 140")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN Height FLOAT")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN Weight FLOAT")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN CDR VARCHAR(50)")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN CMS VARCHAR(50)")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN Allergies TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN IdentityNumber VARCHAR(20)")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN HealthCardNumber VARCHAR(20)")
        except: pass

        # 2. 擴充 HealthRecord 增加欄位
        try: cursor.execute("ALTER TABLE HealthRecord ADD COLUMN BloodSugar FLOAT")
        except: pass
        try: cursor.execute("ALTER TABLE HealthRecord ADD COLUMN BloodOxygen INT")
        except: pass

        # 3. 建立疫苗紀錄表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS VaccinationRecord (
                VaccineID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                VaccineType VARCHAR(100),
                Brand VARCHAR(100),
                DoseDate DATE,
                NextDoseDate DATE,
                CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
            )
        """)

        # 3. 建立慢性病表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ChronicDisease (
                DiseaseID INT AUTO_INCREMENT PRIMARY KEY,
                DiseaseName VARCHAR(100) NOT NULL,
                DefaultBpThreshold INT DEFAULT 140
            )
        """)
        
        # 🚀 強制清理重複資料 (只保留 ID 最小的)
        try:
            cursor.execute("""
                DELETE c1 FROM ChronicDisease c1
                INNER JOIN ChronicDisease c2 
                WHERE c1.DiseaseID > c2.DiseaseID AND c1.DiseaseName = c2.DiseaseName
            """)
            # 🚀 強制加入唯一限制
            cursor.execute("ALTER TABLE ChronicDisease ADD UNIQUE (DiseaseName)")
        except: pass
        
        # 🚀 使用 INSERT IGNORE 配合 UNIQUE 限制
        cursor.execute("INSERT IGNORE INTO ChronicDisease (DiseaseName, DefaultBpThreshold) VALUES ('高血壓', 155), ('糖尿病', 140), ('心臟病', 135)")

        # 3. 建立住民病歷關聯表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ResidentMedicalProfile (
                ProfileID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                DiseaseID INT,
                DiagnosisDate DATE,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE,
                FOREIGN KEY (DiseaseID) REFERENCES ChronicDisease(DiseaseID) ON DELETE CASCADE
            )
        """)

        # 4. 建立醫囑表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS MedicalOrder (
                OrderID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                DoctorID INT,
                OrderContent TEXT,
                MedName VARCHAR(100),
                Dosage VARCHAR(50),
                Schedule VARCHAR(100),
                CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
            )
        """)

        # 5. 🚀 修正關聯：確保 MedicationRecord 擁有 OrderID 且能連動刪除
        try: cursor.execute("ALTER TABLE MedicationRecord ADD COLUMN OrderID INT")
        except: pass
        
        try:
            cursor.execute("""
                ALTER TABLE MedicationRecord 
                ADD CONSTRAINT fk_order_link 
                FOREIGN KEY (OrderID) REFERENCES MedicalOrder(OrderID) ON DELETE CASCADE
            """)
        except: pass

        # 6. 🚀 建立護理進接紀錄表 (Nursing Progress Notes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS NursingNote (
                NoteID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                StaffID INT,
                NoteContent TEXT,
                CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
            )
        """)

        # 7. 🚀 建立位置追蹤表 (IoT Sighting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ResidentSighting (
                SightingID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                Zone VARCHAR(100),
                X_Coordinate FLOAT DEFAULT 0,
                Y_Coordinate FLOAT DEFAULT 0,
                Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
            )
        """)

        # 8. 🚀 建立日常照護紀錄表 (清潔與巡查)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DailyCareRecord (
                RecordID INT AUTO_INCREMENT PRIMARY KEY,
                ResidentID INT,
                StaffID INT,
                RecordTime DATETIME,
                BathStatus INT DEFAULT 0,
                DiaperCount INT DEFAULT 0,
                WoundNote TEXT,
                CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE,
                FOREIGN KEY (StaffID) REFERENCES StaffAccount(StaffID) ON DELETE SET NULL
            )
        """)
        # 🚀 遷移舊資料 (如果存在 RecordDate 則轉為 RecordTime)
        try:
            cursor.execute("ALTER TABLE DailyCareRecord ADD COLUMN RecordTime DATETIME")
            cursor.execute("UPDATE DailyCareRecord SET RecordTime = RecordDate WHERE RecordTime IS NULL")
            cursor.execute("ALTER TABLE DailyCareRecord DROP COLUMN RecordDate")
            cursor.execute("ALTER TABLE DailyCareRecord DROP INDEX daily_res_date")
        except: pass

        # 9. 🚀 建立系統設定表 (房號、狀態、等級)
        cursor.execute("CREATE TABLE IF NOT EXISTS SystemRoom (RoomID INT AUTO_INCREMENT PRIMARY KEY, RoomNumber VARCHAR(50) UNIQUE, IsWard TINYINT DEFAULT 1)")
        
        # 🚀 確保 IsWard 欄位存在 (針對已建立的舊表)
        try: cursor.execute("ALTER TABLE SystemRoom ADD COLUMN IsWard TINYINT DEFAULT 1")
        except: pass
        
        cursor.execute("CREATE TABLE IF NOT EXISTS SystemStatus (StatusID INT AUTO_INCREMENT PRIMARY KEY, StatusName VARCHAR(50) UNIQUE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS SystemCareLevel (LevelID INT AUTO_INCREMENT PRIMARY KEY, LevelName VARCHAR(50) UNIQUE)")

        # 寫入預設值
        # 區分病房 (IsWard=1) 與公共區域 (IsWard=0)
        wards = ['401房', '402房', '403房', '404房', '405房', '406房', '407房', '408房', '409房', '410房', '411房', '412房']
        public_areas = ['交誼廳', '護理站', '行政辦公室', '走廊']
        
        for r in wards: cursor.execute("INSERT IGNORE INTO SystemRoom (RoomNumber, IsWard) VALUES (%s, 1)", (r,))
        for r in public_areas: cursor.execute("INSERT IGNORE INTO SystemRoom (RoomNumber, IsWard) VALUES (%s, 0)", (r,))
        
        # 確保現有資料的 IsWard 欄位正確 (強制更新一次)
        cursor.execute("UPDATE SystemRoom SET IsWard = 1 WHERE RoomNumber LIKE '4%房'")
        cursor.execute("UPDATE SystemRoom SET IsWard = 0 WHERE RoomNumber IN ('交誼廳', '護理站', '行政辦公室', '走廊')")
        
        statuses = ['入住中', '住院', '請假', '退宿']
        for s in statuses: cursor.execute("INSERT IGNORE INTO SystemStatus (StatusName) VALUES (%s)", (s,))
        
        levels = ['輕度', '中度', '重度']
        for l in levels: cursor.execute("INSERT IGNORE INTO SystemCareLevel (LevelName) VALUES (%s)", (l,))

        # 10. 擴充 ResidentIdentity 增加 ID 關聯欄位
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN RoomID INT")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN StatusID INT")
        except: pass
        try: cursor.execute("ALTER TABLE ResidentIdentity ADD COLUMN CareLevelID INT")
        except: pass

        # 執行資料遷移 (將舊的字串對應到 ID)
        cursor.execute("UPDATE ResidentIdentity ri JOIN SystemRoom sr ON ri.RoomNumber = sr.RoomNumber SET ri.RoomID = sr.RoomID WHERE ri.RoomID IS NULL")
        cursor.execute("UPDATE ResidentIdentity ri JOIN SystemStatus ss ON ri.Status = ss.StatusName SET ri.StatusID = ss.StatusID WHERE ri.StatusID IS NULL")
        cursor.execute("UPDATE ResidentIdentity ri JOIN SystemCareLevel scl ON ri.CareLevel = scl.LevelName SET ri.CareLevelID = scl.LevelID WHERE ri.CareLevelID IS NULL")

        # 🚀 11. 加入正式的 Foreign Key 約束 (確保資料完整性)
        try:
            cursor.execute("ALTER TABLE ResidentIdentity ADD CONSTRAINT fk_room FOREIGN KEY (RoomID) REFERENCES SystemRoom(RoomID)")
        except: pass
        try:
            cursor.execute("ALTER TABLE ResidentIdentity ADD CONSTRAINT fk_status FOREIGN KEY (StatusID) REFERENCES SystemStatus(StatusID)")
        except: pass
        try:
            cursor.execute("ALTER TABLE ResidentIdentity ADD CONSTRAINT fk_level FOREIGN KEY (CareLevelID) REFERENCES SystemCareLevel(LevelID)")
        except: pass

        conn.commit(); conn.close()

        print("✅ 資料庫自動升級與初始化成功")
    except Exception as e:
        print(f"⚠️ 資料庫初始化跳過或失敗: {e}")

# --- 日常照護 API ---
@app.get("/api/daily-care")
def get_daily_care(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, s.RealName as StaffName
        FROM DailyCareRecord d
        LEFT JOIN StaffAccount s ON d.StaffID = s.StaffID
        WHERE d.ResidentID = %s
        ORDER BY d.RecordTime DESC LIMIT 50
    """, (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/daily-care")
def add_daily_care(d: DailyCareData):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        # 🚀 移除 ON DUPLICATE KEY UPDATE，允許同一天多筆不同時間紀錄
        cursor.execute("""
            INSERT INTO DailyCareRecord (ResidentID, StaffID, RecordTime, BathStatus, DiaperCount, WoundNote)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (d.ResidentID, d.StaffID, d.RecordTime, d.BathStatus, d.DiaperCount, d.WoundNote))
        conn.commit(); conn.close()
        return {"status": "success", "message": "照護紀錄已儲存"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# --- 護理紀錄 API ---
@app.get("/api/residents/{res_id}/notes")
def get_nursing_notes(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, s.RealName as StaffName 
        FROM NursingNote n
        JOIN StaffAccount s ON n.StaffID = s.StaffID
        WHERE n.ResidentID = %s 
        ORDER BY n.CreateTime DESC
    """, (res_id,))
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/residents/{res_id}/notes")
def add_nursing_note(res_id: int, data: dict):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO NursingNote (ResidentID, StaffID, NoteContent) 
            VALUES (%s, %s, %s)
        """, (res_id, data['StaffID'], data['NoteContent']))
        conn.commit(); conn.close()
        return {"status": "success", "message": "紀錄已儲存"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/chronic-diseases")
def get_diseases():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM ChronicDisease")
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.post("/api/medical-orders")
def create_medical_order(order: MedicalOrderData):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        # 1. 新增醫囑
        cursor.execute("""
            INSERT INTO MedicalOrder (ResidentID, DoctorID, OrderContent, MedName, Dosage, Schedule) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (order.ResidentID, order.DoctorID, order.OrderContent, order.MedName, order.Dosage, order.Schedule))
        
        # 🚀 取得剛產生的 OrderID
        order_id = cursor.lastrowid

        # 2. 同步產生給藥任務 (帶入 OrderID)
        cursor.execute("""
            INSERT INTO MedicationRecord (ResidentID, MedName, Dosage, Schedule, Staff_ID, IsTaken, OrderID) 
            VALUES (%s, %s, %s, %s, %s, 0, %s)
        """, (order.ResidentID, order.MedName, order.Dosage, order.Schedule, order.DoctorID, order_id))

        conn.commit(); conn.close()
        return {"status": "success", "message": "醫囑已開立"}
    except Exception as e:
        return {"status": "error", "message": f"資料庫寫入失敗: {str(e)}"}

@app.post("/api/residents/{res_id}/medical-profile")
def add_resident_disease(res_id: int, data: dict):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        # data 預期包含 DiseaseID
        cursor.execute("""
            INSERT INTO ResidentMedicalProfile (ResidentID, DiseaseID, DiagnosisDate) 
            VALUES (%s, %s, CURDATE())
        """, (res_id, data['DiseaseID']))
        conn.commit(); conn.close()
        return {"status": "success", "message": "病史已新增"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/residents/medical-profile/{profile_id}")
def delete_resident_disease(profile_id: int):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("DELETE FROM ResidentMedicalProfile WHERE ProfileID = %s", (profile_id,))
        conn.commit(); conn.close()
        return {"status": "success", "message": "病史已移除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/residents/{res_id}/medical-profile")
def get_resident_profile(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    # 🚀 修正：選取時多拿 ProfileID 以便後續刪除
    cursor.execute("""
        SELECT p.ProfileID, d.DiseaseName, d.DefaultBpThreshold, p.DiagnosisDate 
        FROM ResidentMedicalProfile p
        JOIN ChronicDisease d ON p.DiseaseID = d.DiseaseID
        WHERE p.ResidentID = %s
    """, (res_id,))
    diseases = cursor.fetchall()

    # 取得醫囑
    cursor.execute("SELECT * FROM MedicalOrder WHERE ResidentID = %s ORDER BY CreateTime DESC", (res_id,))
    orders = cursor.fetchall()

    conn.close()
    return {"status": "success", "diseases": diseases, "orders": orders}

# 🚀 升級：查詢健康紀錄時，自動附加住民的閾值與血糖血氧數據
@app.get("/api/residents/{res_id}/health-history-v2")
def get_health_history_v2(res_id: int):
    conn = get_db_connection(); cursor = conn.cursor()
    # 取得住民自訂閾值
    cursor.execute("SELECT BpThreshold FROM ResidentIdentity WHERE ResidentID = %s", (res_id,))
    res_info = cursor.fetchone()
    threshold = res_info['BpThreshold'] if res_info else 140

    # 取得歷史紀錄 (包含血糖血氧)
    cursor.execute("""
        SELECT RecordTime, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, Notes 
        FROM HealthRecord WHERE ResidentID = %s 
        ORDER BY RecordTime DESC LIMIT 20
    """, (res_id,))
    records = cursor.fetchall(); conn.close()

    return {
        "status": "success", 
        "threshold": threshold, 
        "data": records
    }

@app.delete("/api/medical-orders/{order_id}")
def delete_medical_order(order_id: int):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        # 刪除醫囑 (會連動刪除 MedicationRecord 嗎？ 
        # 為了安全起見，我們手動處理或僅刪除醫囑紀錄)
        cursor.execute("DELETE FROM MedicalOrder WHERE OrderID = %s", (order_id,))
        conn.commit(); conn.close()
        return {"status": "success", "message": "醫囑已取消"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/dashboard-stats")
def get_dashboard_stats():
    conn = get_db_connection(); cursor = conn.cursor()
    # 1. 照護等級分佈
    cursor.execute("SELECT CareLevel, COUNT(*) as count FROM ResidentIdentity GROUP BY CareLevel")
    care_levels = cursor.fetchall()

    # 2. 異常警示人數 (血壓超過其個人閾值的最新紀錄)
    cursor.execute("""
        SELECT COUNT(DISTINCT r.ResidentID) as alert_count
        FROM ResidentIdentity r
        JOIN HealthRecord h ON r.ResidentID = h.ResidentID
        WHERE h.SystolicBP > r.BpThreshold 
        AND h.RecordTime > DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    alerts = cursor.fetchone()

    # 3. 住民總數
    cursor.execute("SELECT COUNT(*) as total FROM ResidentIdentity")
    total = cursor.fetchone()

    conn.close()
    return {
        "status": "success",
        "care_distribution": care_levels,
        "alerts": alerts['alert_count'] if alerts else 0,
        "total": total['total'] if total else 0
    }

# ==========================================
# 5. 報表與統計 
# ==========================================

@app.get("/api/reports/medication-full")
def get_med_report_all():
    conn = get_db_connection(); cursor = conn.cursor()
    # 串接三張表：給藥紀錄、住民姓名、職員(護理師)姓名
    cursor.execute("""
        SELECT 
            m.RecordID, r.FullName as ResidentName, m.MedName, m.Dosage, 
            m.Schedule, m.IsTaken, s.RealName as StaffName, m.CreateTime
        FROM MedicationRecord m
        JOIN ResidentIdentity r ON m.ResidentID = r.ResidentID
        LEFT JOIN StaffAccount s ON m.Staff_ID = s.StaffID
        ORDER BY m.CreateTime DESC
        LIMIT 500
    """)
    data = cursor.fetchall(); conn.close()
    return {"status": "success", "data": data}

@app.get("/api/reports/medication-export")
def export_med_excel():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.CreateTime as '紀錄時間', r.FullName as '住民姓名', r.RoomNumber as '房號',
            m.MedName as '藥品名稱', m.Dosage as '劑量', m.Schedule as '時段',
            IF(m.IsTaken=1, '已服用', '未服用') as '狀態',
            s.RealName as '執行職員'
        FROM MedicationRecord m
        JOIN ResidentIdentity r ON m.ResidentID = r.ResidentID
        LEFT JOIN StaffAccount s ON m.Staff_ID = s.StaffID
        ORDER BY m.CreateTime DESC
    """)
    rows = cursor.fetchall(); conn.close()

    # 使用 pandas 轉換為 Excel
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='給藥紀錄報表')

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Care_Medication_Report.xlsx"}
    )

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")