# 📋 KẾ HOẠCH TÁI CẤU TRÚC DỰ ÁN - KAFKA INTEGRATION

> **Mục tiêu**: Chuyển đổi từ kiến trúc Monolithic sang Event-Driven Microservices với Apache Kafka
> 
> **Phiên bản**: 1.0 - Phase 1 Implementation
> 
> **Ngày**: November 28, 2025

---

## 📊 HIỆN TRẠNG DỰ ÁN (AS-IS)

### Cấu trúc hiện tại
```
crypto-ml-trading-project/
├── app/
│   ├── bot.py                    # Discord bot (monolithic)
│   ├── ml/                       # ML algorithms
│   │   ├── algorithms/          # LinearRegression, KNN, KMeans
│   │   ├── train_all.py         # Training orchestrator
│   │   └── model_registry.py    # Model versioning
│   ├── data_collector/          # Binance API scraper
│   │   └── realtime_collector.py
│   └── services/
│       ├── trainer.py           # Auto training service
│       └── store.py             # File-based storage
├── data/
│   ├── realtime/                # CSV/JSON data files
│   └── models_production/       # .joblib/.pkl files
├── models/                       # Training artifacts
└── docs/                         # Documentation
```

### Vấn đề cần giải quyết

1. **Tight Coupling**: Bot trực tiếp gọi ML models và Binance API
2. **File-based Storage**: Dữ liệu lưu CSV/JSON, khó scale và sync
3. **No Message Queue**: Không có buffer khi API Binance chậm hoặc ML tính toán lâu
4. **Single Point of Failure**: Bot crash = toàn bộ hệ thống ngưng
5. **Limited Algorithms**: Chỉ có 3 thuật toán cũ (Linear, KNN, KMeans)

---

## 🎯 MỤC TIÊU TÁI CẤU TRÚC (TO-BE)

### Kiến trúc mới (Kafka-based Microservices)

```
┌─────────────────────────────────────────────────────────────────┐
│                     APACHE KAFKA CLUSTER                         │
│                                                                  │
│  Topics:                                                         │
│  • crypto.market_data    → OHLCV từ Binance                     │
│  • crypto.ml_signals     → Predictions từ ML Service            │
│  • crypto.orders         → Trading decisions                     │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
    │ Producer│         │ML Service│        │Decision │
    │ Service │         │(Consumer)│        │ Engine  │
    │         │         │          │        │         │
    │ Binance │         │RandomFor-│        │Backtra- │
    │   API   │         │est + SVM │        │  der    │
    └─────────┘         │+ Logistic│        └─────────┘
                        └──────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌──────────┐        ┌──────────┐
              │ Discord  │        │Streamlit │
              │   Bot    │        │Dashboard │
              └──────────┘        └──────────┘
```

### Lợi ích

✅ **Decoupling**: Mỗi service độc lập, dễ maintain
✅ **Scalability**: Có thể chạy nhiều ML Consumer song song
✅ **Resilience**: Kafka buffer data khi service tạm ngưng
✅ **Real Big Data**: Sẵn sàng cho millions records/day
✅ **Modern Stack**: Phù hợp CDIO & Production-ready

---

## 📁 CẤU TRÚC THƯ MỤC MỚI (Đề xuất)

