# 🚀 PHASE 5 QUICK START GUIDE

## ⚡ Khởi động nhanh Phase 5 trong 5 phút

### Bước 1: Cài đặt MongoDB

**Option A - Local MongoDB (Recommended for development):**
```bash
# Download MongoDB Community: https://www.mongodb.com/try/download/community
# Install và chạy service
net start MongoDB
```

**Option B - MongoDB Atlas (Cloud - Free 512MB):**
1. Tạo account tại: https://www.mongodb.com/cloud/atlas
2. Tạo cluster miễn phí
3. Thêm connection string vào `.env`:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=crypto_trading_db
```

### Bước 2: Khởi động Kafka

```bash
# Terminal 1
docker-compose up -d

# Kiểm tra
docker ps
# → Phải thấy: kafka, zookeeper đang chạy
```

### Bước 3: Khởi động Market Data & ML (Từ Phase 1-3)

**Terminal 2 - Market Data Producer:**
```batch
cd crypto-ml-trading-project
crypto-venv\Scripts\activate
python app\producers\market_data_producer.py
```

**Terminal 3 - ML Predictor:**
```batch
cd crypto-ml-trading-project
crypto-venv\Scripts\activate
python app\consumers\ml_predictor.py
```

### Bước 4: Khởi động Backtrader Engine

**Terminal 4:**
```batch
start_backtrader.bat
```

Kết quả:
```
✅ MongoDB Connected: crypto_trading_db
✅ User created: admin with $5,000.00
🚀 BACKTRADER WRAPPER STARTED (HYBRID MODE)
💵 Initial Balance: $5,000.00
⏳ Waiting for Kafka signals...
```

### Bước 5: Mở Dashboard

**Terminal 5:**
```batch
start_backtrader_dashboard.bat
```

Browser tự động mở: http://localhost:8501

**Login:**
- Username: `admin`
- Password: `admin123`

---

## 📊 Dashboard Features

Dashboard sẽ hiển thị:

✅ **Account Balance** - Số dư hiện tại
✅ **Realized PnL** - Lời/lỗ đã chốt
✅ **Unrealized PnL** - Lời/lỗ chưa chốt (từ lệnh đang mở)
✅ **Win Rate** - Tỷ lệ thắng
✅ **Active Position** - Lệnh đang mở (nếu có)
✅ **Trade History** - Lịch sử giao dịch
✅ **Equity Curve** - Biểu đồ vốn
✅ **Panic Button** - Đóng tất cả lệnh khẩn cấp

---

## 🧪 Test Workflow

### 1. Chờ ML Signal BUY

Terminal 3 (ML Predictor) sẽ hiển thị:
```
[12:34:56] 🤖 ML PREDICTION | BTCUSDT
           Signal: BUY
           Confidence: 82.50%
           → Published to crypto.ml_signals
```

Terminal 4 (Backtrader) sẽ tự động:
```
[12:34:56] 📡 Signal: BUY | BTCUSDT | Conf: 82.50% | Price: $68,234.00
         ✅ BUY EXECUTED: 0.0366 BTCUSDT @ $68,234.00
         💵 Cost: $2,500.00 + Fee: $2.50 = $2,502.50
         💰 Remaining Cash: $2,497.50
```

Dashboard (auto-refresh 3s) sẽ update:
- ✅ Active Position hiển thị lệnh mới
- ✅ Unrealized PnL bắt đầu thay đổi theo giá
- ✅ Trade History có record mới

### 2. Chờ ML Signal SELL

Khi giá tăng và ML predict SELL:
```
Terminal 3:
[12:38:22] 🤖 ML PREDICTION | BTCUSDT
           Signal: SELL
           Confidence: 91.20%

Terminal 4:
[12:38:22] 📡 Signal: SELL | BTCUSDT | Conf: 91.20% | Price: $68,891.00
         ✅ SELL EXECUTED: 0.0366 BTCUSDT @ $68,891.00
         💵 Revenue: $2,521.41 - Fee: $2.52 = $2,518.89
         💰 PROFIT: $16.39
         💰 New Balance: $5,016.39
```

Dashboard updates:
- ✅ Balance: $5,016.39 (+$16.39)
- ✅ Realized PnL: +$16.39
- ✅ Win Rate: 100% (1W / 0L)
- ✅ Active Position: None (lệnh đã đóng)
- ✅ Equity Curve tăng

### 3. Test Panic Button

Trong Dashboard:
1. Sidebar → "🛑 PANIC BUTTON"
2. Xác nhận warning
3. Engine sẽ đóng TẤT CẢ lệnh ngay lập tức
4. Dashboard auto-refresh → Positions cleared

---

## 🔧 Troubleshooting

### ❌ "ServerSelectionTimeoutError"
→ MongoDB chưa chạy. Khởi động MongoDB hoặc kiểm tra connection string.

### ❌ "KafkaException: Broker transport failure"
→ Kafka chưa chạy. `docker-compose up -d`

### ❌ Dashboard hiển thị "No trades yet"
→ Backtrader Engine chưa chạy hoặc chưa có ML signals. Kiểm tra Terminal 4.

### ❌ "ModuleNotFoundError: backtrader"
→ Chưa cài package. `pip install backtrader pymongo bcrypt`

---

## 📁 File Structure

```
crypto-ml-trading-project/
├── app/
│   ├── consumers/
│   │   └── backtrader_engine.py      # 🆕 Backtrader trading engine
│   ├── dashboard/
│   │   └── backtrader_app.py          # 🆕 Streamlit dashboard
│   └── services/
│       └── mongo_db.py                # 🆕 MongoDB service layer
│
├── start_backtrader.bat               # 🆕 Launch engine
├── start_backtrader_dashboard.bat     # 🆕 Launch dashboard
└── PHASE5_BACKTRADER_COMPLETION.md    # 🆕 Full documentation
```

---

## 🎯 Expected Results

Sau khi chạy đầy đủ 5 terminals:

✅ Terminal 2: Market data streaming từ Binance
✅ Terminal 3: ML predictions mỗi 30s
✅ Terminal 4: Backtrader executing trades
✅ Terminal 5: Dashboard hiển thị real-time metrics
✅ MongoDB: Lưu trữ users, trades, balances

**Metrics after 1 hour of trading:**
- Trades executed: 3-5 giao dịch
- Win rate: 60-80% (tùy market conditions)
- PnL: +/- $50-100 (với initial $5,000)
- Dashboard: Equity curve hiển thị performance

---

## 📊 MongoDB Data Inspection

**Xem trades trong MongoDB:**
```bash
mongosh

use crypto_trading_db

# Xem tất cả trades
db.trades.find().pretty()

# Xem trades của admin
db.trades.find({username: "admin"}).pretty()

# Xem balance hiện tại
db.users.findOne({username: "admin"})

# Count trades
db.trades.countDocuments({status: "CLOSED"})
```

---

## 🚀 Next Steps

Phase 5 hoàn tất! Hệ thống đã có:

✅ MongoDB persistence
✅ Backtrader trading engine
✅ Real-time dashboard
✅ Panic button emergency control

**Optional enhancements:**
- Multi-symbol trading (ETHUSDT, BNBUSDT...)
- Stop loss / Take profit
- Email/Discord notifications
- Performance reports

---

**🎉 Ready to trade with ML + Backtrader!**

Xem `PHASE5_BACKTRADER_COMPLETION.md` để biết chi tiết đầy đủ.
