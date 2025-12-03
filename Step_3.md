Tuyệt vời\! Việc Phase 1 (Hạ tầng Kafka) và Phase 2 (Thu thập dữ liệu) đã vượt qua bài test là cột mốc quan trọng. Hệ thống của bạn hiện đã có "Mạch máu" (Kafka) và "Tim" (Producer).

Bây giờ chúng ta sẽ xây dựng "Bộ não" (Brain) trong **Phase 3: Machine Learning & Real-time Prediction**.

Đây là giai đoạn phức tạp nhất vì nó chứa đựng logic toán học. Mục tiêu là thay thế các thuật toán Linear Regression/KNN đơn giản cũ bằng bộ 3 mạnh mẽ hơn: **Random Forest, SVM, Logistic Regression**, đồng thời khắc phục vấn đề *Data Leakage* (rò rỉ dữ liệu) và *Cold Start* (thiếu dữ liệu đầu vào).

-----

### 📋 MỤC TIÊU PHASE 3

1.  **Feature Engineering đồng bộ:** Đảm bảo cách tính chỉ báo (RSI, MACD, MA) lúc Training và lúc chạy Real-time là *giống hệt nhau* (tránh sai số logic).
2.  **Huấn luyện (Training):** Tải dữ liệu lịch sử và train 3 model mới, lưu ra file `.joblib`.
3.  **Dự đoán Real-time (Consumer):** Lắng nghe dữ liệu từng giây từ Kafka -\> Tích lũy đủ nến -\> Dự đoán -\> Bắn tín hiệu ra Kafka.

-----

### 🛠️ BƯỚC 1: CÀI ĐẶT THƯ VIỆN ML

Cập nhật `requirements.txt` để thêm các thư viện toán học và kỹ thuật:

```text
scikit-learn==1.3.0
pandas_ta==0.3.14b  # Thư viện tính chỉ báo kỹ thuật chuẩn xác
joblib==1.3.2
```

Chạy lệnh: `pip install -r requirements.txt`

-----

### 🧠 BƯỚC 2: TẠO MODULE FEATURE ENGINEERING (QUAN TRỌNG NHẤT)

**Vấn đề:** Trong dự án cũ, code xử lý dữ liệu nằm rải rác.
**Giải pháp:** Tạo một file dùng chung `app/ml/feature_engineering.py`. File này sẽ được gọi bởi cả *script training* và *consumer real-time*.

```python
import pandas as pd
import pandas_ta as ta

def calculate_features(df: pd.DataFrame):
    """
    Hàm tính toán chỉ báo kỹ thuật.
    Input: DataFrame chứa OHLCV (Open, High, Low, Close, Volume)
    Output: DataFrame đã có thêm các cột features (RSI, SMA, v.v.)
    """
    df = df.copy()
    
    # 1. Trend Indicators
    df['SMA_10'] = ta.sma(df['close'], length=10)
    df['SMA_50'] = ta.sma(df['close'], length=50)
    
    # 2. Momentum Indicators
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    
    # 3. Volatility (Biến động)
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20)
    if bb is not None:
        df['BB_UPPER'] = bb['BBU_20_2.0']
        df['BB_LOWER'] = bb['BBL_20_2.0']
    
    # 4. Target (Chỉ dùng cho training, Realtime sẽ bỏ qua dòng này)
    # Target: 1 nếu giá đóng cửa sau 1 nến tăng, 0 nếu giảm
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # Xóa các dòng NaN do tính toán chỉ báo (ví dụ 50 dòng đầu tiên của SMA_50)
    df.dropna(inplace=True)
    
    return df
```

-----

### 🎓 BƯỚC 3: HUẤN LUYỆN MÔ HÌNH (TRAINING)

Chúng ta sẽ viết script tự động tải dữ liệu lịch sử từ Binance về để train, thay vì phụ thuộc vào file CSV cũ.

**Tạo file:** `app/ml/train_models.py`

