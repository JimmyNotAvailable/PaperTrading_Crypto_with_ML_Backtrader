# Hướng Dẫn Hệ Thống Đa Đồng Coin (Multi-Symbol)

## Tổng Quan

Hệ thống đã được nâng cấp để hỗ trợ **5 đồng coin phổ biến**:

| Coin | Tên Đầy Đủ | Symbol |
|------|-----------|--------|
| 🟠 BTC | Bitcoin | BTC/USDT |
| 🔵 ETH | Ethereum | ETH/USDT |
| ⚫ XRP | Ripple | XRP/USDT |
| 🟣 SOL | Solana | SOL/USDT |
| 🟡 BNB | Binance Coin | BNB/USDT |

## Kiến Trúc Đã Cập Nhật

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-SYMBOL SYSTEM                       │
└─────────────────────────────────────────────────────────────┘

Binance API (BTC, ETH, XRP, SOL, BNB)
    ↓
Multi-Symbol Producer ──→ Kafka Topic: crypto.market_data
    ↓                         (Partitioned by Symbol)
ML Predictor Consumer
    ├─ BTC Models (RF, SVM, LR)
    ├─ ETH Models (RF, SVM, LR)
    ├─ XRP Models (RF, SVM, LR)
    ├─ SOL Models (RF, SVM, LR)
    └─ BNB Models (RF, SVM, LR)
    ↓
Kafka Topic: crypto.ml_signals
    ↓
Decision Engine / Dashboard / Discord Bot
```

## Files Mới Được Tạo

### 1. **config/symbols_config.py**
Quản lý cấu hình tập trung cho tất cả các symbol:

```python
from config.symbols_config import (
    SUPPORTED_SYMBOLS,      # ['BTC/USDT', 'ETH/USDT', ...]
    normalize_symbol,       # 'btc' → 'BTC/USDT'
    get_base_symbol,        # 'BTC/USDT' → 'BTC'
    get_binance_format,     # 'BTC/USDT' → 'BTCUSDT'
    is_valid_symbol,        # Kiểm tra symbol có hợp lệ không
    get_symbol_info         # Lấy thông tin đầy đủ về symbol
)
```

**Ví dụ sử dụng:**
```python
>>> from config.symbols_config import normalize_symbol, get_symbol_info

>>> normalize_symbol('eth')
'ETH/USDT'

>>> get_symbol_info('SOL')
{
    'base': 'SOL',
    'ccxt_format': 'SOL/USDT',
    'binance_format': 'SOLUSDT',
    'display_name': 'Solana',
    'coingecko_id': 'solana'
}
```

### 2. **app/producers/multi_symbol_producer.py**
Producer nâng cấp hỗ trợ đa symbol với chế độ parallel:

```bash
# Thu thập dữ liệu cho TẤT CẢ các coin
python app/producers/multi_symbol_producer.py --all --parallel

# Thu thập cho 1 coin cụ thể
python app/producers/multi_symbol_producer.py --symbols BTC

# Thu thập cho một vài coin
python app/producers/multi_symbol_producer.py --symbols BTC ETH SOL
```

**Tính năng:**
- ✅ Parallel fetching (nhanh hơn, hiệu quả hơn)
- ✅ Sequential fetching (đơn giản, dễ debug)
- ✅ Tự động normalize symbol input
- ✅ Logging chi tiết cho từng symbol

### 3. **app/ml/train_models.py (Cập nhật)**
Script training giờ hỗ trợ train cho nhiều symbol:

```bash
# Train cho TẤT CẢ các coin (15 models: 3 models × 5 coins)
python app/ml/train_models.py --all

# Train cho 1 coin cụ thể
python app/ml/train_models.py --symbol BTC
python app/ml/train_models.py --symbol ETH

