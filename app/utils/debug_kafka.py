from confluent_kafka import Consumer
import json
import os
from dotenv import load_dotenv

load_dotenv()

def start_debug_consumer() -> None:
    conf = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': 'debug_group_01',
        'auto.offset.reset': 'latest'  # Chỉ đọc dữ liệu mới nhất
    }

    consumer = Consumer(conf)
    topic = 'crypto.market_data'
    consumer.subscribe([topic])

    print(f"👀 Đang lắng nghe topic '{topic}'... (Nhấn Ctrl+C để dừng)")

    try:
        while True:
            msg = consumer.poll(1.0)  # Chờ 1s
            if msg is None: 
                continue
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
