Chào bạn, chúng ta sẽ tiếp tục bước sang **Phase 2: Xây Dựng Data Pipeline (Đường Ống Dữ Liệu)**.

Ở Phase 1, bạn đã dựng xong "đường cao tốc" (Kafka). Nhiệm vụ của Phase 2 là chế tạo "xe tải" (Producer) để vận chuyển dữ liệu từ Binance vào đường cao tốc đó một cách liên tục, ổn định và tốc độ cao.

Dưới đây là hướng dẫn chi tiết, đã được tối ưu hóa để khắc phục các nhược điểm của code cũ (như việc xử lý file rườm rà).

-----

### 📋 MỤC TIÊU PHASE 2

1.  **Thu thập dữ liệu Real-time:** Lấy giá (OHLCV - Open, High, Low, Close, Volume) từ Binance API.
2.  **Chuẩn hóa dữ liệu:** Đóng gói thành bản tin JSON chuẩn.
3.  **Phát luồng (Producing):** Bắn dữ liệu vào Kafka Topic `crypto.market_data`.
4.  **Tính ổn định:** Tự động khôi phục nếu mất kết nối mạng hoặc API lỗi (Retry Mechanism).

-----

### 🛠️ BƯỚC 1: CÀI ĐẶT THƯ VIỆN CHUYÊN DỤNG

Thay vì dùng `requests` và tự parse JSON thủ công như dự án cũ, chúng ta sẽ dùng **CCXT**. Đây là thư viện chuẩn công nghiệp cho Crypto Trading, hỗ trợ xử lý lỗi mạng và chuẩn hóa dữ liệu cực tốt.

**Hành động:** Cập nhật file `requirements.txt` và cài đặt thêm:

```text
ccxt==4.1.0  # Thư viện giao tiếp sàn Crypto tối ưu
```

Chạy lệnh cài đặt:

```bash
pip install -r requirements.txt
```

-----

### 🏭 BƯỚC 2: VIẾT KAFKA PRODUCER (XE TẢI DỮ LIỆU)

Chúng ta sẽ viết một Class chuyên biệt để quản lý việc này. Code được thiết kế theo hướng đối tượng (OOP) để dễ mở rộng.

**Tạo file:** `app/producers/market_data_producer.py`

```python
import json
import time
import os
import ccxt
import logging
from confluent_kafka import Producer
from dotenv import load_dotenv

# Setup Logging (Thay vì print đơn thuần, dùng logging để debug tốt hơn)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load biến môi trường
load_dotenv()

class CryptoProducer:
    def __init__(self, symbol='BTC/USDT', timeframe='1m'):
        """
        Khởi tạo Producer
        :param symbol: Cặp coin cần lấy (VD: BTC/USDT)
        :param timeframe: Khung thời gian (1m, 5m, 1h)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        
        # 1. Khởi tạo Kafka Producer
        kafka_conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'client.id': 'crypto-producer-01',
            'retries': 5  # Tự động thử lại nếu gửi lỗi
        }
        self.producer = Producer(kafka_conf)
        self.topic = 'crypto.market_data'

        # 2. Khởi tạo kết nối Binance qua CCXT (Không cần API Key cho Public Data)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,  # Tự động delay để không bị sàn ban IP
            'options': {'defaultType': 'spot'}
        })

    def delivery_report(self, err, msg):
        """Callback xác nhận tin nhắn đã gửi thành công hay chưa"""
        if err is not None:
            logger.error(f'❌ Gửi thất bại: {err}')
        else:
            # Chỉ log debug để tránh spam console
            logger.debug(f'✅ Đã gửi data {msg.key().decode("utf-8")} vào {msg.topic()}')

    def fetch_and_produce(self):
        """Hàm chính: Lấy data và bắn vào Kafka"""
        logger.info(f"🚀 Bắt đầu thu thập dữ liệu {self.symbol}...")
        
        while True:
            try:
                # 1. Lấy nến mới nhất (fetch_ohlcv trả về list các nến)
                # limit=1: Chỉ lấy nến mới nhất
                candles = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=1)
                
                if not candles:
                    logger.warning("⚠️ Không lấy được dữ liệu từ sàn, thử lại sau 3s...")
                    time.sleep(3)
                    continue

                # Cấu trúc nến từ CCXT: [timestamp, open, high, low, close, volume]
                candle = candles[0]
                
                # 2. Đóng gói JSON payload
                payload = {
                    'symbol': self.symbol.replace('/', ''), # Format lại thành BTCUSDT
                    'timestamp': candle[0],                 # Unix timestamp (ms)
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5],
                    'source': 'binance'
                }

                # 3. Serialize (Chuyển thành chuỗi bytes)
                key = self.symbol.encode('utf-8')
                value = json.dumps(payload).encode('utf-8')

                # 4. Gửi vào Kafka (Non-blocking)
                self.producer.produce(
                    self.topic, 
                    key=key, 
                    value=value, 
                    callback=self.delivery_report
                )
                
                # Quan trọng: Gọi poll để trigger callback (xác nhận đã gửi)
                self.producer.poll(0)

                logger.info(f"📡 Sent: {payload['symbol']} | Price: {payload['close']}")

                # 5. Chờ đến nến tiếp theo hoặc sleep ngắn
                # Với nến 1m, ta có thể sleep 2s để cập nhật giá close liên tục (như ticker)
                # Hoặc sleep 60s nếu chỉ quan tâm giá chốt nến. 
                # Ở đây ta sleep 5s để mô phỏng real-time vừa phải.
                time.sleep(5)

            except ccxt.NetworkError as e:
                logger.error(f"🌐 Lỗi mạng: {e} - Thử lại sau 5s")
                time.sleep(5)
            except Exception as e:
                logger.error(f"🔥 Lỗi không xác định: {e}")
                time.sleep(5)

    def close(self):
        self.producer.flush() # Đẩy nốt các tin nhắn còn kẹt trong hàng đợi đi
        logger.info("🛑 Producer đã dừng.")

if __name__ == "__main__":
    # Chạy thử Producer
    bot_producer = CryptoProducer(symbol='BTC/USDT', timeframe='1m')
    try:
        bot_producer.fetch_and_produce()
    except KeyboardInterrupt:
        bot_producer.close()
```

