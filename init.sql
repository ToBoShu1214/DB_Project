-- 基礎核心資料表初始化
-- 這些是 Python 後端所依賴的基礎表，後端的 startup 腳本會進一步擴充這幾張表

CREATE TABLE IF NOT EXISTS StaffAccount (
    StaffID INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(50) UNIQUE,
    Password VARCHAR(255),
    RealName VARCHAR(50),
    Role VARCHAR(50),
    IsApproved TINYINT DEFAULT 0
);
-- 預設一組管理員帳號供測試登入
INSERT IGNORE INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES ('admin', 'admin', '預設管理員', '管理員', 1);

CREATE TABLE IF NOT EXISTS SystemRoom (
    RoomID INT AUTO_INCREMENT PRIMARY KEY, 
    RoomNumber VARCHAR(50) UNIQUE, 
    IsWard TINYINT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS SystemStatus (
    StatusID INT AUTO_INCREMENT PRIMARY KEY, 
    StatusName VARCHAR(50) UNIQUE
);

CREATE TABLE IF NOT EXISTS SystemCareLevel (
    LevelID INT AUTO_INCREMENT PRIMARY KEY, 
    LevelName VARCHAR(50) UNIQUE
);

CREATE TABLE IF NOT EXISTS ResidentIdentity (
    ResidentID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(100),
    Sex VARCHAR(10),
    DateOfBirth DATE,
    CareLevel VARCHAR(50),
    RoomNumber VARCHAR(50),
    Status VARCHAR(50),
    BpThreshold INT DEFAULT 140,
    Height FLOAT,
    Weight FLOAT,
    CDR VARCHAR(50),
    CMS VARCHAR(50),
    Allergies TEXT,
    IdentityNumber VARCHAR(20),
    HealthCardNumber VARCHAR(20),
    RoomID INT,
    StatusID INT,
    CareLevelID INT,
    FOREIGN KEY (RoomID) REFERENCES SystemRoom(RoomID),
    FOREIGN KEY (StatusID) REFERENCES SystemStatus(StatusID),
    FOREIGN KEY (CareLevelID) REFERENCES SystemCareLevel(LevelID)
);

CREATE TABLE IF NOT EXISTS FamilyMember (
    FamilyID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    FullName VARCHAR(100),
    Relationship VARCHAR(50),
    Phone VARCHAR(50),
    Password VARCHAR(255) DEFAULT '123456',
    IsEmergencyContact TINYINT DEFAULT 0,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS HealthRecord (
    RecordID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    SystolicBP INT,
    DiastolicBP INT,
    HeartRate INT,
    BloodSugar FLOAT,
    BloodOxygen INT,
    RecordTime DATETIME DEFAULT CURRENT_TIMESTAMP,
    Notes TEXT,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE
);

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
);

CREATE TABLE IF NOT EXISTS MedicationRecord (
    RecordID INT AUTO_INCREMENT PRIMARY KEY,
    ResidentID INT,
    MedName VARCHAR(100),
    Dosage VARCHAR(50),
    Schedule VARCHAR(100),
    Staff_ID INT,
    IsTaken TINYINT DEFAULT 0,
    OrderID INT,
    CreateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ResidentID) REFERENCES ResidentIdentity(ResidentID) ON DELETE CASCADE,
    FOREIGN KEY (OrderID) REFERENCES MedicalOrder(OrderID) ON DELETE CASCADE
);