```
crypto-ml-trading-project/
├── .github/
│   └── copilot-instructions.md          # ← ĐÃ TẠO
│
├── docker-compose.yml                   # ← CẦN CẬP NHẬT (Kafka + Zookeeper + UI)
├── .env.example                         # ← Template cho biến môi trường
├── .env                                 # ← Secrets (KHÔNG commit)
├── .gitignore                           # ← Đã có (kiểm tra .env, data/)
├── requirements.txt                     # ← CẦN BỔ SUNG confluent-kafka, backtrader
│
├── app/
│   ├── __init__.py
│   │
│   ├── producers/                       # ← MỚI: Kafka Producers
│   │   ├── __init__.py
│   │   ├── binance_producer.py         # Thu thập data → Kafka
│   │   └── config.py                   # Kafka connection config
│   │
│   ├── consumers/                       # ← MỚI: Kafka Consumers
│   │   ├── __init__.py
│   │   ├── ml_consumer.py              # Consume market_data → predict → produce signals
│   │   └── decision_consumer.py        # Consume signals → Backtrader → produce orders
│   │
│   ├── ml/                              # ← GIỮ NGUYÊN + NÂNG CẤP
│   │   ├── algorithms/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Abstract BaseModel
│   │   │   ├── linear_regression.py    # ← Giữ lại
│   │   │   ├── knn_models.py           # ← Giữ lại
│   │   │   ├── clustering.py           # ← Giữ lại (K-Means)
│   │   │   ├── random_forest.py        # ← ĐÃ CÓ - CẦN KIỂM TRA
│   │   │   ├── svm_models.py           # ← MỚI (Support Vector Machine)
│   │   │   └── logistic_regression.py  # ← ĐÃ CÓ - CẦN KIỂM TRA
│   │   ├── core.py
│   │   ├── data_prep.py
│   │   ├── train_all.py                # ← CẬP NHẬT: train 3 models mới
│   │   └── model_registry.py
│   │
│   ├── backtrader/                      # ← MỚI: Decision Engine
│   │   ├── __init__.py
│   │   ├── strategies/
│   │   │   ├── ml_strategy.py          # Strategy nhận signals từ Kafka
│   │   │   └── risk_management.py      # Stop loss, take profit logic
│   │   └── virtual_exchange.py         # Sàn ảo để demo
│   │
│   ├── bot.py                           # ← GIỮ NGUYÊN nhưng refactor
│   │                                    #    Sẽ consume từ Kafka thay vì gọi trực tiếp
│   ├── services/
│   │   ├── trainer.py                  # ← Giữ nguyên
│   │   └── store.py                    # ← Giữ nguyên (chuẩn bị MongoDB)
│   │
│   └── utils/                           # ← MỚI: Shared utilities
│       ├── __init__.py
│       ├── logger.py                   # Centralized logging
│       └── config_loader.py            # Load .env safely
│
├── config/                              # ← MỚI: Configuration files
│   ├── kafka_config.py
│   ├── mongodb_config.py               # ← ĐÃ CÓ
│   └── production_config.py            # ← ĐÃ CÓ
│
├── data/
│   ├── realtime/                       # ← Giữ nguyên (legacy)
│   ├── cache/                          # ← Giữ nguyên
│   └── models_production/              # ← Giữ nguyên
│
├── models/                              # ← Giữ nguyên (.joblib files)
│
├── scripts/
│   ├── setup_environment.ps1           # ← ĐÃ CÓ
│   └── init_kafka_topics.py            # ← MỚI: Tạo topics tự động
│
├── web/                                 # ← MỚI: Streamlit Dashboard
│   ├── app.py                          # Main Streamlit app
│   ├── components/
│   │   ├── price_chart.py              # Real-time chart
│   │   ├── ml_predictions.py           # ML signals display
│   │   └── virtual_portfolio.py        # Portfolio tracker
│   └── requirements.txt                # streamlit, plotly
│
├── tests/                               # ← MỞ RỘNG
│   ├── test_producers.py
│   ├── test_consumers.py
│   └── test_ml_models.py
│
└── docs/
    ├── RESTRUCTURING_PLAN_KAFKA.md     # ← FILE NÀY
    ├── Step_1.md                       # ← ĐÃ CÓ (Phase 1 guide)
    ├── ToturialUpgrade.md              # ← ĐÃ CÓ (Upgrade guide)
    ├── DanhGiaTongQuan.md              # ← ĐÃ CÓ (Overall assessment)
    └── KAFKA_TOPICS_SCHEMA.md          # ← MỚI: Kafka message schemas
```

---

## 🔧 PHASE 1: SETUP INFRASTRUCTURE (Tuần 1-2)

### Bước 1.1: Cập nhật Dependencies

