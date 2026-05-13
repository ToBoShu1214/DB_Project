import requests
import random
import time
import sys

# 配置 API 網址 (如果在 Docker 外部執行，請用 localhost)
API_BASE = "http://localhost:8000/api"

def simulate_iot(resident_id):
    print(f"🚀 開始模擬住民 ID: {resident_id} 的 IOT 數據傳輸...")
    
    zones = ["房間", "餐廳", "客廳", "樓梯間", "花園"]
    
    try:
        while True:
            # 1. 模擬生理數據 (血壓、心跳)
            health_data = {
                "ResidentID": resident_id,
                "SystolicBP": random.randint(110, 160),  # 故意產生一些可能超標的數值
                "DiastolicBP": random.randint(70, 100),
                "HeartRate": random.randint(60, 100),
                "Notes": "IOT 自動上傳"
            }
            resp1 = requests.post(f"{API_BASE}/health-records", json=health_data)
            
            # 2. 模擬位置數據
            zone = random.choice(zones)
            sighting_data = {
                "ResidentID": resident_id,
                "Zone": zone,
                "X_Coordinate": round(random.uniform(0, 100), 2),
                "Y_Coordinate": round(random.uniform(0, 100), 2)
            }
            resp2 = requests.post(f"{API_BASE}/sightings", json=sighting_data)
            
            if resp1.status_code == 200 and resp2.status_code == 200:
                print(f"✅ 數據已更新 | 位置: {zone} | 血壓: {health_data['SystolicBP']}/{health_data['DiastolicBP']}")
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