# Train mặc định (chỉ BTC)
python app/ml/train_models.py
```

**Cấu trúc models mới:**
```
app/ml/models/
├── random_forest_BTC_latest.joblib
├── svm_BTC_latest.joblib
├── logistic_regression_BTC_latest.joblib
├── random_forest_ETH_latest.joblib
├── svm_ETH_latest.joblib
├── logistic_regression_ETH_latest.joblib
├── ... (tương tự cho XRP, SOL, BNB)
└── [Timestamped versions...]
```

### 4. **app/consumers/ml_predictor.py (Cập nhật)**
Consumer giờ tự động load models cho từng symbol:

**Tính năng mới:**
- ✅ Buffer riêng biệt cho từng symbol
- ✅ Tự động load models khi nhận symbol mới
- ✅ Statistics riêng cho từng symbol
- ✅ Graceful handling khi model chưa được train

**Output mẫu:**
```
✅ Loaded models for BTC
⏳ [BTC] Accumulating data: 35/52
🟢 [BTC:1] BUY | Price: $68,234.50 | Conf: 0.72 | RF:1 SVM:1
✅ Loaded models for ETH
⏳ [ETH] Accumulating data: 12/52
🟢 [ETH:1] BUY | Price: $3,456.78 | Conf: 0.68 | RF:1 SVM:1
```

### 5. **setup_multi_symbol.py**
Script tự động hóa toàn bộ quy trình setup:

```bash
python setup_multi_symbol.py
```

**Workflow:**
1. ✅ Kiểm tra virtual environment
2. ✅ Train models cho tất cả 5 symbols
3. ✅ Verify tất cả model files
4. ✅ Test symbols configuration
5. ✅ Hiển thị hướng dẫn testing

---

## Hướng Dẫn Sử Dụng Nhanh

### Bước 1: Test Symbols Configuration

```bash
.\crypto-venv\Scripts\Activate.ps1
python config\symbols_config.py
```

**Kết quả mong đợi:**
```
🧪 Testing Symbols Configuration...

Input: BTC
  ✅ Normalized: BTC/USDT
  📊 Binance Format: BTCUSDT
  💎 Display: Bitcoin
  🪙 CoinGecko: bitcoin
  ✓ Valid: True

📋 All supported symbols: ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT', 'BNB/USDT']
```

### Bước 2: Train Models (Chọn 1 trong 3)

#### Option A: Tự động (Khuyến nghị) ⭐
```bash
python setup_multi_symbol.py
```

#### Option B: Train tất cả manual
```bash
python app\ml\train_models.py --all
```

#### Option C: Train từng coin
```bash
# Train từng coin riêng lẻ
python app\ml\train_models.py --symbol BTC
python app\ml\train_models.py --symbol ETH
python app\ml\train_models.py --symbol XRP
python app\ml\train_models.py --symbol SOL
python app\ml\train_models.py --symbol BNB
```

**Thời gian dự kiến:**
- 1 symbol: ~1-2 phút
- Tất cả 5 symbols: ~5-10 phút

### Bước 3: Kiểm Tra Models

```bash
# Kiểm tra files đã được tạo
ls app\ml\models\*_latest.joblib

# Kết quả mong đợi (15 files):
# random_forest_BTC_latest.joblib
# svm_BTC_latest.joblib
# logistic_regression_BTC_latest.joblib
# ... (tương tự cho ETH, XRP, SOL, BNB)
```

### Bước 4: Test Hệ Thống Hoàn Chỉnh

Mở **3 terminals** và chạy đồng thời:

#### Terminal 1: ML Consumer
```powershell
.\crypto-venv\Scripts\Activate.ps1
python app\consumers\ml_predictor.py
```

#### Terminal 2: Multi-Symbol Producer
```powershell
.\crypto-venv\Scripts\Activate.ps1

# Option A: Tất cả symbols (song song - nhanh)
python app\producers\multi_symbol_producer.py --all --parallel

# Option B: Chọn một vài symbols
python app\producers\multi_symbol_producer.py --symbols BTC ETH SOL