**File: `requirements.txt`**
```txt
# Existing
pymongo
requests
scikit-learn
numpy
pandas
discord.py
python-dotenv
joblib
psutil

# ← THÊM MỚI cho Kafka
confluent-kafka==2.3.0         # Kafka Python client (C-based, nhanh)

# ← THÊM MỚI cho Backtrader
backtrader==1.9.78.123         # Trading framework

# ← THÊM MỚI cho Dashboard
streamlit==1.28.0
plotly==5.18.0

# ← THÊM MỚI cho Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

**Cài đặt**:
```powershell
.\crypto-venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Bước 1.2: Setup Kafka với Docker Compose

**File: `docker-compose.yml` (CẬP NHẬT)**

```yaml
version: '3.8'

services:
  # ========== KAFKA INFRASTRUCTURE ==========
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    hostname: zookeeper
    container_name: crypto_zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data
      - zookeeper_logs:/var/lib/zookeeper/log

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    hostname: kafka
    container_name: crypto_kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"      # External access (localhost Python)
      - "29092:29092"    # Internal access (Docker network)
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    volumes:
      - kafka_data:/var/lib/kafka/data
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 5

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: crypto_kafka_ui
    ports:
      - "8080:8080"
    depends_on:
      - kafka
    environment:
      KAFKA_CLUSTERS_0_NAME: crypto_cluster
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181

  # ========== MONGODB (Existing) ==========
  mongo:
    image: mongo:latest
    container_name: crypto_mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
      - ./db/init:/docker-entrypoint-initdb.d

  # ========== PYTHON SERVICES (To be added later) ==========
  # producer:
  #   build: .
  #   container_name: crypto_producer
  #   environment:
  #     - KAFKA_BOOTSTRAP_SERVERS=kafka:29092
  #   depends_on:
  #     - kafka

volumes:
  zookeeper_data:
  zookeeper_logs:
  kafka_data:
  mongo_data:
```

**Khởi động**:
```powershell
docker-compose up -d
docker ps  # Kiểm tra 4 containers: zookeeper, kafka, kafka-ui, mongo
```

**Kiểm tra Kafka UI**: Mở http://localhost:8080

### Bước 1.3: Tạo Kafka Topics

**File: `scripts/init_kafka_topics.py` (MỚI)**

```python
#!/usr/bin/env python3
"""
Khởi tạo Kafka topics cho Crypto ML Trading Project
"""

from confluent_kafka.admin import AdminClient, NewTopic
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_topics():
    """Tạo các Kafka topics cần thiết"""
    
    admin_client = AdminClient({
        'bootstrap.servers': 'localhost:9092'
    })
    
    topics = [
        NewTopic(
            topic='crypto.market_data',
            num_partitions=3,
            replication_factor=1,
            config={
                'retention.ms': '86400000',  # 24 hours
                'compression.type': 'gzip'
            }
        ),
        NewTopic(
            topic='crypto.ml_signals',
            num_partitions=3,
            replication_factor=1,
            config={
                'retention.ms': '604800000',  # 7 days
                'compression.type': 'gzip'
            }
        ),
        NewTopic(
            topic='crypto.orders',
            num_partitions=1,
            replication_factor=1,
            config={
                'retention.ms': '2592000000',  # 30 days
                'cleanup.policy': 'compact'
            }
        )
    ]
    
    # Tạo topics
    fs = admin_client.create_topics(topics)
    
    for topic, f in fs.items():
        try:
            f.result()
            logger.info(f"✅ Topic '{topic}' created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create topic '{topic}': {e}")

if __name__ == "__main__":
    create_topics()
```

**Chạy**:
```powershell
python scripts\init_kafka_topics.py
```

### Bước 1.4: Cập nhật .env Template

**File: `.env.example`**

```env
# ========== DISCORD BOT ==========
DISCORD_BOT_TOKEN=your-discord-token-here

# ========== KAFKA CONFIGURATION ==========
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=crypto_ml_group

# ========== BINANCE API ==========
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key

# ========== MONGODB ==========
MONGODB_URI=mongodb://localhost:27017/crypto

# ========== CURRENCY ==========
FX_USD_VND=24000

# ========== ML SETTINGS ==========
ML_MODEL_PATH=./models
ML_PREDICTION_THRESHOLD=0.7

# ========== LOGGING ==========
LOG_LEVEL=INFO
```

