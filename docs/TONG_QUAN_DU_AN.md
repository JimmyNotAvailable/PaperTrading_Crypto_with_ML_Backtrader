# 📊 TỔNG QUAN DỰ ÁN - CRYPTO ML TRADING BOT

## 🎯 MỤC TIÊU THIẾT KẾ BAN ĐẦU

**Chatbot Discord dự đoán giá Cryptocurrency sử dụng Machine Learning**

### Chức năng chính:
1. **Discord Bot Interface**: Người dùng tương tác qua Discord commands
2. **Machine Learning Models**: Dự đoán giá crypto (BTC, ETH, v.v.)
3. **Real-time Data**: Thu thập dữ liệu từ Binance API
4. **Multi-model Support**: Linear Regression, KNN, K-Means

---

## 🏗️ KIẾN TRÚC HỆ THỐNG

```
┌─────────────────┐
│  Discord User   │
└────────┬────────┘
         │ !dudoan BTC
         ▼
┌─────────────────────────────────┐
│    Discord Bot (app/bot.py)     │
│  - Commands: !dudoan, !price    │
│  - Token: BOT_TOKEN/token.txt   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  ML Prediction Engine           │
│  (data/models_production/)      │
│  - quick_loader.py              │
│  - crypto_models_production.pkl │
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ Binance │ │ ML Models    │
│   API   │ │ - Linear Reg │
│         │ │ - KNN        │
│         │ │ - K-Means    │
└─────────┘ └──────────────┘
```

---

## 📁 CẤU TRÚC THƯ MỤC

> Cây thư mục dưới đây được tạo tự động để đảm bảo tính chính xác.
> **Lệnh (PowerShell):** `Get-ChildItem -Depth 3 -Recurse -Exclude "crypto-venv",".git",".idea","__pycache__","*.joblib" | tree`

```
app/ml/
├── algorithms/          # Các thuật toán ML
│   ├── linear_regression.py
│   ├── knn_classifier.py
│   ├── kmeans_clustering.py
├── core.py             # Base classes, utilities
├── data_prep.py        # Data preprocessing
├── train_all.py        # Training orchestrator
└── model_registry.py   # Model versioning
```

### 3. **app/data_collector/** - Thu thập dữ liệu
```
app/data_collector/
├── realtime_collector.py      # Binance API
└── enhanced_realtime_collector.py
```

### 4. **data/models_production/** - Production Models
```
data/models_production/
├── quick_loader.py                    # Model loader
└── crypto_models_production.pkl       # Trained models
```

### 5. **app/services/** - Business Logic
```
app/services/
├── trainer.py          # Auto training service
├── crypto_api_service.py
└── store.py           # Data storage
```

---

## 🤖 DISCORD BOT COMMANDS

### Commands chính:

| Command | Mô tả | Ví dụ |
|---------|-------|-------|
| `!ping` | Kiểm tra bot online | `!ping` |
| `!help` | Hiển thị trợ giúp | `!help` |
| `!dudoan [SYMBOL]` | Dự đoán giá 24h | `!dudoan BTC` |
| `!price [SYMBOL]` / `!gia` | Giá hiện tại | `!price ETH` |
| `!movers` | Top gainers/losers | `!movers` |
| `!chart [SYMBOL]` | Xem biểu đồ | `!chart BTC` |
| `!dudoan_json {...}` | Dự đoán với JSON custom | `!dudoan_json {"close":45000,...}` |

### Ví dụ output `!dudoan BTC`:
```
🎯 Dự đoán giá BTC
📊 Giá hiện tại: $68,000.00
🎯 Giá dự đoán: $69,500.00
📈 Thay đổi dự kiến: +2.21%
🇻🇳 Giá VND hiện tại: 1,632,000,000 đ
💴 Giá VND dự đoán: 1,668,000,000 đ
🔒 Độ tin cậy: Medium
🧠 Model: linear_regression_price R²=0.892, MAE=245.32
📈 Xu hướng: Tăng
```

---

## 🔐 BẢO MẬT TOKEN

### ⚠️ VẤN ĐỀ HIỆN TẠI:
- Token lưu trong `token.txt` (đã bị leak lên GitHub)
- File `.gitignore` đã có `token.txt` nhưng file đã commit trước đó

### ✅ GIẢI PHÁP KHUYẾN NGHỊ:

