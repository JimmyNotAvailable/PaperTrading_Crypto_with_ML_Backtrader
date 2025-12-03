# 📡 KAFKA TOPICS SCHEMA DOCUMENTATION

> **Project**: Crypto ML Trading Bot
> 
> **Purpose**: Định nghĩa chuẩn message format cho các Kafka topics
> 
> **Version**: 1.0

---

## 📋 DANH SÁCH TOPICS

| Topic Name | Partitions | Retention | Producer | Consumer | Description |
|------------|-----------|-----------|----------|----------|-------------|
| `crypto.market_data` | 3 | 24h | Binance Producer | ML Consumer | Dữ liệu OHLCV real-time |
| `crypto.ml_signals` | 3 | 7 days | ML Consumer | Decision Engine, Bot | ML predictions |
| `crypto.orders` | 1 | 30 days | Decision Engine | Virtual Exchange | Trading orders |

---

## 1️⃣ TOPIC: `crypto.market_data`

### Mục đích
Thu thập dữ liệu giá cryptocurrency real-time từ Binance API

### Message Schema

```json
{
  "symbol": "BTCUSDT",
  "timestamp": 1701187200000,
  "price": 68000.50,
  "open": 67500.00,
  "high": 68500.00,
  "low": 67200.00,
  "volume": 12345.67,
  "price_change_pct": 2.15
}
```

### Field Definitions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `symbol` | string | ✅ | Crypto pair symbol | "BTCUSDT" |
| `timestamp` | integer | ✅ | Unix timestamp (milliseconds) | 1701187200000 |
| `price` | float | ✅ | Current/close price (USDT) | 68000.50 |
| `open` | float | ✅ | Opening price trong 24h | 67500.00 |
| `high` | float | ✅ | Highest price trong 24h | 68500.00 |
| `low` | float | ✅ | Lowest price trong 24h | 67200.00 |
| `volume` | float | ✅ | Trading volume 24h | 12345.67 |
| `price_change_pct` | float | ✅ | % thay đổi giá 24h | 2.15 |

### Message Key
- **Key**: `symbol` (string) - VD: `"BTCUSDT"`
- **Purpose**: Partition by symbol để đảm bảo ordering cho cùng coin

### Producer Logic

```python
from confluent_kafka import Producer
import json

def produce_market_data(symbol: str, data: dict):
    producer = Producer({'bootstrap.servers': 'localhost:9092'})
    
    message = json.dumps(data).encode('utf-8')
    producer.produce(
        topic='crypto.market_data',
        key=symbol.encode('utf-8'),
        value=message
    )
    producer.flush()
```

### Consumer Logic

```python
from confluent_kafka import Consumer
import json

def consume_market_data():
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'ml_consumer_group',
        'auto.offset.reset': 'latest'
    })
    
    consumer.subscribe(['crypto.market_data'])
    
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
            
        data = json.loads(msg.value().decode('utf-8'))
        # Process data...
```

### Validation Rules

- `symbol` must match pattern: `^[A-Z]{3,6}USDT$`
- `timestamp` must be within last 5 minutes
- `price`, `open`, `high`, `low` must be > 0
- `high` >= `low`
- `volume` >= 0

---

## 2️⃣ TOPIC: `crypto.ml_signals`

### Mục đích
Chứa kết quả predictions từ ML models (Random Forest, SVM, Logistic Regression)

### Message Schema

```json
{
  "symbol": "BTCUSDT",
  "timestamp": 1701187200000,
  "model": "random_forest",
  "prediction_type": "price",
  "predicted_value": 69500.00,
  "current_price": 68000.50,
  "expected_change_pct": 2.21,
  "confidence": 0.85,
  "signal": "BUY",
  "features": {
    "ma_7": 67800.00,
    "ma_25": 66500.00,
    "rsi_14": 62.5,
    "volatility_7d": 0.025,
    "volume_change_pct": 15.3
  },
  "metadata": {
    "model_version": "1.2.0",
    "r2_score": 0.892,
    "mae": 245.32
  }
}
```

### Field Definitions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `symbol` | string | ✅ | Crypto symbol | "BTCUSDT" |
| `timestamp` | integer | ✅ | Prediction timestamp (ms) | 1701187200000 |
| `model` | string | ✅ | Model name | "random_forest", "svm", "logistic_regression" |
| `prediction_type` | string | ✅ | Type of prediction | "price", "price_change", "trend" |
| `predicted_value` | float | ✅ | Giá dự đoán (USDT) | 69500.00 |
| `current_price` | float | ✅ | Giá hiện tại (USDT) | 68000.50 |
| `expected_change_pct` | float | ✅ | % thay đổi dự kiến | 2.21 |
| `confidence` | float | ✅ | Độ tin cậy (0-1) | 0.85 |
| `signal` | string | ✅ | Trading signal | "BUY", "SELL", "HOLD" |
| `features` | object | ✅ | Features used for prediction | {...} |
| `metadata` | object | ✅ | Model metadata | {...} |