**Copy để sử dụng**:
```powershell
copy .env.example .env
# Sau đó chỉnh sửa .env với thông tin thực tế
```

---

## 📝 PHASE 2: IMPLEMENT PRODUCERS (Tuần 3)

### File: `app/producers/binance_producer.py` (MỚI)

```python
#!/usr/bin/env python3
"""
Kafka Producer: Thu thập dữ liệu crypto từ Binance → Kafka topic
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List
import logging

from confluent_kafka import Producer
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceKafkaProducer:
    """Producer service: Binance API → Kafka"""
    
    def __init__(self):
        self.kafka_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'client.id': 'binance_producer'
        }
        self.producer = Producer(self.kafka_config)
        self.topic = 'crypto.market_data'
        
        self.binance_api = "https://api.binance.com/api/v3"
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOGEUSDT',
            'XRPUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT'
        ]
    
    def delivery_report(self, err, msg):
        """Callback khi message được gửi"""
        if err is not None:
            logger.error(f'❌ Message delivery failed: {err}')
        else:
            logger.debug(f'✅ Message delivered to {msg.topic()} [{msg.partition()}]')
    
    def fetch_market_data(self, symbol: str) -> Dict:
        """Lấy dữ liệu OHLCV từ Binance"""
        try:
            # Current price
            ticker_url = f"{self.binance_api}/ticker/24hr?symbol={symbol}"
            response = requests.get(ticker_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                market_data = {
                    'symbol': symbol,
                    'timestamp': int(time.time() * 1000),
                    'price': float(data['lastPrice']),
                    'open': float(data['openPrice']),
                    'high': float(data['highPrice']),
                    'low': float(data['lowPrice']),
                    'volume': float(data['volume']),
                    'price_change_pct': float(data['priceChangePercent'])
                }
                
                return market_data
            else:
                logger.error(f"Binance API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def produce_market_data(self):
        """Main loop: Thu thập và gửi dữ liệu vào Kafka"""
        logger.info(f"🚀 Starting Binance Producer...")
        logger.info(f"📡 Kafka: {self.kafka_config['bootstrap.servers']}")
        logger.info(f"📊 Symbols: {', '.join(self.symbols)}")
        
        while True:
            try:
                for symbol in self.symbols:
                    data = self.fetch_market_data(symbol)
                    
                    if data:
                        # Serialize to JSON
                        message = json.dumps(data).encode('utf-8')
                        
                        # Send to Kafka
                        self.producer.produce(
                            self.topic,
                            key=symbol.encode('utf-8'),
                            value=message,
                            callback=self.delivery_report
                        )
                        
                        logger.info(f"📤 Produced: {symbol} @ ${data['price']:,.2f}")
                
                # Flush buffer
                self.producer.flush()
                
                # Wait 60s before next batch
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Producer stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in producer loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    producer = BinanceKafkaProducer()
    producer.produce_market_data()
```

**Chạy Producer**:
```powershell
python app\producers\binance_producer.py
```

---

## 📊 PHASE 3: ML MODELS UPGRADE (Tuần 4-5)

### Bước 3.1: Implement Random Forest (Primary Model)

**File: `app/ml/algorithms/random_forest.py`** (ĐÃ TỒN TẠI - kiểm tra)

```python
# Kiểm tra file này đã có chưa:
ls app\ml\algorithms\random_forest.py

# Nếu chưa có, cần tạo mới theo pattern BaseModel
```

### Bước 3.2: Implement SVM

**File: `app/ml/algorithms/svm_models.py` (MỚI)**

```python
from sklearn.svm import SVR, SVC
from sklearn.preprocessing import StandardScaler
from .base import BaseModel
# ... (implement theo pattern LinearRegressionModel)
```

### Bước 3.3: Verify Logistic Regression

