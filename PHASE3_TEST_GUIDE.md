# 🧪 PHASE 3 INTEGRATION TEST GUIDE

## Mục tiêu
Test toàn bộ ML pipeline: Producer → Kafka → ML Consumer → ML Signals

## Chuẩn bị

### 1. Kafka Infrastructure phải đang chạy
```powershell
docker ps --filter "name=crypto_kafka"
```
Kết quả mong đợi: `crypto_kafka` status = "Up" (healthy)

### 2. Activate Virtual Environment
```powershell
.\crypto-venv\Scripts\Activate.ps1
```

## Các Terminal cần mở

### Terminal 1: ML Consumer (Bộ não AI)
```powershell
.\crypto-venv\Scripts\Activate.ps1
python app\consumers\ml_predictor.py
```

**Kỳ vọng output:**
```
🚀 ML Predictor Service Started...
✅ All models loaded successfully
⏳ Accumulating data: 1/52
⏳ Accumulating data: 2/52
...
⏳ Accumulating data: 52/52
🟢 [1] BUY | Price: $92,726.57 | Conf: 0.75 | RF:1 SVM:1
```

### Terminal 2: Debug ML Signals (Kiểm tra output)
```powershell
.\crypto-venv\Scripts\Activate.ps1
python test_phase3_debug_ml_signals.py
```

**Kỳ vọng output:**
```
👀 Listening to topic 'crypto.ml_signals'...
🟢 [1] BUY Signal
   Symbol: BTCUSDT
   Price: $92,726.57
   Models: RF=1, SVM=1, Confidence=75.00%
```

### Terminal 3: Producer (Gửi data)
```powershell
.\crypto-venv\Scripts\Activate.ps1
python test_phase3_integration.py
```

**Kỳ vọng output:**
```
🚀 Phase 3 Integration Test
📡 Sending 60 messages...
✅ [Buffering 1/52] Sent: BTCUSDT | $92,726.57
...
✅ [Predicting 1/8] Sent: BTCUSDT | $92,750.23
```

## Luồng hoạt động

1. **Messages 1-52**: ML Consumer tích lũy data vào buffer
2. **Message 53+**: ML Consumer bắt đầu dự đoán và gửi signals
3. **Debug Consumer**: Nhận và hiển thị ML signals

## Kiểm tra thành công

✅ **Terminal 1 (ML Consumer)**:
- Thấy `⏳ Accumulating data: 52/52`
- Sau đó thấy predictions: `🟢 BUY` hoặc `🔴 SELL` hoặc `⚪ NEUTRAL`

✅ **Terminal 2 (Debug Signals)**:
- Nhận được messages từ topic `crypto.ml_signals`
- Hiển thị đầy đủ: signal, price, models, confidence

✅ **Terminal 3 (Producer)**:
- Gửi thành công 60 messages
- Không có lỗi

## Troubleshooting

### Lỗi: "Failed to load models"
**Nguyên nhân**: Chưa train models
**Giải pháp**:
```powershell
python app\ml\train_models.py
```

### Lỗi: "Kafka broker not available"
**Nguyên nhân**: Docker Kafka chưa chạy
**Giải pháp**:
```powershell
docker-compose up -d
```

### ML Consumer không dự đoán
**Nguyên nhân**: Chưa đủ 52 messages
**Giải pháp**: Chờ Producer gửi đủ data

## Dừng các services

1. **Ctrl+C** ở mỗi terminal
2. Kiểm tra statistics ở ML Consumer terminal:
```
📊 Session statistics:
   Total predictions: 8
   BUY signals: 2
   SELL signals: 1
   NEUTRAL: 5
```

## Next Steps sau khi test thành công

✅ Phase 1: Kafka Infrastructure ✅ COMPLETE
✅ Phase 2: Data Pipeline ✅ COMPLETE  
✅ Phase 3: ML Integration ✅ COMPLETE

**Phase 4**: Decision Engine (Backtrader) + Dashboard (Streamlit)
