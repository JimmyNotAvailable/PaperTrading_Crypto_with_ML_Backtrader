# ✅ PHASE 5: LỖI ĐÃ SỬA & HƯỚNG DẪN CHẠY

## 🔧 CÁC LỖI ĐÃ SỬA

### 1. **Type Hints trong `mongo_db.py`**

**Lỗi:** 
- `symbol: str = None` không đúng kiểu Optional
- Missing null check trong `update_balance`

**Đã sửa:**
```python
# Before
def get_open_trade(self, username: str, symbol: str = None)

# After  
def get_open_trade(self, username: str, symbol: Optional[str] = None)

# Before
print(f"💰 Balance updated: {username} -> ${user['current_balance']:,.2f}")

# After
if user:
    print(f"💰 Balance updated: {username} -> ${user['current_balance']:,.2f}")
```

### 2. **Null Checks trong `backtrader_app.py`**

**Lỗi:**
- `st.session_state.user` có thể là None
- Missing type guard

**Đã sửa:**
```python
# Added type guard
if st.session_state.user is None:
    st.error("❌ Session expired! Please login again.")
    st.session_state.logged_in = False
    st.rerun()

user = db.get_user(st.session_state.user['username'])
if not user:
    st.error("❌ User not found! Please login again.")
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()
```

### 3. **Docker Configuration**

**Đã cập nhật:**
- ✅ `docker-compose.yml` - Thêm `backtrader-engine` và `backtrader-dashboard` services
- ✅ `entrypoint.sh` - Thêm support cho Phase 5 services
- ✅ `.dockerignore` - Tối ưu build context

---

## 🚀 HƯỚNG DẪN CHẠY PHASE 5 (WITHOUT DOCKER)

Do Docker có vấn đề tạm thời, chạy Phase 5 bằng cách thủ công:

### Bước 1: Khởi động MongoDB

**Option A - MongoDB Local:**
```bash
mongod --dbpath G:\MongoDB\data
# Hoặc
net start MongoDB
```

**Option B - MongoDB Atlas (Recommended):**
1. Tạo cluster free tại https://cloud.mongodb.com
2. Copy connection string
3. Update `.env`:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=crypto_trading_db
```

### Bước 2: Khởi động Kafka (Docker)

```bash
# Terminal 1
docker run -d --name zookeeper -p 2181:2181 confluentinc/cp-zookeeper:7.4.0 \
  -e ZOOKEEPER_CLIENT_PORT=2181

# Terminal 2  
docker run -d --name kafka -p 9092:9092 confluentinc/cp-kafka:7.4.0 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
```

**Hoặc dùng docker-compose cho Kafka only:**
```bash
docker-compose up -d kafka zookeeper kafka-ui
```

### Bước 3: Chạy Phase 1-3 Components

**Terminal 3 - Market Data Producer:**
```bash
cd crypto-ml-trading-project
.\crypto-venv\Scripts\Activate.ps1
python app\producers\market_data_producer.py
```

**Terminal 4 - ML Predictor:**
```bash
cd crypto-ml-trading-project
.\crypto-venv\Scripts\Activate.ps1
python app\consumers\ml_predictor.py
```

### Bước 4: Khởi động Phase 5

**Terminal 5 - Backtrader Engine:**
```bash
.\start_backtrader.bat
```

**Terminal 6 - Backtrader Dashboard:**
```bash
.\start_backtrader_dashboard.bat
```

### Bước 5: Access Dashboard

- **URL:** http://localhost:8501
- **Login:** `admin` / `admin123`

---

## 📊 KIỂM TRA HỆ THỐNG

### Verify MongoDB
```bash
python -c "from app.services.mongo_db import MongoDB; db = MongoDB(); print('✅ MongoDB OK'); db.close()"
```

### Verify Packages
```bash
python -c "import backtrader, pymongo, bcrypt; print('✅ All packages OK')"
```

### Check Kafka
```bash
docker ps | findstr kafka
# Should see: kafka, zookeeper running
```

---

## 🐛 TROUBLESHOOTING DOCKER

Nếu muốn sử dụng Docker, làm theo:

### Fix Docker Desktop Issue

1. **Restart Docker:**
```bash
# Stop
Stop-Process -Name "Docker Desktop" -Force

# Start
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait 30s, then check
docker info
```

2. **Reset Docker:**
- Docker Desktop → Settings → Troubleshoot → Reset to factory defaults

3. **Build từng service:**
```bash
# Build base image first
docker-compose build web

# Then build Phase 5
docker-compose build backtrader-engine
docker-compose build backtrader-dashboard
```

### Run with Docker (Sau khi fix)

```bash
# Start infrastructure
docker-compose up -d mongo kafka zookeeper

# Start Phase 5
docker-compose up -d backtrader-engine backtrader-dashboard

# View logs
docker-compose logs -f backtrader-engine
docker-compose logs -f backtrader-dashboard
```

---

## ✅ SUMMARY

**Lỗi đã sửa:**
- ✅ Type hints trong `mongo_db.py` (3 locations)
- ✅ Null checks trong `backtrader_app.py` (1 location)
- ✅ Docker configuration files updated

**Files đã chỉnh sửa:**
1. `app/services/mongo_db.py` - Fixed Optional type hints và null checks
2. `app/dashboard/backtrader_app.py` - Added type guards
3. `docker-compose.yml` - Added Phase 5 services
4. `entrypoint.sh` - Added Phase 5 modes
5. `.dockerignore` - Optimized build context

**Cách chạy:**
- **Recommended:** Manual setup (5 terminals như hướng dẫn trên)
- **Alternative:** Docker (sau khi restart Docker Desktop)

**Status:** 🟢 Lỗi đã fix hoàn toàn, code sạch, ready to run!

---

**Xem chi tiết:** `PHASE5_QUICKSTART.md` và `PHASE5_BACKTRADER_COMPLETION.md`
