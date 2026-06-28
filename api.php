<?php
// ==========================================
// 智慧長照管理系統 API (PHP 版本)
// ==========================================
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once 'db_config.php';

try {
    $dsn = "mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4";
    $pdo = new PDO($dsn, $DB_USER, $DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(["status" => "error", "message" => "資料庫連線失敗: " . $e->getMessage()]);
    exit;
}

$endpoint = isset($_GET['endpoint']) ? rtrim($_GET['endpoint'], '/') : '';
$method = $_SERVER['REQUEST_METHOD'];
$input = json_decode(file_get_contents('php://input'), true);

function response($data, $status_code = 200) {
    http_response_code($status_code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

// 簡單的路徑比對
function match_path($pattern, $path, &$matches) {
    $pattern = preg_replace('/\{([a-zA-Z0-9_]+)\}/', '(?P<\1>[a-zA-Z0-9_-]+)', $pattern);
    $pattern = "@^" . $pattern . "$@";
    return preg_match($pattern, $path, $matches);
}

// ==========================================
// API 路由處理
// ==========================================
try {
    // 1. 系統權限 & 帳號管理
    if ($endpoint === 'status' && $method === 'GET') {
        response(["status" => "系統運作中"]);
    }
    
    if ($endpoint === 'login' && $method === 'POST') {
        $stmt = $pdo->prepare("SELECT StaffID, Username, RealName, Role, IsApproved FROM StaffAccount WHERE Username = ? AND Password = ?");
        $stmt->execute([$input['Username'], $input['Password']]);
        $user = $stmt->fetch();
        if (!$user) {
            response(["detail" => "帳號或密碼錯誤"], 401);
        }
        if ($user['IsApproved'] == 0) {
            response(["detail" => "帳號審核中，請聯繫管理員。"], 403);
        }
        response(["status" => "success", "user_info" => $user]);
    }
    
    if ($endpoint === 'register' && $method === 'POST') {
        $stmt = $pdo->prepare("SELECT * FROM StaffAccount WHERE Username = ?");
        $stmt->execute([$input['Username']]);
        if ($stmt->fetch()) response(["status" => "error", "message" => "此帳號已被註冊"]);
        $is_approved = ($input['Username'] === 'admin') ? 1 : 0;
        $stmt = $pdo->prepare("INSERT INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES (?,?,?,?,?)");
        $stmt->execute([$input['Username'], $input['Password'], $input['RealName'], $input['Role'], $is_approved]);
        response(["status" => "success"]);
    }
    
    if ($endpoint === 'staff' && $method === 'GET') {
        $stmt = $pdo->query("SELECT StaffID, Username, RealName, Role, IsApproved, Password FROM StaffAccount ORDER BY StaffID DESC");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'staff' && $method === 'POST') {
        $stmt = $pdo->prepare("INSERT INTO StaffAccount (Username, Password, RealName, Role, IsApproved) VALUES (?,?,?,?,?)");
        $stmt->execute([$input['Username'], $input['Password'], $input['RealName'], $input['Role'], $input['IsApproved']]);
        response(["status" => "success"]);
    }
    
    if (match_path('staff/{id}', $endpoint, $matches) && $method === 'PUT') {
        $stmt = $pdo->prepare("UPDATE StaffAccount SET Username=?, Password=?, RealName=?, Role=?, IsApproved=? WHERE StaffID=?");
        $stmt->execute([$input['Username'], $input['Password'], $input['RealName'], $input['Role'], $input['IsApproved'], $matches['id']]);
        response(["status" => "success"]);
    }
    
    if (match_path('staff/{id}', $endpoint, $matches) && $method === 'DELETE') {
        $stmt = $pdo->prepare("DELETE FROM StaffAccount WHERE StaffID=?");
        $stmt->execute([$matches['id']]);
        response(["status" => "success"]);
    }
    
    if ($endpoint === 'family/login' && $method === 'POST') {
        $stmt = $pdo->prepare("SELECT FamilyID, ResidentID, FullName FROM FamilyMember WHERE Phone = ? AND Password = ?");
        $stmt->execute([$input['Phone'], $input['Password']]);
        $user = $stmt->fetch();
        if ($user) response(["status" => "success", "message" => "歡迎，{$user['FullName']} 家屬", "user_info" => $user]);
        response(["detail" => "電話號碼或密碼錯誤"], 401);
    }
    
    if ($endpoint === 'family/register' && $method === 'POST') {
        $stmt = $pdo->prepare("SELECT * FROM ResidentIdentity WHERE ResidentID = ?");
        $stmt->execute([$input['ResidentID']]);
        if (!$stmt->fetch()) response(["status" => "error", "message" => "找不到該住民編號"]);
        $stmt = $pdo->prepare("INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, Password) VALUES (?,?,?,?,?)");
        $stmt->execute([$input['ResidentID'], $input['FullName'], $input['Relationship'], $input['Phone'], $input['Password']]);
        response(["status" => "success"]);
    }
    
    // 2. 選項與住民管理
    if ($endpoint === 'options/rooms' && $method === 'GET') {
        $stmt = $pdo->query("SELECT * FROM SystemRoom");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    if ($endpoint === 'options/statuses' && $method === 'GET') {
        $stmt = $pdo->query("SELECT * FROM SystemStatus");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    if ($endpoint === 'options/care-levels' && $method === 'GET') {
        $stmt = $pdo->query("SELECT * FROM SystemCareLevel");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'residents' && $method === 'GET') {
        $stmt = $pdo->query("
            SELECT ri.*, sr.RoomNumber as RoomNumberDisplay, ss.StatusName as StatusDisplay, scl.LevelName as CareLevelDisplay
            FROM ResidentIdentity ri
            LEFT JOIN SystemRoom sr ON ri.RoomID = sr.RoomID
            LEFT JOIN SystemStatus ss ON ri.StatusID = ss.StatusID
            LEFT JOIN SystemCareLevel scl ON ri.CareLevelID = scl.LevelID
            ORDER BY ri.ResidentID DESC
        ");
        $data = $stmt->fetchAll();
        foreach ($data as &$r) {
            if ($r['RoomNumberDisplay']) $r['RoomNumber'] = $r['RoomNumberDisplay'];
            if ($r['StatusDisplay']) $r['Status'] = $r['StatusDisplay'];
            if ($r['CareLevelDisplay']) $r['CareLevel'] = $r['CareLevelDisplay'];
        }
        response(["status" => "success", "data" => $data]);
    }
    
    if ($endpoint === 'residents/single' && $method === 'POST') {
        $stmt = $pdo->prepare("
            INSERT INTO ResidentIdentity (FullName, Sex, DateOfBirth, CareLevel, RoomNumber, Status, Height, Weight, CDR, CMS, Allergies, IdentityNumber, HealthCardNumber, RoomID, StatusID, CareLevelID) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ");
        $stmt->execute([
            $input['FullName'], $input['Sex'], $input['DateOfBirth'], $input['CareLevel'], $input['RoomNumber'], $input['Status'],
            $input['Height'] ?? null, $input['Weight'] ?? null, $input['CDR'] ?? null, $input['CMS'] ?? null, $input['Allergies'] ?? null,
            $input['IdentityNumber'] ?? null, $input['HealthCardNumber'] ?? null, $input['RoomID'] ?? null, $input['StatusID'] ?? null, $input['CareLevelID'] ?? null
        ]);
        response(["status" => "success"]);
    }
    
    if (match_path('residents/{id}', $endpoint, $matches)) {
        $res_id = $matches['id'];
        if ($method === 'GET') {
            $stmt = $pdo->prepare("
                SELECT ri.*, sr.RoomNumber as RoomNumberDisplay, ss.StatusName as StatusDisplay, scl.LevelName as CareLevelDisplay
                FROM ResidentIdentity ri
                LEFT JOIN SystemRoom sr ON ri.RoomID = sr.RoomID
                LEFT JOIN SystemStatus ss ON ri.StatusID = ss.StatusID
                LEFT JOIN SystemCareLevel scl ON ri.CareLevelID = scl.LevelID
                WHERE ri.ResidentID = ?
            ");
            $stmt->execute([$res_id]);
            $data = $stmt->fetch();
            if ($data) {
                if ($data['RoomNumberDisplay']) $data['RoomNumber'] = $data['RoomNumberDisplay'];
                if ($data['StatusDisplay']) $data['Status'] = $data['StatusDisplay'];
                if ($data['CareLevelDisplay']) $data['CareLevel'] = $data['CareLevelDisplay'];
            }
            response(["status" => "success", "data" => $data]);
        }
        if ($method === 'PUT') {
            $stmt = $pdo->prepare("
                UPDATE ResidentIdentity 
                SET FullName=?, Sex=?, DateOfBirth=?, CareLevel=?, RoomNumber=?, Status=?, BpThreshold=?, Height=?, Weight=?, CDR=?, CMS=?, Allergies=?, IdentityNumber=?, HealthCardNumber=?, RoomID=?, StatusID=?, CareLevelID=?
                WHERE ResidentID=?
            ");
            $stmt->execute([
                $input['FullName'], $input['Sex'], $input['DateOfBirth'], $input['CareLevel'], $input['RoomNumber'], $input['Status'],
                $input['BpThreshold'] ?? 140, $input['Height'] ?? null, $input['Weight'] ?? null, $input['CDR'] ?? null, $input['CMS'] ?? null, $input['Allergies'] ?? null,
                $input['IdentityNumber'] ?? null, $input['HealthCardNumber'] ?? null, $input['RoomID'] ?? null, $input['StatusID'] ?? null, $input['CareLevelID'] ?? null,
                $res_id
            ]);
            response(["status" => "success"]);
        }
        if ($method === 'DELETE') {
            $stmt = $pdo->prepare("DELETE FROM ResidentIdentity WHERE ResidentID=?");
            $stmt->execute([$res_id]);
            response(["status" => "success"]);
        }
    }
    
    // 3. 家屬、健康、位置
    if ($endpoint === 'family-members' && $method === 'GET') {
        $stmt = $pdo->query("SELECT f.*, r.FullName as ResidentName FROM FamilyMember f LEFT JOIN ResidentIdentity r ON f.ResidentID = r.ResidentID");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'family-members' && $method === 'POST') {
        $stmt = $pdo->prepare("INSERT INTO FamilyMember (ResidentID, FullName, Relationship, Phone, IsEmergencyContact) VALUES (?,?,?,?,?)");
        $stmt->execute([$input['ResidentID'], $input['FullName'], $input['Relationship'], $input['Phone'], $input['IsEmergencyContact'] ?? 0]);
        response(["status" => "success"]);
    }
    
    if (match_path('family-members/{id}', $endpoint, $matches)) {
        if ($method === 'PUT') {
            $stmt = $pdo->prepare("UPDATE FamilyMember SET ResidentID=?, FullName=?, Relationship=?, Phone=?, IsEmergencyContact=? WHERE FamilyID=?");
            $stmt->execute([$input['ResidentID'], $input['FullName'], $input['Relationship'], $input['Phone'], $input['IsEmergencyContact'], $matches['id']]);
            response(["status" => "success"]);
        }
        if ($method === 'DELETE') {
            $stmt = $pdo->prepare("DELETE FROM FamilyMember WHERE FamilyID=?");
            $stmt->execute([$matches['id']]);
            response(["status" => "success"]);
        }
    }
    
    if (match_path('reports/health-summary/{id}', $endpoint, $matches) && $method === 'GET') {
        $stmt = $pdo->prepare("SELECT AVG(SystolicBP) as AvgSystolic, AVG(DiastolicBP) as AvgDiastolic, AVG(HeartRate) as AvgHeartRate, COUNT(*) as TotalRecords FROM HealthRecord WHERE ResidentID=?");
        $stmt->execute([$matches['id']]);
        response(["status" => "success", "summary" => $stmt->fetch()]);
    }
    
    if (match_path('residents/{id}/health-history', $endpoint, $matches) && $method === 'GET') {
        $stmt = $pdo->prepare("SELECT RecordTime, SystolicBP, DiastolicBP, HeartRate, Notes FROM HealthRecord WHERE ResidentID = ? ORDER BY RecordTime ASC LIMIT 10");
        $stmt->execute([$matches['id']]);
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'health-records' && $method === 'POST') {
        if (!empty($input['RecordTime'])) {
            $stmt = $pdo->prepare("INSERT INTO HealthRecord (ResidentID, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, RecordTime, Notes) VALUES (?,?,?,?,?,?,?,?)");
            $stmt->execute([$input['ResidentID'], $input['SystolicBP'], $input['DiastolicBP'], $input['HeartRate'], $input['BloodSugar'] ?? null, $input['BloodOxygen'] ?? null, $input['RecordTime'], $input['Notes'] ?? null]);
        } else {
            $stmt = $pdo->prepare("INSERT INTO HealthRecord (ResidentID, SystolicBP, DiastolicBP, HeartRate, BloodSugar, BloodOxygen, Notes) VALUES (?,?,?,?,?,?,?)");
            $stmt->execute([$input['ResidentID'], $input['SystolicBP'], $input['DiastolicBP'], $input['HeartRate'], $input['BloodSugar'] ?? null, $input['BloodOxygen'] ?? null, $input['Notes'] ?? null]);
        }
        response(["status" => "success"]);
    }
    
    // 給藥、疫苗、紀錄
    if (match_path('residents/{id}/medications', $endpoint, $matches) && $method === 'GET') {
        $stmt = $pdo->prepare("
            SELECT * FROM MedicationRecord 
            WHERE ResidentID = ? 
            AND (IsTaken = 0 OR (IsTaken = 1 AND DATE(CreateTime) = CURDATE()))
            ORDER BY IsTaken ASC, CreateTime DESC
        ");
        $stmt->execute([$matches['id']]);
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'medications' && $method === 'POST') {
        $stmt = $pdo->prepare("INSERT INTO MedicationRecord (ResidentID, MedName, Dosage, Schedule, Staff_ID, IsTaken) VALUES (?, ?, ?, ?, ?, 0)");
        $stmt->execute([$input['ResidentID'], $input['MedName'], $input['Dosage'], $input['Schedule'], $input['Staff_ID']]);
        response(["status" => "success"]);
    }
    
    if (match_path('medications/{id}/status', $endpoint, $matches) && ($method === 'GET' || $method === 'PUT' || $method === 'POST')) {
        // FastAPI 之前用 GET 收 Body，這裡兼容各種可能
        $isTaken = isset($input['IsTaken']) ? $input['IsTaken'] : (isset($_GET['IsTaken']) ? $_GET['IsTaken'] : 1);
        $staffID = isset($input['Staff_ID']) ? $input['Staff_ID'] : (isset($_GET['Staff_ID']) ? $_GET['Staff_ID'] : 1);
        $stmt = $pdo->prepare("UPDATE MedicationRecord SET IsTaken=?, Staff_ID=? WHERE RecordID=?");
        $stmt->execute([$isTaken, $staffID, $matches['id']]);
        response(["status" => "success"]);
    }
    
    if ($endpoint === 'residents/locations/all' && $method === 'GET') {
        $stmt = $pdo->query("
            SELECT rs.ResidentID, ri.FullName, rs.Zone, rs.X_Coordinate, rs.Y_Coordinate, rs.Timestamp 
            FROM ResidentSighting rs
            JOIN ResidentIdentity ri ON rs.ResidentID = ri.ResidentID
            WHERE (rs.ResidentID, rs.Timestamp) IN (
                SELECT ResidentID, MAX(Timestamp)
                FROM ResidentSighting
                GROUP BY ResidentID
            )
        ");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'sightings' && $method === 'POST') {
        $stmt = $pdo->prepare("INSERT INTO ResidentSighting (ResidentID, Zone, X_Coordinate, Y_Coordinate) VALUES (?, ?, ?, ?)");
        $stmt->execute([$input['ResidentID'], $input['Zone'], $input['X_Coordinate'], $input['Y_Coordinate']]);
        response(["status" => "success"]);
    }
    
    if ($endpoint === 'daily-care') {
        if ($method === 'GET') {
            $stmt = $pdo->prepare("
                SELECT d.*, s.RealName as StaffName
                FROM DailyCareRecord d
                LEFT JOIN StaffAccount s ON d.StaffID = s.StaffID
                WHERE d.ResidentID = ?
                ORDER BY d.RecordTime DESC LIMIT 50
            ");
            $stmt->execute([$_GET['res_id']]);
            response(["status" => "success", "data" => $stmt->fetchAll()]);
        }
        if ($method === 'POST') {
            $stmt = $pdo->prepare("
                INSERT INTO DailyCareRecord (ResidentID, StaffID, RecordTime, BathStatus, DiaperCount, WoundNote)
                VALUES (?, ?, ?, ?, ?, ?)
            ");
            $stmt->execute([$input['ResidentID'], $input['StaffID'], $input['RecordTime'], $input['BathStatus'], $input['DiaperCount'], $input['WoundNote'] ?? null]);
            response(["status" => "success", "message" => "照護紀錄已儲存"]);
        }
    }
    
    if (match_path('residents/{id}/notes', $endpoint, $matches)) {
        if ($method === 'GET') {
            $stmt = $pdo->prepare("
                SELECT n.*, s.RealName as StaffName 
                FROM NursingNote n
                JOIN StaffAccount s ON n.StaffID = s.StaffID
                WHERE n.ResidentID = ? 
                ORDER BY n.CreateTime DESC
            ");
            $stmt->execute([$matches['id']]);
            response(["status" => "success", "data" => $stmt->fetchAll()]);
        }
        if ($method === 'POST') {
            $stmt = $pdo->prepare("INSERT INTO NursingNote (ResidentID, StaffID, NoteContent) VALUES (?, ?, ?)");
            $stmt->execute([$matches['id'], $input['StaffID'], $input['NoteContent']]);
            response(["status" => "success"]);
        }
    }
    
    if ($endpoint === 'chronic-diseases' && $method === 'GET') {
        $stmt = $pdo->query("SELECT * FROM ChronicDisease");
        response(["status" => "success", "data" => $stmt->fetchAll()]);
    }
    
    if ($endpoint === 'medical-orders' && $method === 'POST') {
        $stmt = $pdo->prepare("INSERT INTO MedicalOrder (ResidentID, DoctorID, OrderContent, MedName, Dosage, Schedule) VALUES (?, ?, ?, ?, ?, ?)");
        $stmt->execute([$input['ResidentID'], $input['DoctorID'], $input['OrderContent'], $input['MedName'], $input['Dosage'], $input['Schedule']]);
        $order_id = $pdo->lastInsertId();
        
        $stmt2 = $pdo->prepare("INSERT INTO MedicationRecord (ResidentID, MedName, Dosage, Schedule, Staff_ID, IsTaken, OrderID) VALUES (?, ?, ?, ?, ?, 0, ?)");
        $stmt2->execute([$input['ResidentID'], $input['MedName'], $input['Dosage'], $input['Schedule'], $input['DoctorID'], $order_id]);
        response(["status" => "success"]);
    }
    
    if (match_path('residents/{id}/medical-profile', $endpoint, $matches)) {
        if ($method === 'GET') {
            $stmt = $pdo->prepare("
                SELECT p.ProfileID, d.DiseaseName, d.DefaultBpThreshold, p.DiagnosisDate 
                FROM ResidentMedicalProfile p
                JOIN ChronicDisease d ON p.DiseaseID = d.DiseaseID
                WHERE p.ResidentID = ?
            ");
            $stmt->execute([$matches['id']]);
            $diseases = $stmt->fetchAll();
            
            $stmt2 = $pdo->prepare("SELECT * FROM MedicalOrder WHERE ResidentID = ? ORDER BY CreateTime DESC");
            $stmt2->execute([$matches['id']]);
            $orders = $stmt2->fetchAll();
            response(["status" => "success", "diseases" => $diseases, "orders" => $orders]);
        }
        if ($method === 'POST') {
            $stmt = $pdo->prepare("INSERT INTO ResidentMedicalProfile (ResidentID, DiseaseID, DiagnosisDate) VALUES (?, ?, CURDATE())");
            $stmt->execute([$matches['id'], $input['DiseaseID']]);
            response(["status" => "success"]);
        }
    }
    
    if (match_path('residents/medical-profile/{id}', $endpoint, $matches) && $method === 'DELETE') {
        $stmt = $pdo->prepare("DELETE FROM ResidentMedicalProfile WHERE ProfileID = ?");
        $stmt->execute([$matches['id']]);
        response(["status" => "success"]);
    }
    
    // 預設 404
    response(["status" => "error", "message" => "Endpoint not found: $endpoint"], 404);

} catch (Exception $e) {
    response(["status" => "error", "message" => $e->getMessage()], 500);
}
?>
