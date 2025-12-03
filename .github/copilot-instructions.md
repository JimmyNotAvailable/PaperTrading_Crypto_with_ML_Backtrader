# Crypto ML Trading Project - AI Coding Agent Instructions

## Project Overview

**Production-ready event-driven cryptocurrency ML trading system** with Kafka message bus, ensemble ML predictions (Random Forest, SVM, Logistic Regression), Backtrader execution engine, and multi-interface access (Discord bot + Streamlit dashboard). Supports 5 major crypto pairs (BTC, ETH, XRP, SOL, BNB) with Vietnamese language UI.

**Current Status**: Phase 4 completed (Nov 2024) - Kafka pipeline operational, Backtrader decision engine integrated, SQLite trade logging active. Phase 5 (Dashboard) in development.

## Architecture (Fully Implemented)

### Event-Driven Pipeline
```
Binance API (CCXT) → Kafka Producer → crypto.market_data topic
                           ↓
                    ML Consumer (52-candle buffer)
                    ├─ Random Forest (primary)
                    ├─ SVM Classifier
                    └─ Logistic Regression
                           ↓
                    crypto.ml_signals topic
                           ↓
                Backtrader Decision Engine
                (Risk mgmt: 2% SL, 5% TP)
                           ↓
                    SQLite Logs + crypto.orders topic
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓                                      ↓
Discord Bot (!dudoan, !price)      Streamlit Dashboard (planned)
```

**Kafka Topics** (see `docs/KAFKA_TOPICS_SCHEMA.md`):
- `crypto.market_data`: OHLCV + volume from Binance (1min candles)
- `crypto.ml_signals`: Ensemble predictions with confidence scores (BUY/SELL/NEUTRAL)
- `crypto.orders`: Backtrader execution logs with entry/SL/TP prices

## Critical Developer Workflows

### 1. Environment Setup (First Time)
```powershell
# Create virtual environment
python -m venv crypto-venv
.\crypto-venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file (NEVER commit this)
# Required vars: DISCORD_BOT_TOKEN, KAFKA_BOOTSTRAP_SERVERS
```

**Token Security** (see `docs/HUONG_DAN_BAO_MAT_TOKEN.md`):
- Priority: `DISCORD_BOT_TOKEN` env var → `BOT_TOKEN` → `token.txt` (insecure fallback)
- `app/bot.py::read_bot_token()` implements this resolution logic

### 2. Multi-Symbol ML Training (PRODUCTION PATH)
```powershell
# Train all 5 symbols with ensemble models (RF, SVM, LR)
python setup_multi_symbol.py
# → Outputs: app/ml/models/improved_{model}_{SYMBOL}_latest.joblib
# → 15 models total (3 algos × 5 symbols)
# → Training uses TimeSeriesSplit to prevent data leakage

# Single symbol training
python app\ml\train_models.py --symbol BTC
```

**Critical**: Models expect **52+ candles** for feature calculation (SMA_50 + buffer). See `app/consumers/ml_predictor.py::min_required_data`.

### 3. Running the Kafka Pipeline
```powershell
# Terminal 1: Start Kafka infrastructure
docker-compose up -d
# Wait for http://localhost:8080 (Kafka UI) to show cluster online

# Terminal 2: Start Producer (5 symbols, 60s interval)
python app\producers\binance_producer.py

# Terminal 3: Start ML Consumer (ensemble predictions)
python app\consumers\ml_predictor.py

# Terminal 4: Start Backtrader Decision Engine
python app\consumers\backtrader_decision_engine.py

# Terminal 5 (optional): Discord Bot interface
python app\bot.py
```

**Kafka Listeners** (critical for local dev):
- `localhost:9092` - Python code outside Docker
- `kafka:29092` - Services inside Docker network

### 4. Discord Bot Commands (Vietnamese UI)
```
!ping           - Health check
!dudoan BTC     - Full ML prediction with model confidence
!price ETH      - Current price + quick prediction
!gia SOL        - Vietnamese alias for !price
!movers         - Top gainers/losers 24h
```

Bot loads models from `app/ml/models/improved_random_forest_{SYMBOL}_latest.joblib` (fallback to legacy `data/models_production/quick_loader.py`).

## Project-Specific Conventions

