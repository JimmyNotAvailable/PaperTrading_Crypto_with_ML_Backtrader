"""Test consumer that reads from beginning of topic"""
from confluent_kafka import Consumer
import json
import os
from dotenv import load_dotenv

load_dotenv()

conf = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    'group.id': 'test_group_earliest',
    'auto.offset.reset': 'earliest'  # Đọc từ đầu topic
}

consumer = Consumer(conf)
topic = 'crypto.market_data'
consumer.subscribe([topic])

print(f"👀 Reading ALL messages from topic '{topic}'...\n")

try:
    count = 0
    timeout_count = 0
    max_timeout = 5  # Dừng sau 5 lần poll() không có data
    
    while timeout_count < max_timeout:
        msg = consumer.poll(1.0)
        
        if msg is None:
            timeout_count += 1
            print(f"⏳ Waiting... ({timeout_count}/{max_timeout})")
            continue
            
        timeout_count = 0  # Reset counter khi có message
        
        if msg.error():
            print(f"❌ Error: {msg.error()}")
            continue

        # Decode message
        data = json.loads(msg.value().decode('utf-8'))
        count += 1
        print(f"📥 [{count}] {data['symbol']} | Price: ${data['close']:,.2f} | Vol: {data['volume']:,.0f} | Time: {data['timestamp']}")
        
    print(f"\n✅ Total messages received: {count}")
    
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
finally:
    consumer.close()
    print("🛑 Consumer closed")