# Option C: Chỉ 1 symbol
python app\producers\multi_symbol_producer.py --symbols BTC
```

#### Terminal 3: Debug ML Signals
```powershell
.\crypto-venv\Scripts\Activate.ps1
python test_phase3_debug_ml_signals.py
```

---

## Ví Dụ Output

### Producer (Multi-Symbol)
```
🚀 Multi-Symbol Producer initialized
📊 Tracking 5 symbols: BTC, ETH, XRP, SOL, BNB
⏰ Timeframe: 1m
🚀 Starting parallel data collection...
============================================================
📡 [BTC] Price: $68,234.50 | Vol: 1,234,567
📡 [ETH] Price: $3,456.78 | Vol: 5,678,901
📡 [XRP] Price: $0.5234 | Vol: 98,765,432
📡 [SOL] Price: $123.45 | Vol: 2,345,678
📡 [BNB] Price: $567.89 | Vol: 876,543
✅ Round complete: 5/5 successful
⏳ Waiting 5s before next round...
```

### ML Consumer (Multi-Symbol)
```
🚀 ML Predictor Service Started...
📡 Consuming from: crypto.market_data
📤 Producing to: crypto.ml_signals
🔄 Minimum data required: 52 candles
------------------------------------------------------------
✅ Loaded models for BTC
⏳ [BTC] Accumulating data: 1/52
⏳ [BTC] Accumulating data: 2/52
...
⏳ [BTC] Accumulating data: 52/52
🟢 [BTC:1] BUY | Price: $68,234.50 | Conf: 0.72 | RF:1 SVM:1

✅ Loaded models for ETH
⏳ [ETH] Accumulating data: 1/52
...
🔴 [ETH:1] SELL | Price: $3,456.78 | Conf: 0.35 | RF:0 SVM:0

✅ Loaded models for XRP
⏳ [XRP] Accumulating data: 1/52
...
⚪ [XRP:1] NEUTRAL | Price: $0.5234 | Conf: 0.52 | RF:1 SVM:0
```

### Statistics (Khi dừng Consumer)
```
📊 Session statistics:
============================================================

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

XRP:
   Total predictions: 44
   BUY signals: 11
   SELL signals: 7
   NEUTRAL: 26

SOL:
   Total predictions: 42
   BUY signals: 9
   SELL signals: 10
   NEUTRAL: 23

BNB:
   Total predictions: 41
   BUY signals: 8
   SELL signals: 11
   NEUTRAL: 22

============================================================
🛑 ML Predictor Service Stopped
```

---

## API Reference

### Symbols Configuration

```python
from config.symbols_config import *

# Danh sách tất cả symbols được hỗ trợ
SUPPORTED_SYMBOLS  # ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT', 'BNB/USDT']

# Normalize bất kỳ input nào về CCXT format
normalize_symbol('btc')      # → 'BTC/USDT'
normalize_symbol('ETHUSDT')  # → 'ETH/USDT'
normalize_symbol('xrp')      # → 'XRP/USDT'

# Lấy base symbol
get_base_symbol('BTC/USDT')   # → 'BTC'
get_base_symbol('ETHUSDT')    # → 'ETH'

# Convert sang Binance format
get_binance_format('BTC/USDT')  # → 'BTCUSDT'

# Kiểm tra validity
is_valid_symbol('BTC')    # → True
is_valid_symbol('DOGE')   # → False (not supported)

# Lấy tất cả thông tin
info = get_symbol_info('ETH')
# {
#     'base': 'ETH',
#     'ccxt_format': 'ETH/USDT',
#     'binance_format': 'ETHUSDT',
#     'display_name': 'Ethereum',
#     'coingecko_id': 'ethereum'
# }
```

---

## Troubleshooting

### Lỗi: "Models not found for XXX"
**Nguyên nhân:** Chưa train models cho symbol đó.

**Giải pháp:**
```bash
python app\ml\train_models.py --symbol XXX
```

### Lỗi: Import Error - config.symbols_config
**Nguyên nhân:** Path chưa được thêm vào sys.path.

**Giải pháp:** Đảm bảo code có:
```python
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Producer gửi data nhưng Consumer không nhận
**Kiểm tra:**
1. Kafka đang chạy: `docker ps`
2. Topic tồn tại: `docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092`
3. Consumer group ID khác nhau giữa các lần chạy

