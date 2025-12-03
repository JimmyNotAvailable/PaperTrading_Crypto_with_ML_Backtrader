# Crypto ML Trading Project - AI Coding Agent Instructions

## Project Overview

**Event-driven cryptocurrency ML trading system** combining Discord bot interface, real-time data collection, ML predictions (Linear Regression, KNN, K-Means), and planned Kafka integration for microservices architecture. Vietnamese language support throughout.

**Critical Context**: Currently transitioning from monolithic architecture to Kafka-based event-driven microservices following upgrade plan in `Step_1.md` and `ToturialUpgrade.md`.

## Architecture Patterns

### Current Monolithic Structure
```
Discord Bot → ML Models (quick_loader) → Binance API
          ↓
    File-based storage (CSV/PKL/JSON)
```

### Target Kafka-Based Architecture (In Progress)
```
Binance API → Producer → Kafka Topics → ML Consumer → Backtrader Decision Engine
                            ↓
                    Discord Bot + Streamlit Dashboard
```

**Kafka Topics Design** (from `ToturialUpgrade.md`):
- `crypto.market_data`: OHLCV data from Binance
- `crypto.ml_signals`: ML predictions with confidence scores
- `crypto.orders`: Trading decisions

## Critical Developer Workflows

### Security First: Token Management
**NEVER** commit tokens. Token resolution priority:
1. `DISCORD_BOT_TOKEN` env variable (recommended)
2. `BOT_TOKEN` env variable (legacy)
3. `token.txt` file (insecure, local dev only)

Always use `.env` file (already in `.gitignore`). See `docs/HUONG_DAN_BAO_MAT_TOKEN.md`.

### ML Model Training Pipeline
```powershell
# 1. Activate virtual environment
.\crypto-venv\Scripts\Activate.ps1

# 2. Collect data
python app\data_collector\realtime_collector.py

# 3. Train all models (orchestrator)
python app\ml\train_all.py

# 4. Models saved to models/*.joblib with metadata JSON
```

**Model persistence pattern**: All models use `BaseModel` abstract class (`app/ml/algorithms/base.py`) with standardized:
- `train(datasets: Dict[str, pd.DataFrame])` → returns metrics dict
- `predict(X: pd.DataFrame)` → returns np.ndarray
- `save_model(name: str)` → saves `.joblib` + `_metadata.json`

### Running the Discord Bot
```powershell
# Production quick loader path (prioritized)
python app\bot.py
# → Uses data/models_production/quick_loader.py if exists
# → Falls back to models/*.joblib
```

**Bot Commands** (`!dudoan`, `!price`, `!gia`, `!movers`) return Vietnamese-formatted embeds with VND conversion.

## Project-Specific Conventions

### File Organization
- `app/ml/algorithms/` - All ML models inherit from `BaseModel`
- `data/models_production/` - Production models with `quick_loader.py`
- `models/` - Development/training model artifacts
- `data/realtime/` - Real-time data collection (JSON/CSV)
- `docs/` - Vietnamese documentation (`.md` files)

### ML Algorithm Standardization
Current: Linear Regression, KNN Classifier/Regressor, K-Means
**Upgrade Plan** (from `DanhGiaTongQuan.md`): Add Random Forest (primary), SVM, Logistic Regression

All models must:
- Accept `datasets` dict with train/test splits
- Return standardized metrics: `{'r2', 'mae', 'rmse'}` for regression, `{'accuracy', 'precision', 'recall'}` for classification
- Support both `price` and `price_change` targets
- Include feature normalization (`normalize_features=True`)

### Feature Engineering Pattern
See `app/data_collector/realtime_collector.py`:
- Always calculate: `ma_7`, `ma_25`, `rsi_14`, `volatility_7d`, `volume_change_pct`
- Features must match training data schema exactly
- Use pandas `rolling()` for time-series features

### Discord Bot Response Format
```python
embed = discord.Embed(color=discord.Color.green())
embed.add_field(name="📊 Giá hiện tại", value=f"${price:,.2f}")
embed.add_field(name="🇻🇳 Giá VND", value=f"{vnd_price:,.0f} đ")
# Always include model name and R² score
```