### 1. Symbol Handling (Multi-Symbol System)
**Centralized config**: `config/symbols_config.py`
```python
# Always use these utilities - NEVER hardcode symbols
from config.symbols_config import normalize_symbol, get_base_symbol, is_valid_symbol

# Supported: BTC, ETH, XRP, SOL, BNB
symbol = normalize_symbol('btc')      # → 'BTC/USDT' (CCXT format)
base = get_base_symbol('ETHUSDT')     # → 'ETH'
binance_fmt = get_binance_format('BTC/USDT')  # → 'BTCUSDT'
```

**Model naming convention**: `improved_{algorithm}_{SYMBOL}_latest.joblib`  
Example: `improved_random_forest_BTC_latest.joblib`

### 2. ML Model Architecture (BaseModel Pattern)
All models inherit from `app/ml/algorithms/base.py::BaseModel`:
```python
class MyModel(BaseModel):
    def __init__(self):
        super().__init__(model_name="MyModel", model_type="regression")
    
    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict[str, Any]:
        # CRITICAL: Use TimeSeriesSplit for validation
        from sklearn.model_selection import TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=5)
        # ... training logic
        return {'r2': 0.85, 'mae': 50.2}  # Standardized metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        # Must complete <500ms for real-time trading
        return self.model.predict(X)
    
    def save_model(self, name: str):
        # Auto-saves to app/ml/models/{name}.joblib + _metadata.json
```

**Why TimeSeriesSplit?**: Prevents data leakage by respecting temporal order (train on past, validate on future). See `ToturialUpgrade.md` - critical for financial data.

### 3. Feature Engineering (52-Candle Buffer)
From `app/consumers/ml_predictor.py`:
```python
# REQUIRED: 52 candles minimum (50 for SMA_50 + 2 buffer)
self.min_required_data = 52

# Standard features (all models trained on these)
features = [
    'open', 'high', 'low', 'close', 'volume',
    'SMA_10', 'SMA_20', 'SMA_50',  # Simple Moving Averages
    'RSI_14',                        # Relative Strength Index
    'MACD', 'MACD_signal',          # MACD indicators
    'BB_upper', 'BB_lower',         # Bollinger Bands
    'volume_sma_ratio'              # Volume/SMA ratio
]
```

**Critical**: Feature schema must match training data exactly. Use `app/ml/feature_engineering.py::calculate_features()`.

### 4. Kafka Message Formats
**Producer** (`app/producers/binance_producer.py`):
```json
{
  "symbol": "BTC/USDT",
  "timestamp": "2024-11-30T10:00:00Z",
  "open": 67800.0, "high": 68000.0, "low": 67500.0, "close": 67900.0,
  "volume": 1234.5
}
```

**ML Signals** (`app/consumers/ml_predictor.py`):
```json
{
  "symbol": "BTC/USDT",
  "timestamp": "2024-11-30T10:00:00Z",
  "ensemble_signal": "BUY",           // BUY/SELL/NEUTRAL
  "confidence": 0.78,                 // Weighted average 0-1
  "models": {
    "random_forest": {"signal": "BUY", "confidence": 0.85},
    "svm": {"signal": "BUY", "confidence": 0.72},
    "logistic_regression": {"signal": "NEUTRAL", "confidence": 0.55}
  }
}
```

**Orders** (Backtrader → Kafka):
```json
{
  "symbol": "BTC/USDT",
  "action": "BUY",  // or SELL
  "price": 67900.0,
  "amount": 0.147,
  "entry_price": 67900.0,
  "stop_loss": 66542.0,    // -2%
  "take_profit": 71295.0,  // +5%
  "ml_confidence": 0.78
}
```

### 5. Vietnamese Logging Standard (NO EMOJIS in Production)
Phase 4 migration removed all emojis for professionalism. Use these tags:
```python
logger.info("[KHOI TAO] Khởi tạo Backtrader engine")
logger.info("[TIN HIEU ML] Nhận tín hiệu BUY với độ tin cậy 78.5%")
logger.info("[QUYET DINH MUA] Vào lệnh BTC/USDT @ $67,900.00")
logger.info("[CAT LO] Dừng lỗ kích hoạt tại $66,542.00")
logger.error("[LOI] Kết nối Kafka thất bại")
```

User-facing (Discord embeds) can use emojis: `📊 Giá hiện tại`, `🇻🇳 Giá VND`

## Integration Points

