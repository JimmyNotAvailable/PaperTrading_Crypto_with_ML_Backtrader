# 🚀 PHASE 4 - QUICK START GUIDE

Hướng dẫn nhanh để chạy và test Phase 4 Decision Engine.

---

## 📋 CHUẨN BỊ

### 1. Kafka đã chạy
```powershell
docker-compose up -d
docker ps  # Phải thấy crypto_kafka, crypto_zookeeper đang chạy
```

### 2. Virtual environment đã activate
```powershell
.\crypto-venv\Scripts\Activate.ps1
```

### 3. Backtrader đã cài
```powershell
pip install backtrader
```

---

## 🎯 OPTION 1: DEMO NHANH (Fake Signals)

**Dùng khi:** Muốn test nhanh Phase 4 mà không cần chạy Producer + ML Consumer thật

### Bước 1: Mở Terminal 1 - Fake Signal Generator

```powershell
python demo_phase4.py --send-signals --duration 300 --interval 10
```

**Kết quả:**
```
🎮 FAKE ML SIGNAL GENERATOR - DEMO MODE
================================================================================
📡 Sending signals to: crypto.ml_signals
⏱️  Duration: 300 seconds
⏳ Interval: 10 seconds
🪙 Symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT

--- Iteration #1 ---
🟢 BTCUSDT: BUY @ $68,234.50 (confidence: 75.23%)
🟢 ETHUSDT: BUY @ $3,567.89 (confidence: 68.45%)
🔴 SOLUSDT: SELL @ $143.21 (confidence: 72.15%)
...
```

### Bước 2: Mở Terminal 2 - Decision Engine

```powershell
python app\consumers\decision_engine.py
```

**Kết quả:**
```
🎯 Decision Engine initialized
   Initial Balance: $10,000.00
   Risk Parameters: SL 2.0%, TP 5.0%

========================================================================
📊 ML SIGNAL RECEIVED: BTCUSDT
   Signal: BUY
   Price: $68,234.50
   Confidence: 75.23%

🟢 OPENED POSITION: BTCUSDT
   Entry Price: $68,234.50
   Amount: 0.139705
   Total Cost: $9,533.16
   Stop Loss: $66,849.81 (-2.03%)
   Take Profit: $71,646.23 (+5.00%)
========================================================================
```

### Bước 3: Mở Terminal 3 - Monitor Orders (Optional)

```powershell
python test_phase4_integration.py
```

**Kết quả:**
```
📦 ORDER #1 - BUY BTCUSDT
⏰ Time:     2025-12-02 19:45:23
💰 Price:    $68,234.50
🛡️  Stop Loss:     $66,849.81 (-2.03%)
🎯 Take Profit:   $71,646.23 (+5.00%)
🧠 ML Confidence: 75.23%
```

---

## 🔥 OPTION 2: FULL PIPELINE (Real Data)

**Dùng khi:** Muốn test toàn bộ hệ thống từ Phase 1 → 2 → 3 → 4

### Bước 1: Terminal 1 - Binance Producer (Phase 2)

```powershell
python app\producers\binance_producer.py
```

Đợi đến khi thấy:
```
✅ Iteration #1 completed: 10/10 symbols
```

### Bước 2: Terminal 2 - ML Consumer (Phase 3)

```powershell
python app\consumers\ml_predictor.py
```

Đợi đến khi thấy:
```
🔮 Prediction: BUY | Price: 68234.50 | Confidence: 0.75
```

### Bước 3: Terminal 3 - Decision Engine (Phase 4)

```powershell
python app\consumers\decision_engine.py
```

### Bước 4: Terminal 4 - Monitor (Optional)

```powershell
python test_phase4_integration.py
```

---

## 📊 KẾT QUẢ MONG ĐỢI

### Sau 5-10 phút, bạn sẽ thấy:

**BUY Order:**
```
🟢 OPENED POSITION: BTCUSDT
   Entry: $68,234.50
   Amount: 0.139705
   Stop Loss: $66,849.81 (-2%)
   Take Profit: $71,646.23 (+5%)
   Balance: $466.84 remaining
```

**SELL Order (Take Profit):**
```
🟢 CLOSED POSITION: BTCUSDT (TAKE_PROFIT)
   Entry: $68,234.50 → Exit: $71,646.23
   PnL: +$477.07 (+5.00%)
   New Balance: $10,477.07
```

**SELL Order (Stop Loss):**
```
🔴 CLOSED POSITION: ETHUSDT (STOP_LOSS)
   Entry: $3,456.78 → Exit: $3,387.64
   PnL: -$190.14 (-2.00%)
   New Balance: $9,809.86
```

---

## 📈 XEM STATISTICS

Decision Engine tự động in statistics mỗi 10 orders:

```
================================================================================
📊 VIRTUAL EXCHANGE STATISTICS
================================================================================
Initial Balance:       $   10,000.00
Current Balance:       $   10,287.93
Total PnL:             $      287.93 (+2.88%)
Commission Paid:       $       47.16
--------------------------------------------------------------------------------
Total Trades:                      8
Winning Trades:                    5
Losing Trades:                     3
Win Rate:                      62.50%
Average Win:           $      134.52
Average Loss:          $      -89.67
Open Positions:                    1
================================================================================
```

---

## 🛠️ TROUBLESHOOTING

### ❌ "No module named 'backtrader'"
**Fix:** `pip install backtrader`

### ❌ Decision Engine không nhận signals
**Nguyên nhân:** ML Consumer chưa tích lũy đủ 52 nến  
**Fix:** Đợi 2-3 phút

### ❌ Không có BUY orders
**Kiểm tra logs để xem lý do:**
- Confidence < 60%
- RSI > 70 (overbought)
- Balance không đủ
- Đã có position cho symbol đó rồi

### ❌ Kafka connection error
**Fix:** 
```powershell
docker-compose up -d
docker ps  # Verify running
```

---

## 🎯 TESTING SCENARIOS

### Test 1: Profitable Trade
1. Chạy demo với `--interval 5` (nhanh hơn)
2. Đợi BUY order
3. Đợi giá tăng 5% → SELL (Take Profit)
4. Kiểm tra PnL > 0

### Test 2: Stop Loss
1. Chạy demo
2. Đợi BUY order
3. Đợi giá giảm 2% → SELL (Stop Loss)
4. Kiểm tra PnL < 0

### Test 3: Multi-Symbol
1. Chạy demo với cả 5 symbols
2. Xem Decision Engine quản lý nhiều positions
3. Kiểm tra balance allocation

---

## 📝 NEXT STEPS

Sau khi Phase 4 chạy ổn:

1. **Tối ưu parameters:**
   - Thử Stop Loss 3%, Take Profit 7%
   - Thử min_confidence 70%
   - Thử RSI thresholds khác

2. **Analyze performance:**
   - Win rate có đạt > 55%?
   - Average win/loss ratio?
   - Commission impact?

3. **Ready for Phase 5:**
   - Streamlit dashboard
   - Real-time charts
   - Discord notifications

---

## ✅ SUCCESS CRITERIA

Phase 4 thành công khi:

- [x] Decision Engine nhận được ML signals
- [x] Mở positions với SL/TP tự động
- [x] Đóng positions khi chạm SL/TP
- [x] Track PnL chính xác
- [x] Commission được tính đúng
- [x] Win rate > 50%
- [x] Orders được gửi vào Kafka
- [x] Statistics hiển thị đầy đủ

---

**Happy Trading!** 🚀