### Models train lâu quá
**Bình thường:**
- 1 symbol: 1-2 phút
- 5 symbols: 5-10 phút

**Nếu quá lâu (>15 phút):**
- Kiểm tra kết nối mạng (Binance API)
- Giảm số lượng data: `limit=500` thay vì `limit=1000`

---

## Tích Hợp Với Discord Bot

Để tích hợp với Discord Bot (`app/bot.py`), cập nhật các commands:

```python
from config.symbols_config import normalize_symbol, get_base_symbol, is_valid_symbol

@bot.command(name='dudoan')
async def dudoan(ctx, symbol: str = "BTC"):
    """Dự đoán giá cho bất kỳ symbol nào."""
    
    # Validate symbol
    if not is_valid_symbol(symbol):
        await ctx.send(f"❌ Symbol '{symbol}' không được hỗ trợ. Chỉ hỗ trợ: BTC, ETH, XRP, SOL, BNB")
        return
    
    # Normalize
    normalized = normalize_symbol(symbol)
    base = get_base_symbol(symbol)
    
    # Fetch prediction từ ML Consumer hoặc model file
    # ... (code hiện tại)
```

**Commands mới:**
```
!dudoan BTC    → Dự đoán Bitcoin
!dudoan ETH    → Dự đoán Ethereum
!dudoan XRP    → Dự đoán Ripple
!dudoan SOL    → Dự đoán Solana
!dudoan BNB    → Dự đoán Binance Coin

!price BTC     → Giá Bitcoin hiện tại
!price ETH     → Giá Ethereum hiện tại
```

---

## Tối Ưu Hóa

### 1. Training Performance
```bash
# Train parallel với multiprocessing (tự implement nếu cần)
# Hiện tại train sequential để tránh conflict

# Giảm data size nếu cần nhanh hơn
python app\ml\train_models.py --all  # limit=1000 (mặc định)
# Hoặc edit code: limit=500
```

### 2. Producer Performance
```bash
# Luôn dùng --parallel cho nhiều symbols
python app\producers\multi_symbol_producer.py --all --parallel

# Tăng workers nếu cần (edit code)
ThreadPoolExecutor(max_workers=10)  # Default = số symbols
```

### 3. Consumer Memory
ML Consumer load tất cả models vào RAM. Nếu thiếu RAM:
- Chỉ train symbols bạn cần
- Hoặc modify code để lazy-load models

---

## Roadmap Tương Lai

### Phase 4: Backtrader Integration
- [ ] Decision Engine cho từng symbol riêng
- [ ] Risk management per symbol
- [ ] Portfolio balancing

### Phase 5: Streamlit Dashboard
- [ ] Multi-chart view (5 symbols)
- [ ] Real-time predictions display
- [ ] Performance comparison between symbols

### Phase 6: Advanced Features
- [ ] Symbol correlation analysis
- [ ] Dynamic symbol selection based on volatility
- [ ] Auto-retraining schedule per symbol

---

## Kết Luận

Hệ thống giờ đây hỗ trợ đầy đủ **5 đồng coin phổ biến** với khả năng:
- ✅ Training riêng biệt cho từng symbol
- ✅ Real-time prediction cho nhiều symbols đồng thời
- ✅ Quản lý buffer riêng để tránh data mixing
- ✅ Statistics chi tiết per symbol
- ✅ Dễ dàng mở rộng thêm symbols mới

**Các symbols được hỗ trợ:**
- 🟠 **BTC** - Bitcoin (Coin lớn nhất)
- 🔵 **ETH** - Ethereum (Smart contracts)
- ⚫ **XRP** - Ripple (Thanh toán quốc tế)
- 🟣 **SOL** - Solana (High performance blockchain)
- 🟡 **BNB** - Binance Coin (Exchange token)

Để bắt đầu ngay, chạy:
```bash
python setup_multi_symbol.py
```
