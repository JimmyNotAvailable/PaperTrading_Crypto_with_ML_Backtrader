"""Debug Consumer for ML Signals Topic"""
from confluent_kafka import Consumer
import json
import os
from dotenv import load_dotenv

load_dotenv()

def start_debug_ml_signals():
    conf = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': 'debug_ml_signals_group',
        'auto.offset.reset': 'earliest'  # Read from beginning to see all signals
    }

    consumer = Consumer(conf)
    topic = 'crypto.ml_signals'
    consumer.subscribe([topic])

    print(f"👀 Listening to topic '{topic}'... (Press Ctrl+C to stop)\n")
    print("=" * 80)

    try:
        count = 0
        while True:
            msg = consumer.poll(1.0)
            if msg is None: 
                continue
            if msg.error():
                print(f"❌ Error: {msg.error()}")
                continue

            # Decode ML signal
            data = json.loads(msg.value().decode('utf-8'))
            count += 1
            
            # Pretty print signal
            signal = data['signal']
            signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            
            print(f"{signal_emoji} [{count}] {signal} Signal")
            print(f"   Symbol: {data['symbol']}")
            print(f"   Price: ${data['price']:,.2f}")
            print(f"   Timestamp: {data['timestamp']}")
            print(f"   Models: RF={data['details']['random_forest']}, "
                  f"SVM={data['details']['svm']}, "
                  f"Confidence={data['details']['lr_confidence']:.2%}")
            
            if 'features' in data:
                print(f"   Features: SMA_10=${data['features']['sma_10']:.2f}, "
                      f"SMA_50=${data['features']['sma_50']:.2f}, "
                      f"RSI={data['features']['rsi_14']:.1f}")
            
            print("-" * 80)

    except KeyboardInterrupt:
        print(f"\n⚠️ Interrupted. Total signals received: {count}")
    finally:
        consumer.close()
        print("🛑 Consumer closed")

if __name__ == "__main__":
    start_debug_ml_signals()