### Signal Mapping

| `expected_change_pct` | `signal` | Strategy |
|----------------------|----------|----------|
| > +1.5% | "BUY" | Mua khi dự đoán tăng mạnh |
| < -1.5% | "SELL" | Bán khi dự đoán giảm mạnh |
| -1.5% to +1.5% | "HOLD" | Giữ khi biến động nhỏ |

### Confidence Levels

| `confidence` | Level | Action |
|-------------|-------|--------|
| >= 0.8 | High | Execute trade immediately |
| 0.6 - 0.8 | Medium | Confirm with other signals |
| < 0.6 | Low | Ignore signal |

### Producer Logic (ML Consumer)

```python
def produce_ml_signal(symbol: str, prediction_data: dict):
    producer = Producer({'bootstrap.servers': 'localhost:9092'})
    
    signal = {
        "symbol": symbol,
        "timestamp": int(time.time() * 1000),
        "model": "random_forest",
        "prediction_type": "price",
        "predicted_value": prediction_data['price'],
        "current_price": prediction_data['current'],
        "expected_change_pct": prediction_data['change_pct'],
        "confidence": prediction_data['confidence'],
        "signal": determine_signal(prediction_data['change_pct']),
        "features": prediction_data['features'],
        "metadata": {
            "model_version": "1.2.0",
            "r2_score": 0.892,
            "mae": 245.32
        }
    }
    
    message = json.dumps(signal).encode('utf-8')
    producer.produce('crypto.ml_signals', key=symbol.encode('utf-8'), value=message)
    producer.flush()
```

### Validation Rules

- `confidence` must be between 0.0 and 1.0
- `signal` must be one of: "BUY", "SELL", "HOLD"
- `timestamp` must be recent (within last 2 minutes)
- `predicted_value` and `current_price` must be > 0

---

## 3️⃣ TOPIC: `crypto.orders`

### Mục đích
Chứa lệnh giao dịch từ Decision Engine (Backtrader)

### Message Schema

```json
{
  "order_id": "ORD-20251128-001",
  "symbol": "BTCUSDT",
  "timestamp": 1701187200000,
  "action": "BUY",
  "order_type": "MARKET",
  "quantity": 0.1,
  "price": 68000.50,
  "total_value": 6800.05,
  "status": "PENDING",
  "strategy": "ml_signal_strategy",
  "trigger_signal": {
    "model": "random_forest",
    "confidence": 0.85,
    "expected_change_pct": 2.21
  },
  "risk_management": {
    "stop_loss": 66640.49,
    "take_profit": 71400.53,
    "stop_loss_pct": -2.0,
    "take_profit_pct": 5.0
  },
  "metadata": {
    "portfolio_balance_usdt": 10000.00,
    "position_size_pct": 68.0,
    "created_by": "backtrader_engine"
  }
}
```

### Field Definitions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `order_id` | string | ✅ | Unique order ID | "ORD-20251128-001" |
| `symbol` | string | ✅ | Crypto symbol | "BTCUSDT" |
| `timestamp` | integer | ✅ | Order creation timestamp | 1701187200000 |
| `action` | string | ✅ | Order action | "BUY", "SELL" |
| `order_type` | string | ✅ | Order type | "MARKET", "LIMIT" |
| `quantity` | float | ✅ | Số lượng coin | 0.1 |
| `price` | float | ✅ | Giá thực hiện | 68000.50 |
| `total_value` | float | ✅ | Tổng giá trị (USDT) | 6800.05 |
| `status` | string | ✅ | Order status | "PENDING", "FILLED", "CANCELLED" |
| `strategy` | string | ✅ | Strategy name | "ml_signal_strategy" |
| `trigger_signal` | object | ✅ | ML signal triggered order | {...} |
| `risk_management` | object | ✅ | Stop loss & take profit | {...} |
| `metadata` | object | ✅ | Additional info | {...} |

### Order Status Flow

```
PENDING → FILLED → CLOSED
         ↓
      CANCELLED
```

| Status | Description |
|--------|-------------|
| `PENDING` | Lệnh đã tạo, chờ thực thi |
| `FILLED` | Lệnh đã khớp thành công |
| `CANCELLED` | Lệnh bị hủy |
| `CLOSED` | Position đã đóng (take profit/stop loss) |

### Producer Logic (Backtrader)

