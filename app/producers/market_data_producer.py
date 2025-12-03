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
    def __init__(self, symbol: str = 'BTC/USDT', timeframe: str = '1m') -> None:
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

    def fetch_and_produce(self) -> None:
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
                    'symbol': self.symbol.replace('/', ''),  # Format lại thành BTCUSDT
                    'timestamp': candle[0],                  # Unix timestamp (ms)
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

    def close(self) -> None:
        self.producer.flush()  # Đẩy nốt các tin nhắn còn kẹt trong hàng đợi đi
        logger.info("🛑 Producer đã dừng.")

if __name__ == "__main__":
    # Chạy thử Producer
    bot_producer = CryptoProducer(symbol='BTC/USDT', timeframe='1m')
    try:
        bot_producer.fetch_and_produce()
    except KeyboardInterrupt:
        bot_producer.close()