## Kafka Integration (Upcoming)

### Development Environment Setup (Step 1)
```yaml
# docker-compose.yml structure (from Step_1.md)
services:
  zookeeper: confluentinc/cp-zookeeper:7.4.0 → port 2181
  kafka: confluentinc/cp-kafka:7.4.0 → ports 9092 (external), 29092 (internal)
  kafka-ui: provectuslabs/kafka-ui → http://localhost:8080
```

**Critical listeners config**:
```yaml
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
# → localhost:9092 for local Python code
# → kafka:29092 for Docker containers
```

### Producer Pattern (from `ToturialUpgrade.md`)
```python
from confluent_kafka import Producer
p = Producer({'bootstrap.servers': 'localhost:9092'})
data = {'symbol': 'BTCUSDT', 'price': 68000, 'timestamp': ...}
p.produce('crypto.market_data', json.dumps(data).encode('utf-8'))
p.flush()
```

### Data Leakage Prevention
**CRITICAL**: Use `TimeSeriesSplit` for validation. Never use future data to predict past (e.g., don't use 10:00 close price to predict 09:00).

## Integration Points

### Binance API
- Endpoint: `https://api.binance.com/api/v3`
- Supported symbols: 10 pairs (BTCUSDT, ETHUSDT, etc.) in `realtime_collector.py`
- Rate limits: Be cautious with API calls

### Model Registry
`app/ml/model_registry.py` tracks:
- Model versions with timestamps
- Metrics history
- Production deployment status

### Data Store
`app/services/store.py` - Abstraction layer for data persistence (file-based, preparing for MongoDB)

## External Dependencies

### Core Libraries
- `scikit-learn` - All ML algorithms
- `discord.py` - Bot framework
- `pandas`, `numpy` - Data processing
- `joblib` - Model serialization
- `confluent-kafka` - Kafka Python client (upcoming)

### Backtrader Integration (Planned)
Decision engine framework for trading logic with:
- PnL calculation
- Commission/slippage handling
- Risk management (stop loss, take profit)

## Code Quality Standards

### Vietnamese + English Hybrid
- User-facing: Vietnamese (`!dudoan`, `Giá VND`)
- Code/variables: English (`LinearRegressionModel`, `price_prediction`)
- Documentation: Both languages (see `docs/`)

### Error Handling Pattern
```python
try:
    # API call or ML prediction
except Exception as e:
    logger.error(f"❌ Error: {str(e)}")
    return fallback_value
```

### Path Handling
Always use `Path` from `pathlib` for cross-platform compatibility:
```python
project_root = Path(__file__).parent.parent.parent
data_dir = project_root / "data" / "realtime"
```

## Testing and Validation

### Model Evaluation
Run: `python app\ml\evaluate.py`
Generates reports in `reports/` with:
- Performance metrics per model
- Feature importance analysis
- Prediction distribution plots

### Bot Testing
```
!ping           # Health check
!dudoan BTC     # Full prediction flow
!price ETH      # API + quick prediction
```

## Known Limitations

- **Latency target**: ML `predict()` must complete <500ms or trading signals become stale
- **Data storage**: Currently file-based; MongoDB integration partial
- **Replication factor**: Kafka currently single-node (`KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1`)

## Quick Reference

### Activate Environment
```powershell
.\crypto-venv\Scripts\Activate.ps1  # Windows
```

### Common File Paths
- Bot token: `.env` → `DISCORD_BOT_TOKEN`
- Trained models: `models/*.joblib`
- Production models: `data/models_production/*.pkl`
- Upgrade roadmap: `Step_1.md`, `ToturialUpgrade.md`, `DanhGiaTongQuan.md`

### Entry Points
- Discord Bot: `app\bot.py`
- ML Training: `app\ml\train_all.py`
- Data Collection: `app\data_collector\realtime_collector.py`
- Demo/Monitoring: `monitor_bot.py`, `mock_bot_demo.py`

---

**For detailed Vietnamese documentation**: See `docs/TONG_QUAN_DU_AN.md`, `docs/QUICK_START.md`
