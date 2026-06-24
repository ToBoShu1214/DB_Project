-- ==========================================
-- 示範資料 (seed.sql) - 自動載入版
--
-- 透過 docker-compose.yml 掛載到 /docker-entrypoint-initdb.d/，
-- 會在資料庫「第一次建立」時，緊接著 init.sql 之後自動執行
-- (Docker 會依檔名排序執行，init.sql 在 seed.sql 之前)。
--
-- ⚠️ 此檔案只會在資料卷 (volume) 第一次建立時自動跑。如果本機已經
-- 跑過 docker-compose 並有舊資料卷，要先 `docker-compose down -v`
-- 清掉舊資料卷，重新 `docker-compose up -d --build` 才會套用。
--
-- main.py 的 init_db() 之後也會建立同樣的表/預設值，這裡用
-- IF NOT EXISTS / INSERT IGNORE，兩邊重複執行不會衝突或報錯。
-- ==========================================

-- 1. 房號 / 狀態 / 照護等級 預設值 (SystemRoom 等表已由 init.sql 建立，這裡補資料)
INSERT IGNORE INTO SystemRoom (RoomNumber, IsWard) VALUES
    ('401房',1),('402房',1),('403房',1),('404房',1),('405房',1),('406房',1),
    ('407房',1),('408房',1),('409房',1),('410房',1),('411房',1),('412房',1),
    ('交誼廳',0),('護理站',0),('行政辦公室',0),('走廊',0);

INSERT IGNORE INTO SystemStatus (StatusName) VALUES ('入住中'),('住院'),('請假'),('退宿');
INSERT IGNORE INTO SystemCareLevel (LevelName) VALUES ('輕度'),('中度'),('重度');

-- 2. 補建後端才會建立的擴充表格 (跟 main.py init_db() 結構一致)
CREATE TABLE IF NOT EXISTS ChronicDisease (
    DiseaseID INT AUTO_INCREMENT PRIMARY KEY,
    DiseaseName VARCHAR(100) NOT NULL UNIQUE,
    DefaultBpThreshold INT DEFAULT 140
);
INSERT IGNORE INTO ChronicDisease (DiseaseName, DefaultBpThreshold) VALUES ('高血壓',155),('糖尿病',140),('心臟病',135);

CREATE TABLE IF NOT EXISTS ResidentMedicalProfile (
    ProfileID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    DiseaseID INT,
    DiagnosisDate DATE,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE,
    FOREIGN KEY (DiseaseID) REFERENCES ChronicDisease(DiseaseID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS NursingNote (
    NoteID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    StaffID INT,
    NoteContent TEXT,
    CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ResidentSighting (
    SightingID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    Zone VARCHAR(100),
    X_Coordinate FLOAT DEFAULT 0,
    Y_Coordinate FLOAT DEFAULT 0,
    Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
);

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
);

CREATE TABLE IF NOT EXISTS VaccinationRecord (
    VaccineID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    VaccineType VARCHAR(100),
    Brand VARCHAR(100),
    DoseDate DATE,
    NextDoseDate DATE,
    CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
);

ALTER TABLE MedicationRecord ADD COLUMN IF NOT EXISTS OrderID INT;

-- 3. 員工帳號（一個已核准的護理師、一個待審核的新人）
INSERT IGNORE INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES
    ('nurse01', '123456', '王小美', '護理師', 1),
    ('newnurse', '123456', '林新人', '護理師', 0);

-- 4. 住民資料 (用 WHERE NOT EXISTS 避免重複執行時插入重複資料)
INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, BpThreshold, Height, Weight, Allergies, RoomID, StatusID, CareLevelID)
SELECT '陳大文', '男', '1940-03-12', '中度', '401房', '入住中', 140, 168, 62, '無',
    (SELECT RoomID FROM SystemRoom WHERE RoomNumber='401房'),
    (SELECT StatusID FROM SystemStatus WHERE StatusName='入住中'),
    (SELECT LevelID FROM SystemCareLevel WHERE LevelName='中度')
WHERE NOT EXISTS (SELECT 1 FROM ResidentIdentity WHERE FullName='陳大文');

INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, BpThreshold, Height, Weight, Allergies, RoomID, StatusID, CareLevelID)
SELECT '林秀英', '女', '1938-07-25', '輕度', '402房', '入住中', 135, 155, 50, '對青黴素過敏',
    (SELECT RoomID FROM SystemRoom WHERE RoomNumber='402房'),
    (SELECT StatusID FROM SystemStatus WHERE StatusName='入住中'),
    (SELECT LevelID FROM SystemCareLevel WHERE LevelName='輕度')
WHERE NOT EXISTS (SELECT 1 FROM ResidentIdentity WHERE FullName='林秀英');

INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, BpThreshold, Height, Weight, Allergies, RoomID, StatusID, CareLevelID)
SELECT '張福生', '男', '1945-11-02', '重度', '403房', '住院', 150, 172, 58, '無',
    (SELECT RoomID FROM SystemRoom WHERE RoomNumber='403房'),
    (SELECT StatusID FROM SystemStatus WHERE StatusName='住院'),
    (SELECT LevelID FROM SystemCareLevel WHERE LevelName='重度')
WHERE NOT EXISTS (SELECT 1 FROM ResidentIdentity WHERE FullName='張福生');

-- 5. 家屬帳號 (密碼皆為 123456，可用電話號碼登入家屬端)
INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, Password, IsEmergencyContact)
SELECT (SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), '陳小華', '兒子', '0911000001', '123456', 1
WHERE NOT EXISTS (SELECT 1 FROM FamilyMember WHERE Phone='0911000001');

INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, Password, IsEmergencyContact)
SELECT (SELECT ResidentID FROM ResidentIdentity WHERE FullName='林秀英'), '林志強', '兒子', '0911000002', '123456', 1
WHERE NOT EXISTS (SELECT 1 FROM FamilyMember WHERE Phone='0911000002');

INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, Password, IsEmergencyContact)
SELECT (SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), '張美玲', '女兒', '0911000003', '123456', 1
WHERE NOT EXISTS (SELECT 1 FROM FamilyMember WHERE Phone='0911000003');

-- 6. 生理量測紀錄
INSERT INTO HealthRecord (ResidentID, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, RecordTime, Notes) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), 135, 85, 72, 110, 97, NOW() - INTERVAL 2 DAY, '量測正常'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), 142, 88, 75, 118, 96, NOW() - INTERVAL 1 DAY, '飯後測量'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='林秀英'), 128, 80, 68, 102, 98, NOW() - INTERVAL 1 DAY, '量測正常'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), 158, 95, 80, 130, 94, NOW(), '血壓偏高，已通知醫師');

-- 7. 慢性病關聯
INSERT INTO ResidentMedicalProfile (ResidentID, DiseaseID, DiagnosisDate) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), (SELECT DiseaseID FROM ChronicDisease WHERE DiseaseName='高血壓'), '2020-05-10'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), (SELECT DiseaseID FROM ChronicDisease WHERE DiseaseName='糖尿病'), '2018-09-01');

-- 8. 醫囑與給藥紀錄
INSERT INTO MedicalOrder (ResidentID, OrderContent, MedName, Dosage, Schedule) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), '降血壓藥物，每日早晚服用', '脈優', '1顆', '早晚飯後'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), '降血糖藥物', '美福明', '1顆', '三餐飯後');

INSERT INTO MedicationRecord (ResidentID, MedName, Dosage, Schedule, Staff_ID, IsTaken, OrderID) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), '脈優', '1顆', '早飯後',
        (SELECT StaffID FROM StaffAccount WHERE Username='admin'), 1,
        (SELECT OrderID FROM MedicalOrder WHERE MedName='脈優')),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), '美福明', '1顆', '午飯後',
        (SELECT StaffID FROM StaffAccount WHERE Username='admin'), 0,
        (SELECT OrderID FROM MedicalOrder WHERE MedName='美福明'));

-- 9. 護理紀錄
INSERT INTO NursingNote (ResidentID, StaffID, NoteContent) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), (SELECT StaffID FROM StaffAccount WHERE Username='admin'), '今日精神狀況良好，食慾正常。'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), (SELECT StaffID FROM StaffAccount WHERE Username='admin'), '血壓偏高，已聯絡家屬並通知醫師調整用藥。');

-- 10. 即時位置紀錄 (對應地圖功能)
INSERT INTO ResidentSighting (ResidentID, Zone, X_Coordinate, Y_Coordinate) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), '交誼廳', 12.5, 8.3),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='林秀英'), '402房', 30.0, 14.0),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='張福生'), '護理站', 5.0, 20.0);

-- 11. 日常照護紀錄
INSERT INTO DailyCareRecord (ResidentID, StaffID, RecordTime, BathStatus, DiaperCount, WoundNote) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), (SELECT StaffID FROM StaffAccount WHERE Username='admin'), NOW() - INTERVAL 1 DAY, 1, 2, NULL),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='林秀英'), (SELECT StaffID FROM StaffAccount WHERE Username='admin'), NOW(), 1, 1, NULL);

-- 12. 疫苗接種紀錄
INSERT INTO VaccinationRecord (ResidentID, VaccineType, Brand, DoseDate, NextDoseDate) VALUES
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='陳大文'), '流感疫苗', 'GSK', '2025-11-01', '2026-11-01'),
    ((SELECT ResidentID FROM ResidentIdentity WHERE FullName='林秀英'), '肺炎鏈球菌疫苗', 'Pfizer', '2025-06-15', NULL);
