"""
Phase 3 Integration Test Script
================================
Tests complete ML pipeline:
Producer → Kafka → ML Consumer → Kafka → Debug Consumer

This script sends 60 messages (enough for SMA_50 calculation)
"""
import sys
import time
sys.path.insert(0, '.')

from app.producers.market_data_producer import CryptoProducer

print("🚀 Phase 3 Integration Test")
print("📡 Sending 60 messages to trigger ML predictions...\n")

producer = CryptoProducer(symbol='BTC/USDT', timeframe='1m')

try:
    for i in range(60):
        # Fetch once
        candles = producer.exchange.fetch_ohlcv(
            producer.symbol, 
            timeframe=producer.timeframe, 
            limit=1
        )
        
        if not candles:
            print(f"⚠️ No data (attempt {i+1}/60)")
            time.sleep(2)
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
        
        # Progress indicator
        if i < 52:
            status = f"[Buffering {i+1}/52]"
        else:
            status = f"[Predicting {i-51}/{60-52}]"
        
        print(f"✅ {status} Sent: {payload['symbol']} | ${payload['close']:,.2f}")
        time.sleep(1)  # Slower to see predictions in real-time
        
    producer.producer.flush()
    print("\n✅ Test completed!")
    print("📊 Check ML Consumer terminal for predictions")
    print("📊 Check Debug Consumer terminal for ML signals")
    
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
    producer.close()
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