```python
import backtrader as bt

class MLSignalStrategy(bt.Strategy):
    def next(self):
        # Consume ML signal from Kafka
        signal = consume_latest_signal(self.symbol)
        
        if signal['signal'] == 'BUY' and signal['confidence'] > 0.7:
            # Calculate position size
            quantity = self.calculate_position_size()
            
            # Create order
            order = {
                "order_id": generate_order_id(),
                "symbol": self.symbol,
                "timestamp": int(time.time() * 1000),
                "action": "BUY",
                "order_type": "MARKET",
                "quantity": quantity,
                "price": self.data.close[0],
                "total_value": quantity * self.data.close[0],
                "status": "PENDING",
                "strategy": "ml_signal_strategy",
                "trigger_signal": {
                    "model": signal['model'],
                    "confidence": signal['confidence'],
                    "expected_change_pct": signal['expected_change_pct']
                },
                "risk_management": {
                    "stop_loss": self.data.close[0] * 0.98,  # -2%
                    "take_profit": self.data.close[0] * 1.05,  # +5%
                    "stop_loss_pct": -2.0,
                    "take_profit_pct": 5.0
                }
            }
            
            # Produce to Kafka
            produce_order(order)
            
            # Execute in Backtrader
            self.buy(size=quantity)
```

### Validation Rules

- `quantity` must be > 0
- `price` must be > 0
- `action` must be "BUY" or "SELL"
- `stop_loss` < `price` < `take_profit` (for BUY orders)
- `total_value` = `quantity` * `price`

---

## 🔧 KAFKA CONFIGURATION

### Producer Config (Best Practices)

```python
producer_config = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'your_service_name',
    'compression.type': 'gzip',  # Tiết kiệm bandwidth
    'acks': 'all',  # Đảm bảo message không mất
    'retries': 3,
    'max.in.flight.requests.per.connection': 1  # Đảm bảo ordering
}
```

### Consumer Config (Best Practices)

```python
consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'your_consumer_group',
    'auto.offset.reset': 'latest',  # Chỉ đọc message mới
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 5000,
    'max.poll.records': 100
}
```

---

## 🔍 MONITORING & DEBUGGING

### Kafka UI (Web Interface)
- URL: http://localhost:8080
- Features:
  - View topics & partitions
  - Browse messages
  - Monitor consumer groups
  - Check lag

### CLI Tools

```bash
# List topics
docker exec -it crypto_kafka kafka-topics --list --bootstrap-server localhost:9092

# Describe topic
docker exec -it crypto_kafka kafka-topics --describe --topic crypto.market_data --bootstrap-server localhost:9092

# Consume messages (debug)
docker exec -it crypto_kafka kafka-console-consumer --topic crypto.ml_signals --from-beginning --bootstrap-server localhost:9092
```

---

## 📊 MESSAGE FLOW DIAGRAM

```
┌───────────────┐
│ Binance API   │
└───────┬───────┘
        │ HTTP GET
        ▼
┌───────────────────────┐
│ Binance Producer      │
│ (app/producers/)      │
└───────┬───────────────┘
        │ Produce
        ▼
┌─────────────────────────────────┐
│ Topic: crypto.market_data       │
│ { symbol, price, volume, ... }  │
└───────┬─────────────────────────┘
        │ Consume
        ▼
┌───────────────────────┐
│ ML Consumer           │
│ (app/consumers/)      │
│ - Load model          │
│ - Feature engineering │
│ - Predict             │
└───────┬───────────────┘
        │ Produce
        ▼
┌─────────────────────────────────┐
│ Topic: crypto.ml_signals        │
│ { prediction, confidence, ... } │
└───────┬─────────────────────────┘
        │ Consume
        ▼
┌───────────────────────┐
│ Decision Engine       │
│ (Backtrader)          │
│ - Evaluate signal     │
│ - Risk management     │
│ - Create order        │
└───────┬───────────────┘
        │ Produce
        ▼
┌─────────────────────────────────┐
│ Topic: crypto.orders            │
│ { order_id, action, price, ... }│
└───────┬─────────────────────────┘
        │ Consume
        ├──────────────┬──────────┐
        ▼              ▼          ▼
┌─────────────┐  ┌──────────┐  ┌────────────┐
│ Discord Bot │  │ Streamlit│  │ Virtual    │
│             │  │ Dashboard│  │ Exchange   │
└─────────────┘  └──────────┘  └────────────┘
```

---

## 🚨 ERROR HANDLING

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `KafkaException: Broker not available` | Kafka container chưa chạy | `docker-compose up -d kafka` |
| `Message serialization error` | JSON không hợp lệ | Validate schema before produce |
| `Consumer group rebalancing` | Consumer join/leave | Normal behavior, wait for stabilization |
| `Offset out of range` | Đọc offset đã bị xóa (retention) | Set `auto.offset.reset: 'latest'` |

### Retry Logic

```python
from confluent_kafka import Producer
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def produce_with_retry(producer, topic, message):
    producer.produce(topic, value=message)
    producer.flush()
```

---

**Document Version**: 1.0  
**Last Updated**: November 28, 2025  
**Maintained By**: Crypto ML Trading Team