```python
import ccxt
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from feature_engineering import calculate_features

# Tạo thư mục lưu model nếu chưa có
os.makedirs('app/ml/models', exist_ok=True)

def fetch_historical_data(symbol='BTC/USDT', limit=1000):
    print(f"📥 Đang tải {limit} nến quá khứ của {symbol}...")
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def train():
    # 1. Chuẩn bị dữ liệu
    df = fetch_historical_data()
    df = calculate_features(df)
    
    # Chọn Features (X) và Target (y)
    features = ['close', 'volume', 'SMA_10', 'SMA_50', 'RSI_14']
    X = df[features]
    y = df['target']
    
    # Chia tập Train/Test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print(f"📊 Dữ liệu training: {len(X_train)} mẫu")

    # 2. Train Random Forest (Model chính bắt Trend)
    print("🧠 Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)
    print(f"   Accuracy RF: {accuracy_score(y_test, rf.predict(X_test)):.2f}")
    
    # 3. Train SVM (Phân loại biên độ khó)
    print("🧠 Training SVM...")
    svm = SVC(probability=True, kernel='rbf') # probability=True để lấy độ tin cậy
    svm.fit(X_train, y_train)
    print(f"   Accuracy SVM: {accuracy_score(y_test, svm.predict(X_test)):.2f}")

    # 4. Train Logistic Regression (Xác suất nền)
    print("🧠 Training Logistic Regression...")
    lr = LogisticRegression()
    lr.fit(X_train, y_train)
    print(f"   Accuracy LR: {accuracy_score(y_test, lr.predict(X_test)):.2f}")

    # 5. Lưu models
    joblib.dump(rf, 'app/ml/models/rf_model.joblib')
    joblib.dump(svm, 'app/ml/models/svm_model.joblib')
    joblib.dump(lr, 'app/ml/models/lr_model.joblib')
    print("✅ Đã lưu 3 models vào thư mục app/ml/models/")

if __name__ == "__main__":
    train()
```

> **Hành động:** Chạy `python app/ml/train_models.py` để tạo ra 3 file model `.joblib`.

-----

### 🔮 BƯỚC 4: XÂY DỰNG ML CONSUMER (REAL-TIME PREDICTOR)

Đây là phần khó nhất: Consumer nhận từng nến rời rạc, nhưng ML cần một chuỗi nến (Series) để tính SMA\_50.
**Giải pháp:** Dùng một bộ nhớ đệm (Buffer) để lưu 50-60 nến gần nhất.

**Tạo file:** `app/consumers/ml_predictor.py`

```python
import json
import os
import joblib
import pandas as pd
import numpy as np
from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv

# Import hàm tính feature dùng chung (để logic giống hệt lúc train)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml'))
from feature_engineering import calculate_features

load_dotenv()

class MLPredictor:
    def __init__(self):
        # Config Kafka
        self.consumer = Consumer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'group.id': 'ml_predictor_group',
            'auto.offset.reset': 'latest'
        })
        self.producer = Producer({'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS')})
        
        self.consumer.subscribe(['crypto.market_data'])
        self.produce_topic = 'crypto.ml_signals'

        # Load Models
        print("⏳ Loading models...")
        self.rf = joblib.load('app/ml/models/rf_model.joblib')
        self.svm = joblib.load('app/ml/models/svm_model.joblib')
        self.lr = joblib.load('app/ml/models/lr_model.joblib')
        
        # Buffer: Cần ít nhất 50 nến để tính SMA_50
        self.data_buffer = [] 
        self.min_required_data = 52 

    def predict(self, current_data):
        # 1. Thêm dữ liệu mới vào buffer
        self.data_buffer.append(current_data)
        
        # Giữ buffer không quá dài (chỉ cần 100 nến gần nhất là đủ tính toán)
        if len(self.data_buffer) > 100:
            self.data_buffer.pop(0)
            
        # 2. Kiểm tra Cold Start (Chưa đủ dữ liệu thì chưa dự đoán)
        if len(self.data_buffer) < self.min_required_data:
            print(f"⏳ Đang tích lũy dữ liệu: {len(self.data_buffer)}/{self.min_required_data}")
            return

        # 3. Tạo DataFrame từ buffer để tính feature
        df = pd.DataFrame(self.data_buffer)
        df = calculate_features(df) # Hàm này sẽ trả về DataFrame đã có cột SMA, RSI...
        
        # Lấy dòng cuối cùng (mới nhất) để dự đoán
        last_row = df.iloc[[-1]][['close', 'volume', 'SMA_10', 'SMA_50', 'RSI_14']]
        
        # 4. Dự đoán bằng 3 models
        rf_pred = self.rf.predict(last_row)[0]
        svm_pred = self.svm.predict(last_row)[0]
        lr_prob = self.lr.predict_proba(last_row)[0][1] # Xác suất tăng giá
        
        # 5. Tổng hợp tín hiệu (Ensemble Logic)
        signal = "NEUTRAL"
        if rf_pred == 1 and svm_pred == 1 and lr_prob > 0.6:
            signal = "BUY"
        elif rf_pred == 0 and svm_pred == 0 and lr_prob < 0.4:
            signal = "SELL"
            
        # 6. Gửi kết quả vào Kafka
        result = {
            "timestamp": current_data['timestamp'],
            "price": current_data['close'],
            "signal": signal,
            "details": {
                "rf": int(rf_pred),
                "svm": int(svm_pred),
                "confidence": float(round(lr_prob, 4))
            }
        }
        
        self.producer.produce(self.produce_topic, json.dumps(result).encode('utf-8'))
        self.producer.flush()
        print(f"🔮 Prediction: {signal} | Price: {current_data['close']} | Conf: {lr_prob:.2f}")

    def start(self):
        print("🚀 ML Predictor Service Started...")
        try:
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None: continue
                
                data = json.loads(msg.value().decode('utf-8'))
                self.predict(data)
                
        except KeyboardInterrupt:
            self.consumer.close()

if __name__ == "__main__":
    service = MLPredictor()
    service.start()
```