#### 1. **Thu hồi token cũ ngay lập tức**
   - Vào [Discord Developer Portal](https://discord.com/developers/applications)
   - Chọn application của bạn → Bot → **Reset Token**

#### 2. **Xóa token khỏi Git history**
```powershell
# Cài đặt git-filter-repo
pip install git-filter-repo

# Xóa token.txt khỏi toàn bộ lịch sử
git filter-repo --path token.txt --invert-paths

# Force push (cẩn thận!)
git push origin --force --all
```

#### 3. **Sử dụng biến môi trường**

**Tạo file `.env`:**
```env
# .env (đã có trong .gitignore)
DISCORD_BOT_TOKEN=your-new-token-here
MONGODB_URI=mongodb://localhost:27017/crypto
FX_USD_VND=24000
```

**Cài đặt python-dotenv:**
```powershell
pip install python-dotenv
```

**Cập nhật `app/bot.py`:**
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file

def read_bot_token() -> Optional[str]:
    # Ưu tiên environment variable
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if token:
        return token.strip()
    
    # Fallback to token.txt (chỉ cho local dev)
    # ... existing code ...
```

#### 4. **Setup cho production (GitHub Actions, Docker)**

**GitHub Secrets:**
- Settings → Secrets and variables → Actions
- Thêm secret: `DISCORD_BOT_TOKEN`

**Docker Compose:**
```yaml
services:
  bot:
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
    # Không mount token.txt
```

#### 5. **Best Practices**
```powershell
# Kiểm tra không commit secrets
git diff --staged

# Pre-commit hook (tùy chọn)
pip install pre-commit detect-secrets
```

---

## 🔧 MACHINE LEARNING PIPELINE

### Workflow:

```
1. Thu thập dữ liệu
   ↓
   app/data_collector/realtime_collector.py
   - Binance API: OHLCV data
   - Feature engineering: MA, volatility, returns
   ↓
2. Lưu trữ
   ↓
   data/realtime/
   data/realtime_production/
   ↓
3. Training
   ↓
   app/ml/train_all.py
   - Linear Regression (price prediction)
   - KNN (classification/regression)
   - K-Means (clustering)
   ↓
4. Model Registry
   ↓
   app/ml/model_registry.py
   - Version tracking
   - Metadata: metrics, timestamp
   ↓
5. Production Deployment
   ↓
   data/models_production/quick_loader.py
   - Load: crypto_models_production.pkl
   - Predict: price, trend, confidence
   ↓
6. Discord Bot sử dụng
   ↓
   app/bot.py → try_predict()
```

### Features được sử dụng:
- `open`, `high`, `low`, `close`, `volume`
- `ma_10`, `ma_50` (moving averages)
- `volatility`, `returns`
- `hour` (time-based)

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN

### 1. Setup môi trường
```powershell
# Clone repo
git clone <your-repo>
cd crypto-ml-trading-project

# Tạo virtual environment
python -m venv crypto-venv
.\crypto-venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Cấu hình
```powershell
# Copy .env.example
copy .env.example .env

# Chỉnh sửa .env
# DISCORD_BOT_TOKEN=your-discord-bot-token
# MONGODB_URI=mongodb://localhost:27017/crypto
```

### 3. Thu thập dữ liệu (tùy chọn)
```powershell
python app/data_collector/realtime_collector.py
```

### 4. Training models (nếu chưa có)
```powershell
python app/ml/train_all.py
```

### 5. Chạy Discord Bot
```powershell
python app/bot.py
```

### 6. Test trên Discord
```
!ping
!dudoan BTC
!price ETH
!movers
```

---

## 📊 MODELS ĐÃ TRAIN

### 1. Linear Regression (Price Prediction)
- **File**: `linreg_price.joblib`
- **Target**: Dự đoán giá `close`
- **Metrics**: R² ~0.85-0.90, MAE ~$200-500

### 2. Linear Regression (Price Change)
- **File**: `linreg_price_change.joblib`
- **Target**: Thay đổi giá %
- **Metrics**: R² ~0.75, MAE ~1.5%

### 3. KNN Classifier
- **File**: `knn_crypto_classifier.joblib`
- **Target**: Trend classification (Up/Down/Sideways)
- **Metrics**: Accuracy ~70-80%

### 4. KNN Regressor
- **File**: `knn_crypto_regressor.joblib`
- **Target**: Price prediction
- **Metrics**: R² ~0.80

### 5. K-Means Clustering
- **File**: `kmeans_crypto.joblib`
- **Target**: Market regime clustering
- **Clusters**: 3-8 clusters

---

## ⚡ TÍNH NĂNG NỔI BẬT

### 1. **Anti-Duplicate System**
- Cross-instance deduplication (file locks)
- Reaction-based claiming (🤖)
- Cooldown mechanism (3-5s per user)
- Prevents multiple bot instances responding

### 2. **Real-time Price Integration**
- Binance API integration
- Fallback to stub data nếu API fail
- USD/VND conversion

### 3. **Production-Ready Model Loading**
- Hot-reload on model file change
- Pickle/Joblib support
- Graceful fallback nếu model không tồn tại

### 4. **Vietnamese Language Support**
- Commands tiếng Việt: `!gia`, `!dudoan`
- Output format tiếng Việt
- VND currency display

---

## 🐛 VẤN ĐỀ CẦN KHẮC PHỤC

### 1. **Token Security** ⚠️ CRITICAL
- [ ] Revoke token cũ đã leak
- [ ] Migrate sang environment variables
- [ ] Xóa `token.txt` khỏi Git history
- [ ] Setup GitHub Secrets cho CI/CD

### 2. **Model Training Data**
- [ ] Dữ liệu training cũ (mean price ~$6k vs current BTC ~$68k)
- [ ] Cần re-train với dữ liệu mới
- [ ] Feature scaling issues

### 3. **Error Handling**
- [ ] Better error messages cho user
- [ ] Logging system (hiện tại chỉ print)
- [ ] API rate limiting handling

### 4. **Testing**
- [ ] Unit tests cho ML models
- [ ] Integration tests cho bot commands
- [ ] Mock data cho testing

---

## 🎯 KẾ HOẠCH PHÁT TRIỂN

### Phase 1: Security & Stability ✅
- [x] Fix token leak issue
- [x] Implement environment variables
- [x] Anti-duplicate system
- [ ] Comprehensive logging

### Phase 2: ML Improvements 🔄
- [ ] Re-train models với dữ liệu mới (2024-2025)
- [ ] Add more features (sentiment, volume profile)
- [ ] Implement ensemble models
- [ ] Backtesting framework

### Phase 3: Features 📅
- [ ] Portfolio tracking
- [ ] Price alerts
- [ ] Technical analysis charts
- [ ] Multi-timeframe predictions (1h, 4h, 1d)
- [ ] Sentiment analysis từ news/Twitter

### Phase 4: Infrastructure 🏗️
- [ ] MongoDB integration (đã có code, chưa active)
- [ ] Redis caching
- [ ] Containerization (Docker)
- [ ] Cloud deployment (AWS/Azure/Heroku)

---

## 📚 TÀI LIỆU LIÊN QUAN

- **README.md**: Hướng dẫn cài đặt
- **docs/BOT_COMMANDS.md**: Chi tiết commands
- **docs/PRODUCTION_README.md**: Production deployment
- **docs/ARCHITECTURE.md**: System architecture
- **docs/ML_ARCHITECTURE_ANALYSIS.md**: ML design

---

## 🤝 ĐÓNG GÓP

### Quy tắc:
1. **KHÔNG BAO GIỜ** commit secrets (tokens, passwords)
2. Luôn test local trước khi push
3. Viết code comments tiếng Việt/English
4. Update docs khi thêm features

### Git Workflow:
```powershell
# Tạo branch mới
git checkout -b feature/ten-tinh-nang

# Commit changes
git add .
git commit -m "feat: mô tả ngắn gọn"

# Push
git push origin feature/ten-tinh-nang

# Tạo Pull Request trên GitHub
```

---

## 📞 HỖ TRỢ

- **Issues**: GitHub Issues
- **Discord**: [Server link nếu có]
- **Email**: [Email support nếu có]

---

**Lưu ý**: Dự án này chỉ mang tính chất học tập và demo. Không nên sử dụng để đưa ra quyết định đầu tư thật sự. Cryptocurrency rất biến động và rủi ro cao.

---

*Tài liệu tạo ngày: 2025-01-14*  
*Phiên bản: 1.0*
