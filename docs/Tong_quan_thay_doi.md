Chào bạn, tôi đã thiết kế lại quy trình triển khai thành một **Tutorial 5 Giai Đoạn** chi tiết. Lộ trình này đảm bảo tính logic từ cơ sở hạ tầng (Kafka) đến trí tuệ (ML) và cuối cùng là hiển thị (Dashboard/Discord).

Dưới đây là các bước thực hiện tuần tự để nâng cấp dự án hiện tại lên chuẩn Big Data & Real-time Trading.

---

### 🗺️ LỘ TRÌNH TRIỂN KHAI TỔNG QUAN

1. **Phase 1: Infrastructure** - Dựng môi trường Docker & Kafka.
2. **Phase 2: Data Pipeline** - Chuyển đổi Data Collector cũ sang Kafka Producer.
3. **Phase 3: ML Upgrade** - Train 3 Model mới & Tạo Service dự đoán (Consumer 1).
4. **Phase 4: Decision Engine** - Xây dựng hệ thống khớp lệnh ảo (Consumer 2).
5. **Phase 5: Interface** - Streamlit Dashboard & Cập nhật Discord Bot.

---

### 🛠️ PHASE 1: INFRASTRUCTURE (NỀN MÓNG)

**Mục tiêu:** Tạo "đường ống" truyền dữ liệu thay vì lưu file `.csv` hay `.pkl` cục bộ dễ gây lỗi khóa file (file locks) như dự án cũ.

**Bước 1.1: Cấu trúc lại thư mục dự án** Tạo cấu trúc mới để tách biệt rõ ràng:

```text
project_root/
├── docker-compose.yml       # Cấu hình Kafka
├── app/
│   ├── producers/           # Code đẩy dữ liệu (Data Collector cũ)
│   ├── consumers/           # Code xử lý (ML & Trading Engine)
│   ├── ml_training/         # Code train model (RandomForest, SVM, LogReg)
│   ├── dashboard/           # Streamlit app
│   └── bot/                 # Discord bot
└── .env                     # Lưu Token & Config (Quan trọng!)
```

**Bước 1.2: Thiết lập Docker Compose** Tạo file `docker-compose.yml` để chạy Kafka và Zookeeper:

```yaml
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

> **Chạy lệnh:** `docker-compose up -d` và đảm bảo 2 container đang chạy.

---

### 📡 PHASE 2: DATA PIPELINE (ĐƯỜNG ỐNG DỮ LIỆU)

**Mục tiêu:** Thay đổi file `app/data_collector/realtime_collector.py` để bắn dữ liệu vào Kafka.

**Bước 2.1: Cài thư viện**

```bash
pip install confluent-kafka python-dotenv
```

**Bước 2.2: Viết Kafka Producer (`app/producers/market_data_producer.py`)** Thay vì lưu file, hãy gửi JSON vào topic `crypto.market_data`.

```python
import json
import time
from confluent_kafka import Producer
# Import code lấy data Binance cũ từ project của bạn

def delivery_report(err, msg):
    if err: print(f'Message failed: {err}')

p = Producer({'bootstrap.servers': 'localhost:9092'})

def start_producing():
    while True:
        # 1. Lấy dữ liệu Realtime từ Binance (Code cũ)
        # raw_data = binance_api.get_latest_price("BTCUSDT") 
        
        # 2. Format dữ liệu chuẩn
        message = {
            "symbol": "BTCUSDT",
            "price": 68000.50,
            "volume": 120.5,
            "timestamp": time.time()
        }
        
        # 3. Gửi vào Kafka
        p.produce('crypto.market_data', json.dumps(message).encode('utf-8'), callback=delivery_report)
        p.flush()
        
        time.sleep(1) # Rate limit
```

---

### 🧠 PHASE 3: ML UPGRADE (TRÍ TUỆ)

**Mục tiêu:** Thay thế các model cũ (Linear Reg, KNN) bằng bộ 3 quyền lực: Random Forest, SVM, Logistic Regression.

**Bước 3.1: Train Model mới (`app/ml_training/train_new_models.py`)** Bạn cần train 3 file `.joblib` riêng biệt:

1. **Random Forest:** Dự đoán xu hướng chính (Main Trend).
2. **SVM:** Phân loại tín hiệu mua/bán ở biên độ khó (Support Vector).
3. **Logistic Regression:** Tính xác suất (Probability) để lọc nhiễu.

> **Lưu ý:** Feature Engineering (MA, RSI, Volatility) phải giống hệt nhau ở lúc Train và lúc chạy Real-time.

**Bước 3.2: Tạo ML Prediction Service (`app/consumers/ml_predictor.py`)** Đây là một "Consumer" lắng nghe `crypto.market_data`.

```python
from confluent_kafka import Consumer, Producer
import joblib
import json
import numpy as np