```python
# Kiểm tra file:
ls app\ml\algorithms\logistic_regression.py
# → ĐÃ TỒN TẠI → Cần kiểm tra tuân thủ BaseModel
```

### Bước 3.4: Update train_all.py

Thêm 3 models mới vào training pipeline:
- Random Forest (primary)
- SVM
- Logistic Regression

---

## 🤖 PHASE 4: ML CONSUMER SERVICE (Tuần 6)

**File: `app/consumers/ml_consumer.py` (MỚI)**

```python
#!/usr/bin/env python3
"""
Kafka Consumer: Nhận market_data → ML Prediction → Produce signals
"""

import os
import json
import joblib
from confluent_kafka import Consumer, Producer
# ... (consume từ crypto.market_data, predict, produce vào crypto.ml_signals)
```

---

## 📈 PHASE 5: BACKTRADER INTEGRATION (Tuần 7-8)

**File: `app/backtrader/strategies/ml_strategy.py` (MỚI)**

```python
import backtrader as bt

class MLSignalStrategy(bt.Strategy):
    """Strategy nhận signals từ Kafka topic crypto.ml_signals"""
    # ... (implement logic mua/bán dựa trên ML predictions)
```

---

## 🎨 PHASE 6: STREAMLIT DASHBOARD (Tuần 9)

**File: `web/app.py` (MỚI)**

```python
import streamlit as st
from confluent_kafka import Consumer
# ... (3-column layout: Price Chart | ML Signals | Virtual Portfolio)
```

---

## ✅ CHECKLIST TRIỂN KHAI

### Phase 1: Infrastructure ✅
- [ ] Cập nhật `requirements.txt` với confluent-kafka, backtrader
- [ ] Cập nhật `docker-compose.yml` với Kafka/Zookeeper/UI
- [ ] Chạy `docker-compose up -d`
- [ ] Chạy `scripts/init_kafka_topics.py`
- [ ] Kiểm tra Kafka UI (localhost:8080)
- [ ] Tạo `.env` từ `.env.example`

### Phase 2: Producer ✅
- [ ] Tạo `app/producers/binance_producer.py`
- [ ] Test producer: `python app\producers\binance_producer.py`
- [ ] Verify messages trong Kafka UI

### Phase 3: ML Upgrade
- [ ] Kiểm tra `random_forest.py` (đã có sẵn?)
- [ ] Tạo `svm_models.py`
- [ ] Verify `logistic_regression.py`
- [ ] Update `train_all.py` để train 3 models
- [ ] Chạy training: `python app\ml\train_all.py`

### Phase 4: Consumer
- [ ] Tạo `app/consumers/ml_consumer.py`
- [ ] Test consumer với producer
- [ ] Verify predictions trong topic `crypto.ml_signals`

### Phase 5: Backtrader
- [ ] Cài `pip install backtrader`
- [ ] Tạo `app/backtrader/strategies/ml_strategy.py`
- [ ] Tạo `virtual_exchange.py` cho demo

### Phase 6: Dashboard
- [ ] Tạo `web/app.py`
- [ ] Implement real-time chart với Plotly
- [ ] Test: `streamlit run web\app.py`

---

## 🚨 RỦI RO & GIẢI PHÁP

| Rủi ro | Giải pháp |
|---------|-----------|
| **Kafka quá nặng cho dev** | Chỉ chạy khi test, tắt khi không dùng: `docker-compose down` |
| **Data leakage trong ML** | Bắt buộc `TimeSeriesSplit`, review `data_prep.py` |
| **Latency >500ms** | Profile code, optimize feature engineering |
| **Token leak** | Rà soát `.gitignore`, không commit `.env` |

---

## 📚 TÀI LIỆU THAM KHẢO

- `Step_1.md` - Hướng dẫn Phase 1 chi tiết
- `ToturialUpgrade.md` - Kafka architecture diagram
- `DanhGiaTongQuan.md` - Đánh giá ML algorithms
- `.github/copilot-instructions.md` - AI agent guide

---

**Author**: AI Restructuring Plan
**Date**: November 28, 2025
**Version**: 1.0
