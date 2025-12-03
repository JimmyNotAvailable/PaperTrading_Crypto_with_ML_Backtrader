# 🚀 Paper Trading Crypto with ML & Backtrader

**Event-driven cryptocurrency ML trading system** combining Discord bot interface, real-time data collection, ML predictions, and Kafka-based microservices architecture with Backtrader execution engine.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Kafka](https://img.shields.io/badge/Kafka-7.4.0-orange.svg)](https://kafka.apache.org/)
[![Backtrader](https://img.shields.io/badge/Backtrader-1.9.78-green.svg)](https://www.backtrader.com/)

---

## 📋 Key Features

✅ **Discord Bot Interface** - Vietnamese chat interface for price predictions  
✅ **Real-time Data Collection** - OHLCV data from Binance API  
✅ **Machine Learning Models** - Linear Regression, KNN, K-Means  
✅ **Kafka Event Streaming** - Event-driven architecture  
✅ **Backtrader Decision Engine** - Risk management with auto SL/TP  
✅ **SQLite Logging** - Trade storage for dashboard  
✅ **100% Vietnamese Logs** - Professional logging without emojis  
🚧 **Streamlit Dashboard** - Coming soon (Phase 5)

---

## 🏗️ System Architecture

```
Binance API → Kafka → ML Models → Backtrader Engine → SQLite/Dashboard
```

**Full Pipeline:**
1. **Phase 1:** Binance Producer → `crypto.market_data` topic
2. **Phase 2:** ML Consumer processes data → predictions
3. **Phase 3:** ML predictions → `crypto.ml_signals` topic
4. **Phase 4:** Backtrader Decision Engine → `crypto.orders` topic + SQLite
5. **Phase 5:** Streamlit Dashboard (in progress)

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git

### 2. Installation
```bash
git clone https://github.com/JimmyNotAvailable/PaperTrading_Crypto_with_ML_Backtrader.git
cd PaperTrading_Crypto_with_ML_Backtrader
python -m venv crypto-venv
.\crypto-venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

### 3. Start Kafka
```bash
docker-compose up -d
```

### 4. Configure Bot Token
Create `.env` file:
```
DISCORD_BOT_TOKEN=your_token_here
```

### 5. Run System
```bash
# Terminal 1: Binance Producer
python app\producers\binance_producer.py

# Terminal 2: ML Consumer
python app\consumers\ml_consumer.py

# Terminal 3: Backtrader Engine
python app\consumers\backtrader_decision_engine.py

# Terminal 4: Discord Bot
python app\bot.py
```

---

## 🧪 Demo Mode

Test without real Binance API:

```bash
# Terminal 1: Fake Signals
python demo_phase4.py --send-signals --duration 300 --interval 10

# Terminal 2: Decision Engine
python app\consumers\backtrader_decision_engine.py
```

Check database:
```bash
python check_db.py
```

---

## 🎯 Risk Management

- **Stop Loss:** 2% below entry
- **Take Profit:** 5% above entry
- **Min Confidence:** 60% (skip if ML confidence < 60%)
- **Position Size:** 95% of available cash
- **Commission:** 0.1% per trade
- **Risk/Reward:** 1:2.5 (displayed in logs)

---

## 📊 ML Models

| Model | Purpose | Metrics |
|-------|---------|---------|
| Linear Regression | Price prediction | R², MAE, RMSE |
| KNN Classifier | Trend direction (BUY/SELL) | Accuracy, Precision |
| KNN Regressor | Price change % | R², MAE |
| K-Means | Market volatility clustering | Silhouette score |

---

## 📈 Kafka Topics

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `crypto.market_data` | Binance | ML Consumer | OHLCV real-time |
| `crypto.ml_signals` | ML Consumer | Decision Engine | ML predictions |
| `crypto.orders` | Decision Engine | Dashboard | Trading decisions |

---

## 📝 Log Format (Vietnamese)

```
[TIN HIEU ML] BTCUSDT
   Du bao: BUY
   Gia: $67,897.65
   Do tin cay: 80.34%
   
[QUYET DINH MUA] ML Signal BUY with 80.34% confidence
   Khoi luong: 0.139916 BTC
   Stop Loss: $66,539.70 (-2.0%)
   Take Profit: $71,292.53 (+5.0%)
   Risk/Reward: 1:2.50
```

**Tags:** `[KHOI TAO]` `[TIN HIEU ML]` `[QUYET DINH MUA]` `[QUYET DINH BAN]` `[CAT LO]` `[CHOT LOI]` `[KAFKA]` `[LOI]`

---

## 🗂️ Project Structure

```
app/
├── bot.py                          # Discord bot
├── producers/binance_producer.py   # Binance data
├── consumers/
│   ├── ml_consumer.py              # ML predictions
│   └── backtrader_decision_engine.py  # Trading logic
├── services/
│   ├── backtrader_broker.py        # Backtrader wrapper
│   └── kafka_datafeed.py           # Kafka feed
└── ml/algorithms/                  # ML models

data/
├── realtime/                       # Cache
├── models_production/              # Trained models
└── trading_logs.db                 # SQLite logs

config/
├── kafka_config.py                 # Kafka settings
└── symbols_config.py               # Trading pairs

docs/                               # Vietnamese docs
demo_phase4.py                      # Demo script
docker-compose.yml                  # Kafka setup
requirements.txt                    # Dependencies
```

---

## 🛠️ Tech Stack

**Core:** Python 3.10+ • Apache Kafka 7.4.0 • Backtrader 1.9.78 • scikit-learn • Discord.py  
**Infrastructure:** Docker • SQLite • MongoDB (optional)  
**Data:** Pandas • NumPy • Binance API  

---

## 🚧 Roadmap

### ✅ Completed (Phase 1-4)
- [x] Discord bot interface
- [x] Real-time Binance data collection
- [x] ML models (LR, KNN, K-Means)
- [x] Kafka event streaming
- [x] Backtrader decision engine
- [x] SQLite logging
- [x] Vietnamese log system

### 🚀 In Progress (Phase 5)
- [ ] Streamlit dashboard
- [ ] Real-time charts
- [ ] Performance analytics

### 📅 Future
- [ ] More ML models (Random Forest, LSTM)
- [ ] Live trading
- [ ] Web API (FastAPI)
- [ ] Mobile app

---

## 📚 Documentation

- [Phase 4 Final Report](PHASE4_FINAL_REPORT.md)
- [Phase 5 Dashboard Guide](PHASE5_DASHBOARD_GUIDE.md)
- [Vietnamese Docs](docs/)

---

## ⚠️ Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY**

❌ DO NOT use for live trading with real money  
❌ Past results DO NOT guarantee future profits  
❌ Cryptocurrency trading is high risk  
✅ Paper trading and backtesting only  

Author not responsible for financial losses.

---

## 📧 Contact

**GitHub:** [@JimmyNotAvailable](https://github.com/JimmyNotAvailable)  
**Project:** [PaperTrading_Crypto_with_ML_Backtrader](https://github.com/JimmyNotAvailable/PaperTrading_Crypto_with_ML_Backtrader)

---

## 🙏 Acknowledgments

[Backtrader](https://www.backtrader.com/) • [Apache Kafka](https://kafka.apache.org/) • [Binance API](https://binance-docs.github.io/apidocs/) • [scikit-learn](https://scikit-learn.org/)

---

**Made with ❤️ in Vietnam 🇻🇳**