### Binance API (CCXT)
**Exchange**: `app/producers/binance_producer.py`
```python
import ccxt
exchange = ccxt.binance({'enableRateLimit': True})
# Fetch OHLCV: exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=100)
```
**Supported symbols**: 5 pairs from `config/symbols_config.py` (BTC, ETH, XRP, SOL, BNB)  
**Rate limits**: `enableRateLimit=True` handles throttling automatically

### Kafka Infrastructure (Docker Compose)
```yaml
# Critical listeners for local dev + Docker network
KAFKA_ADVERTISED_LISTENERS: 
  PLAINTEXT://kafka:29092         # Docker internal
  PLAINTEXT_HOST://localhost:9092 # Local Python
```

**Python connection** (outside Docker):
```python
from confluent_kafka import Producer
p = Producer({'bootstrap.servers': 'localhost:9092'})
```

**Kafka UI**: http://localhost:8080 (admin interface)

### Backtrader Decision Engine
**File**: `app/consumers/backtrader_decision_engine.py`  
**Strategy**: `app/services/backtrader_broker.py::MLKafkaStrategy`

**Risk Management** (hardcoded in Phase 4):
- Stop Loss: 2% below entry
- Take Profit: 5% above entry
- Min Confidence: 60% (filters weak ML signals)
- Commission: 0.1% per trade

**Trade Logging**: SQLite database at `data/trading_logs.db` with 3 tables:
- `trades`: Execution history (price, amount, PnL, ML confidence)
- `equity`: Portfolio value over time
- `positions`: Open positions with SL/TP levels

### Model Registry (Metadata Tracking)
**File**: `app/ml/model_registry.py`
```python
from app.ml.model_registry import model_registry

# Auto-registers when model is saved
model_registry.register_model(
    name="random_forest_BTC",
    version="1.0.0",
    metrics={'r2': 0.85, 'mae': 50.2},
    model_path="app/ml/models/improved_random_forest_BTC_latest.joblib"
)

# Query best model
best = model_registry.get_best_model(model_name="random_forest")
```

## External Dependencies

### Core Libraries (requirements.txt)
- `confluent-kafka==2.3.0` - High-performance Kafka client (C-based)
- `ccxt>=4.2.0` - Unified crypto exchange API (Binance)
- `backtrader>=1.9.78` - Trading strategy backtesting framework
- `scikit-learn>=1.3.0` - ML algorithms
- `discord.py` - Discord bot framework
- `pandas_ta>=0.4.67` - Technical indicators library (RSI, MACD, Bollinger Bands)
- `streamlit==1.28.0` - Real-time dashboard (Phase 5)
- `joblib>=1.3.2` - Model serialization

### Docker Services (docker-compose.yml)
- `confluentinc/cp-kafka:7.4.0` - Kafka broker
- `confluentinc/cp-zookeeper:7.4.0` - Kafka coordinator
- `provectuslabs/kafka-ui:latest` - Web admin interface
- `mongo:latest` - Legacy database (partial migration to SQLite)

## Code Quality Standards

### Vietnamese + English Hybrid Naming
- **User-facing**: Vietnamese (`!dudoan BTC`, `Giá VND`, log tags `[KHOI TAO]`)
- **Code/variables**: English (`LinearRegressionModel`, `price_prediction`, `calculate_features`)
- **Documentation**: Both languages (`docs/TONG_QUAN_DU_AN.md` + English READMEs)

### Error Handling Pattern
```python
try:
    # Kafka consume or ML prediction
    result = model.predict(features)
except Exception as e:
    logger.error(f"[LOI] {type(e).__name__}: {str(e)}")
    return fallback_value  # Always provide graceful degradation
```

### Path Handling (Cross-Platform)
```python
from pathlib import Path

# Always use Path for Windows/Linux compatibility
project_root = Path(__file__).parent.parent.parent
models_dir = project_root / "app" / "ml" / "models"
db_path = project_root / "data" / "trading_logs.db"
```

### Logging Format (Production)
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NO emojis in production code (removed in Phase 4)
logger.info("[TIN HIEU ML] BTC: BUY với độ tin cậy 85.3%")
logger.warning("[BO QUA] Độ tin cậy thấp: 45.2% < 60%")
logger.error("[LOI] Kafka connection timeout sau 30s")
```

## Testing and Validation

### Unit Testing
```powershell
# Run test suite
pytest tests/

