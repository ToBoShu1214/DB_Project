import requests
import random
import time
import sys

# 配置 API 網址 (如果在 Docker 外部執行，請用 localhost)
API_BASE = "http://localhost:8000/api"

# 定義地圖區域與對應的座標範圍 (X, Y: 0-100)
MAP_ZONES = {
    "護理站": {"x": [5, 15], "y": [40, 75]},
    "走廊": {"x": [20, 80], "y": [45, 50]},
    "行政辦公室": {"x": [78, 92], "y": [12, 35]},
    "401房": {"x": [8, 22], "y": [12, 35]},
    "403房": {"x": [42, 48], "y": [12, 35]},
    "405房": {"x": [52, 58], "y": [12, 35]},
    "407房": {"x": [62, 68], "y": [12, 35]},
    "409房": {"x": [72, 78], "y": [12, 35]},
    "402房": {"x": [42, 48], "y": [60, 85]},
    "404房": {"x": [52, 58], "y": [60, 85]},
    "406房": {"x": [62, 68], "y": [60, 85]},
    "408房": {"x": [72, 78], "y": [60, 85]},
    "410房": {"x": [82, 88], "y": [60, 85]},
}

def simulate_iot(resident_id):
    print(f"🚀 開始模擬住民 ID: {resident_id} 的 IOT 數據傳輸 (含座標模擬)...")
    
    try:
        while True:
            # 1. 模擬生理數據 (血壓、心跳、血糖、血氧)
            health_data = {
                "ResidentID": resident_id,
                "SystolicBP": random.randint(110, 155),
                "DiastolicBP": random.randint(70, 95),
                "HeartRate": random.randint(65, 95),
                "BloodSugar": round(random.uniform(80, 130), 1),
                "BloodOxygen": random.randint(96, 100),
                "Notes": "IOT 自動傳輸"
            }
            resp1 = requests.post(f"{API_BASE}/health-records", json=health_data)
            
            # 2. 模擬位置數據 (根據地圖區域產生座標)
            zone_name = random.choice(list(MAP_ZONES.keys()))
            range_info = MAP_ZONES[zone_name]
            x = round(random.uniform(range_info["x"][0], range_info["x"][1]), 2)
            y = round(random.uniform(range_info["y"][0], range_info["y"][1]), 2)
            
            sighting_data = {
                "ResidentID": resident_id,
                "Zone": zone_name,
                "X_Coordinate": x,
                "Y_Coordinate": y
            }
            resp2 = requests.post(f"{API_BASE}/sightings", json=sighting_data)
            
            if resp1.status_code == 200 and resp2.status_code == 200:
                print(f"✅ 更新成功 | 位置: {zone_name} ({x}, {y}) | 生理: {health_data['SystolicBP']}/{health_data['DiastolicBP']}")
            else:
                print(f"❌ 上傳失敗: {resp1.text}")
                
            time.sleep(5)  # 每 5 秒更新一次
            
    except KeyboardInterrupt:
        print("\n🛑 模擬已停止")

if __name__ == "__main__":
    res_id = 1
    if len(sys.argv) > 1:
        res_id = int(sys.argv[1])
    simulate_iot(res_id)
