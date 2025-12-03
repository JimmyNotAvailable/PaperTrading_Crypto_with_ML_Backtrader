# Hướng Dẫn Nhanh: Hệ Thống Đa Đồng Coin

## 🎯 Mục Tiêu
Nâng cấp hệ thống để hỗ trợ **5 đồng coin**: BTC, ETH, XRP, SOL, BNB

## ✅ Đã Hoàn Thành

### 1. Files Mới
- ✅ `config/symbols_config.py` - Quản lý cấu hình symbols
- ✅ `app/producers/multi_symbol_producer.py` - Producer đa symbol
- ✅ `setup_multi_symbol.py` - Script setup tự động
- ✅ `docs/MULTI_SYMBOL_GUIDE.md` - Tài liệu đầy đủ

### 2. Files Đã Cập Nhật
- ✅ `app/ml/train_models.py` - Hỗ trợ train cho nhiều symbols
- ✅ `app/ml/feature_engineering.py` - Sửa lỗi Bollinger Bands
- ✅ `app/consumers/ml_predictor.py` - Buffer riêng cho từng symbol

## 🚀 Cách Sử Dụng Nhanh

### Bước 1: Test Configuration
```bash
.\crypto-venv\Scripts\Activate.ps1
python config\symbols_config.py
```

### Bước 2: Setup Tự Động (Khuyến nghị)
```bash
python setup_multi_symbol.py
```

**Hoặc Manual:**
```bash
# Train tất cả
python app\ml\train_models.py --all

# Train từng coin
python app\ml\train_models.py --symbol BTC
python app\ml\train_models.py --symbol ETH
```

### Bước 3: Test Hệ Thống (3 Terminals)

**Terminal 1 - ML Consumer:**
```bash
.\crypto-venv\Scripts\Activate.ps1
python app\consumers\ml_predictor.py
```

**Terminal 2 - Producer:**
```bash
.\crypto-venv\Scripts\Activate.ps1
# Tất cả symbols
python app\producers\multi_symbol_producer.py --all --parallel

# Hoặc chọn lọc
python app\producers\multi_symbol_producer.py --symbols BTC ETH XRP
```

**Terminal 3 - Debug:**
```bash
.\crypto-venv\Scripts\Activate.ps1
python test_phase3_debug_ml_signals.py
```

## 📊 Các Symbols Được Hỗ Trợ

| Symbol | Tên | Format CCXT | Format Binance |
|--------|-----|-------------|----------------|
| BTC | Bitcoin | BTC/USDT | BTCUSDT |
| ETH | Ethereum | ETH/USDT | ETHUSDT |
| XRP | Ripple | XRP/USDT | XRPUSDT |
| SOL | Solana | SOL/USDT | SOLUSDT |
| BNB | Binance Coin | BNB/USDT | BNBUSDT |

## 📂 Cấu Trúc Models Mới

```
app/ml/models/
├── random_forest_BTC_latest.joblib
├── svm_BTC_latest.joblib
├── logistic_regression_BTC_latest.joblib
├── random_forest_ETH_latest.joblib
├── svm_ETH_latest.joblib
├── logistic_regression_ETH_latest.joblib
├── ... (XRP, SOL, BNB)
```

**Tổng cộng:** 15 models (3 models × 5 symbols)

## 🔧 Các Tính Năng Chính

### 1. Symbols Configuration
```python
from config.symbols_config import *

# Normalize input
normalize_symbol('btc')      # → 'BTC/USDT'
normalize_symbol('ETHUSDT')  # → 'ETH/USDT'

# Get base symbol
get_base_symbol('BTC/USDT')  # → 'BTC'

# Validate
is_valid_symbol('BTC')       # → True
is_valid_symbol('DOGE')      # → False
```

### 2. Training Options
```bash
# Tất cả symbols
python app\ml\train_models.py --all

# Một symbol
python app\ml\train_models.py --symbol ETH

# Mặc định (BTC only)
python app\ml\train_models.py
```

### 3. Producer Options
```bash
# Tất cả symbols (parallel - nhanh)
python app\producers\multi_symbol_producer.py --all --parallel

# Chọn symbols
python app\producers\multi_symbol_producer.py --symbols BTC ETH

# Sequential (chậm hơn, dễ debug)
python app\producers\multi_symbol_producer.py --all
```

## 📝 Ví Dụ Output

### Producer
```
📊 Tracking 5 symbols: BTC, ETH, XRP, SOL, BNB
📡 [BTC] Price: $68,234.50 | Vol: 1,234,567
📡 [ETH] Price: $3,456.78 | Vol: 5,678,901
📡 [XRP] Price: $0.5234 | Vol: 98,765,432
✅ Round complete: 5/5 successful
```

### ML Consumer
```
✅ Loaded models for BTC
🟢 [BTC:1] BUY | Price: $68,234.50 | Conf: 0.72 | RF:1 SVM:1

✅ Loaded models for ETH
🔴 [ETH:1] SELL | Price: $3,456.78 | Conf: 0.35 | RF:0 SVM:0
```

### Statistics
```
📊 Session statistics:
BTC:
   Total predictions: 45
   BUY signals: 12
   SELL signals: 8
   NEUTRAL: 25

ETH:
   Total predictions: 43
   BUY signals: 10
   SELL signals: 9
   NEUTRAL: 24
```

## ⚠️ Lưu Ý Quan Trọng

1. **Training Time:** 
   - 1 symbol: ~1-2 phút
   - 5 symbols: ~5-10 phút

2. **Model Files:** 
   - Phải train trước khi chạy Consumer
   - Mỗi symbol cần 3 model files

3. **Buffer Management:**
   - Consumer cần 52 candles để bắt đầu predict
   - Buffer riêng cho mỗi symbol

4. **Kafka Topics:**
   - `crypto.market_data` - Input (từ Producer)
   - `crypto.ml_signals` - Output (từ ML Consumer)

## 🐛 Troubleshooting

### "Models not found for XXX"
```bash
python app\ml\train_models.py --symbol XXX
```

### Import Error
Đảm bảo virtual environment đã activate:
```bash
.\crypto-venv\Scripts\Activate.ps1
```

### Producer không gửi data
Kiểm tra Kafka đang chạy:
```bash
docker ps
```

## 📚 Tài Liệu Đầy Đủ

Xem chi tiết: `docs/MULTI_SYMBOL_GUIDE.md`

## 🎯 Next Steps

Sau khi test thành công, bạn có thể:
1. Tích hợp vào Discord Bot (`app/bot.py`)
2. Thêm vào Streamlit Dashboard
3. Kết nối với Backtrader Decision Engine

---

**Để bắt đầu ngay:**
```bash
.\crypto-venv\Scripts\Activate.ps1
python setup_multi_symbol.py
```
