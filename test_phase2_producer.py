"""Quick test script for Phase 2 Producer"""
import sys
import time
sys.path.insert(0, '.')

from app.producers.market_data_producer import CryptoProducer

print("🚀 Starting Phase 2 Producer Test...")
print("📡 Will send 5 messages then stop\n")

producer = CryptoProducer(symbol='BTC/USDT', timeframe='1m')

try:
    for i in range(5):
        # Fetch once
        candles = producer.exchange.fetch_ohlcv(producer.symbol, timeframe=producer.timeframe, limit=1)
        
        if not candles:
            print(f"⚠️ No data received (attempt {i+1}/5)")
            continue
            
        candle = candles[0]
        payload = {
            'symbol': producer.symbol.replace('/', ''),
            'timestamp': candle[0],
            'open': candle[1],
            'high': candle[2],
            'low': candle[3],
            'close': candle[4],
            'volume': candle[5],
            'source': 'binance'
        }
        
        import json
        key = producer.symbol.encode('utf-8')
        value = json.dumps(payload).encode('utf-8')
        
        producer.producer.produce(
            producer.topic,
            key=key,
            value=value,
            callback=producer.delivery_report
        )
        producer.producer.poll(0)
        
        print(f"✅ [{i+1}/5] Sent: {payload['symbol']} | Price: ${payload['close']:,.2f}")
        time.sleep(2)
        
    producer.producer.flush()
    print("\n✅ Test completed! Check debug_kafka.py terminal for received messages.")
    
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
    producer.close()
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