-----

### 🔍 BƯỚC 3: KIỂM TRA DỮ LIỆU (DEBUG CONSUMER)

Trước khi sang Phase 3 (Train AI), ta phải chắc chắn dữ liệu đã vào được Kafka. Đừng tin tưởng mù quáng, hãy kiểm chứng ("Trust but Verify").

**Tạo file:** `app/utils/debug_kafka.py`

```python
from confluent_kafka import Consumer
import json
import os
from dotenv import load_dotenv

load_dotenv()

def start_debug_consumer():
    conf = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': 'debug_group_01',
        'auto.offset.reset': 'latest' # Chỉ đọc dữ liệu mới nhất
    }

    consumer = Consumer(conf)
    topic = 'crypto.market_data'
    consumer.subscribe([topic])

    print(f"👀 Đang lắng nghe topic '{topic}'... (Nhấn Ctrl+C để dừng)")

    try:
        while True:
            msg = consumer.poll(1.0) # Chờ 1s
            if msg is None: continue
            if msg.error():
                print(f"Lỗi: {msg.error()}")
                continue

            # Giải mã message
            data = json.loads(msg.value().decode('utf-8'))
            print(f"📥 Đã nhận: {data['symbol']} | Giá: {data['close']} | Vol: {data['volume']}")

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

if __name__ == "__main__":
    start_debug_consumer()
```

-----

### 🚀 BƯỚC 4: VẬN HÀNH PHASE 2

Bây giờ hãy kết hợp mọi thứ lại:

1.  **Bật Hạ Tầng (Nếu chưa bật):**

    ```bash
    docker-compose up -d
    ```

2.  **Mở Terminal 1 (Chạy Producer):**

    ```bash
    python app/producers/market_data_producer.py
    ```

    *Kỳ vọng:* Bạn sẽ thấy log `📡 Sent: BTCUSDT | Price: 68xxx...` xuất hiện đều đặn mỗi 5 giây.

3.  **Mở Terminal 2 (Chạy Debugger):**

    ```bash
    python app/utils/debug_kafka.py
    ```

    *Kỳ vọng:* Bạn sẽ thấy log `📥 Đã nhận...` ngay lập tức sau khi Terminal 1 gửi tin.

-----

### 💡 TẠI SAO TỐI ƯU HƠN CODE CŨ?

1.  **Không tính toán Features ở đây:** Trong code cũ, `realtime_collector` vừa lấy giá vừa tính MA10, MA50. Điều này làm Producer bị chậm. Ở đây, Producer chỉ làm đúng 1 việc: **Lấy RAW DATA**. Việc tính toán (MA, RSI, Bollinger Bands) sẽ do Consumer của Phase 3 làm. Điều này giúp hệ thống linh hoạt (muốn đổi công thức tính MA cũng không cần tắt Producer).
2.  **Cơ chế `ccxt.enableRateLimit`:** Giúp bạn không bao giờ bị Binance chặn IP vì gửi request quá nhanh (lỗi 429).
3.  **JSON Serialization:** Dữ liệu được chuẩn hóa JSON ngay từ đầu, giúp Consumer ở Phase 3 (Machine Learning) đọc vào là dùng được ngay, không cần parse lại string.

Sau khi bạn xác nhận Phase 2 chạy ổn (Terminal 2 nhận được dữ liệu), chúng ta sẽ bước sang **Phase 3: Nâng cấp trí tuệ nhân tạo (Machine Learning)** để tiêu thụ dữ liệu này. Bạn đã sẵn sàng chưa?