# Test specific module
pytest tests/test_ml_predictor.py -v
```

### Integration Testing (Phase 4 Demo)
```powershell
# Full pipeline test with mock data
python demo_phase4.py

# Check trade logs in SQLite
python check_db.py
```

**Expected output**: 
- Trades logged with ML confidence scores
- Position tracking (entry, SL, TP prices)
- Session summary with total trades count

### Model Evaluation
```powershell
# Generate performance reports for all models
python app\ml\evaluate.py
# → Creates reports in reports/ with metrics, feature importance
```

### Bot Commands Testing
```discord
!ping           # Must respond "Pong!"
!dudoan BTC     # Should show 3 model predictions (RF, SVM, LR)
!price ETH      # Current price + quick ensemble prediction
```

## Known Limitations and Gotchas

### Performance Constraints
- **ML Prediction Latency**: Must complete `model.predict()` <500ms or trading signals become stale
- **Buffer Requirements**: Need 52+ candles before predictions start (cold start delay ~52 minutes)
- **Kafka Single Node**: `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1` - not production-ready for critical systems

### Data Leakage Prevention (CRITICAL)
```python
# ❌ WRONG - Uses train_test_split (leaks future data)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# ✅ CORRECT - TimeSeriesSplit respects temporal order
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
```

**Why critical**: Financial data has temporal dependencies. Using future data to predict past inflates metrics artificially.

### Symbol Format Consistency
```python
# ❌ WRONG - Hardcoded formats cause bugs
if symbol == 'BTCUSDT':  # Breaks on 'BTC', 'btc', 'BTC/USDT'

# ✅ CORRECT - Always normalize first
from config.symbols_config import normalize_symbol
normalized = normalize_symbol(user_input)  # Handles all formats
if normalized == 'BTC/USDT':
```

### Kafka Connection Issues (Common Debugging)
```powershell
# Check if Kafka is accessible
docker ps | Select-String kafka  # Must show 'Up' status

# Test Kafka UI
Start-Process http://localhost:8080

# Verify Python can connect
python -c "from confluent_kafka import Producer; p=Producer({'bootstrap.servers':'localhost:9092'}); print('✅ Connected')"
```

**Common error**: `Failed to resolve 'kafka:29092'` → You're using Docker-internal address from outside Docker. Use `localhost:9092` instead.

## Quick Reference

### Environment Activation
```powershell
# Windows PowerShell
.\crypto-venv\Scripts\Activate.ps1

# Verify environment
python -c "import sys; print(sys.prefix)"
# Should show path to crypto-venv, not system Python
```

### File Locations (Frequently Referenced)
```
Token config:             .env (DISCORD_BOT_TOKEN)
Trained models:           app/ml/models/improved_{algo}_{SYMBOL}_latest.joblib
Model metadata:           app/ml/models/improved_{algo}_{SYMBOL}_latest_metadata.json
Trade logs:               data/trading_logs.db
Kafka config:             docker-compose.yml
Symbol definitions:       config/symbols_config.py
Upgrade roadmap:          Step_1.md, ToturialUpgrade.md, PHASE4_FINAL_REPORT.md
Architecture docs:        docs/ARCHITECTURE.md, docs/KAFKA_TOPICS_SCHEMA.md
```

### Entry Points by Use Case
```powershell
# ML Training
python setup_multi_symbol.py           # Train all symbols (recommended)
python app\ml\train_models.py --symbol BTC  # Train single symbol

# Kafka Pipeline
docker-compose up -d                   # Start infrastructure
python app\producers\binance_producer.py    # Market data
python app\consumers\ml_predictor.py        # ML predictions
python app\consumers\backtrader_decision_engine.py  # Trading logic

# User Interfaces
python app\bot.py                      # Discord bot
python demo_phase4.py                  # Phase 4 integration demo
python monitor_bot.py                  # Bot monitoring script

# Debugging/Testing
python check_db.py                     # Inspect SQLite trade logs
python test_phase4_integration.py      # End-to-end test
```

### Docker Quick Commands
```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f kafka           # Kafka broker logs
docker-compose logs -f kafka-ui        # UI logs

# Stop all services
docker-compose down

# Clean restart (loses data)
docker-compose down -v; docker-compose up -d
```

---

**For Vietnamese documentation**: See `docs/TONG_QUAN_DU_AN.md`, `docs/QUICK_START.md`, `MULTI_SYMBOL_QUICKSTART.md`