-----

### ✅ BƯỚC 5: KIỂM TRA TOÀN BỘ HỆ THỐNG (INTEGRATION TEST)

Bây giờ bạn sẽ chạy thử cả 3 Phase kết hợp lại. Hãy mở 3 cửa sổ Terminal (hoặc tab).

**Terminal 1: Hạ tầng (Phase 1)**

```bash
docker-compose up -d
```

*Check:* Đảm bảo Kafka và Zookeeper đang chạy.

**Terminal 2: Producer (Phase 2)**

```bash
python app/producers/market_data_producer.py
```

*Check:* Thấy log `📡 Sent: BTCUSDT...`

**Terminal 3: ML Predictor (Phase 3)**
Đầu tiên, hãy nhớ chạy train model trước (chỉ làm 1 lần):

```bash
python app/ml/train_models.py
```

Sau đó chạy Service dự đoán:

```bash
python app/consumers/ml_predictor.py
```

-----

### 🔎 QUAN SÁT KẾT QUẢ TEST

Khi Terminal 3 chạy:

1.  **Lúc đầu:** Bạn sẽ thấy thông báo `⏳ Đang tích lũy dữ liệu: 1/52`, `2/52`... Do cần đủ 50 nến mới tính được SMA\_50.
2.  **Sau khoảng vài phút:** Khi đủ dữ liệu, bạn sẽ thấy:
    ```text
    🔮 Prediction: NEUTRAL | Price: 68120 | Conf: 0.51
    🔮 Prediction: BUY | Price: 68150 | Conf: 0.75
    ```

**Debug:** Bạn có thể mở thêm Terminal 4 chạy file `debug_kafka.py` (ở Phase 2) nhưng sửa topic thành `crypto.ml_signals` để xem đầu ra JSON cuối cùng mà Dashboard sẽ nhận được.

### 💡 TẠI SAO CÁCH NÀY TỐI ƯU?

  * **Ensemble Learning:** Thay vì tin 1 model, ta kết hợp RF (Trend), SVM (Boundary) và LR (Probability). Chỉ khi cả 3 đồng thuận (`BUY`), rủi ro mới thấp nhất.
  * **Tránh Data Leakage:** Việc tách file `feature_engineering.py` đảm bảo logic tính toán là nhất quán tuyệt đối.
  * **Khắc phục Cold Start:** Cơ chế Buffer đảm bảo không bị lỗi tính toán khi mới khởi động hệ thống.

Phase 3 hoàn tất sẽ cho bạn dòng dữ liệu `crypto.ml_signals` cực kỳ giá trị. Phase tiếp theo chúng ta chỉ việc hiển thị nó lên Dashboard và khớp lệnh ảo\!