# Load 3 models
rf_model = joblib.load('models/random_forest.joblib')
svm_model = joblib.load('models/svm.joblib')
log_model = joblib.load('models/logreg.joblib')

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'ml_group',
    'auto.offset.reset': 'latest'
})
consumer.subscribe(['crypto.market_data'])

producer = Producer({'bootstrap.servers': 'localhost:9092'})

while True:
    msg = consumer.poll(1.0)
    if msg is None: continue

    data = json.loads(msg.value().decode('utf-8'))
    
    # 1. Tính toán Feature (MA, RSI...) từ data raw nhận được
    features = calculate_features(data) 
    
    # 2. Dự đoán
    trend = rf_model.predict([features])[0]
    prob = log_model.predict_proba([features])[0][1] # Xác suất tăng
    
    # 3. Đóng gói kết quả
    prediction_msg = {
        "timestamp": data['timestamp'],
        "price": data['price'],
        "rf_trend": int(trend), # 1: Up, 0: Down
        "svm_signal": int(svm_model.predict([features])[0]),
        "confidence": float(prob)
    }
    
    # 4. Bắn sang topic tín hiệu
    producer.produce('crypto.ml_signals', json.dumps(prediction_msg).encode('utf-8'))
```

---

### ⚖️ PHASE 4: DECISION ENGINE & DEMO EXCHANGE (QUYẾT ĐỊNH)

**Mục tiêu:** Xử lý vấn đề "Hệ thống ra quyết định tối ưu" và "Sàn ảo demo".

**Bước 4.1: Viết Trading Engine (`app/consumers/trading_engine.py`)** Lắng nghe topic `crypto.ml_signals` và ra quyết định.

```python
# Giả lập ví tiền
wallet = {"USDT": 10000, "BTC": 0}
position = None # 'LONG' or None

def execute_trade(signal_data):
    global position, wallet
    price = signal_data['price']
    
    # LOGIC RA QUYẾT ĐỊNH (Decision System)
    # Mua nếu RF báo Tăng VÀ Độ tin cậy > 70% VÀ SVM đồng thuận
    buy_condition = (signal_data['rf_trend'] == 1) and (signal_data['confidence'] > 0.7)
    
    if buy_condition and position is None:
        # Thực hiện MUA
        amount_btc = wallet['USDT'] / price
        wallet['BTC'] = amount_btc
        wallet['USDT'] = 0
        position = 'LONG'
        print(f"✅ BUY at {price}")
        # Gửi sự kiện Order vào Kafka để Dashboard hiển thị
        send_order_event("BUY", price)

    elif not buy_condition and position == 'LONG':
        # Thực hiện BÁN (Chốt lời/Cắt lỗ)
        # ... logic bán ...
```

---

### 🖥️ PHASE 5: INTERFACE (DASHBOARD & BOT)

**Mục tiêu:** Demo trực quan realtime (Streamlit) và giữ tương tác Discord.

**Bước 5.1: Xây dựng Dashboard (`app/dashboard/app.py`)** Sử dụng Streamlit để visualize dữ liệu từ Kafka. Lưu ý: Streamlit không hỗ trợ Kafka native tốt, nên dùng một biến trung gian (như file cache hoặc deque trong bộ nhớ) để hiển thị.

* Hiển thị biểu đồ nến (Candlestick).
* Hiển thị bảng lệnh vừa khớp (Order Book ảo).
* Hiển thị Metrics: Số dư ví, Lãi/Lỗ hiện tại.

**Bước 5.2: Cập nhật Discord Bot (`app/bot.py`)**

* Giữ lại khung sườn bot cũ.
* Thay đổi logic lệnh `!dudoan` và `!gia`: Thay vì đọc file model hoặc gọi API trực tiếp, Bot sẽ đọc "trạng thái mới nhất" từ hệ thống (có thể lưu state vào Redis hoặc file JSON chung được update bởi Trading Engine).
* **Quan trọng:** Đảm bảo fix lỗi bảo mật Token bằng `.env` như file gốc đã khuyến nghị.

---

### ✅ CHECKLIST KIỂM TRA (Tránh Bug)

1. **Dữ liệu đầu vào:** Kiểm tra xem `crypto.market_data` có nhận được chuỗi liên tục không? Nếu mất kết nối Binance, hệ thống có crash không? -\> *Cần thêm `try-except` ở Producer.*
2. **Đồng bộ Feature:** Hàm `calculate_features` ở Phase 3 (Real-time) phải giống 100% logic lúc Train model. Sai lệch nhỏ cũng làm model dự đoán sai.
3. **Cold Start:** Khi mới bật hệ thống, chưa đủ dữ liệu để tính MA50 (Moving Average 50). Cần chờ đủ 50 điểm dữ liệu rồi mới bắt đầu dự đoán.
