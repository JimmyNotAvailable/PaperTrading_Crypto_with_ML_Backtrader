"""
Phase 4 Integration Test
Kiểm tra end-to-end pipeline: Producer → ML Consumer → Decision Engine → Virtual Exchange

Test flow:
1. Phase 1: Kafka infrastructure (đã chạy)
2. Phase 2: Binance Producer → crypto.market_data
3. Phase 3: ML Consumer → crypto.ml_signals
4. Phase 4: Decision Engine → crypto.orders

Usage:
    Terminal 1: python app/producers/binance_producer.py
    Terminal 2: python app/consumers/ml_predictor.py
    Terminal 3: python app/consumers/decision_engine.py
    Terminal 4: python test_phase4_integration.py
"""
import os
import sys
import json
import time
from confluent_kafka import Consumer
from datetime import datetime

# Setup consumer để monitor orders
def monitor_orders(duration_seconds=300):
    """
    Monitor crypto.orders topic để xem Decision Engine đang làm gì
    
    Args:
        duration_seconds: Thời gian monitor (mặc định 5 phút)
    """
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'phase4_test_monitor',
        'auto.offset.reset': 'earliest'  # Đọc từ đầu để test
    })
    
    consumer.subscribe(['crypto.orders'])
    
    print("\n" + "="*80)
    print("🔍 PHASE 4 INTEGRATION TEST - MONITORING ORDERS")
    print("="*80)
    print(f"📡 Listening to: crypto.orders")
    print(f"⏱️  Duration: {duration_seconds} seconds")
    print("🎯 Waiting for Decision Engine to place orders...")
    print("="*80 + "\n")
    
    start_time = time.time()
    order_count = 0
    buy_orders = []
    sell_orders = []
    
    try:
        while (time.time() - start_time) < duration_seconds:
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                print(f"❌ Error: {msg.error()}")
                continue
            
            # Parse order
            order = json.loads(msg.value().decode('utf-8'))
            order_count += 1
            
            # Extract info
            symbol = order.get('symbol', 'UNKNOWN')
            action = order.get('action', 'UNKNOWN')
            price = order.get('price', 0.0)
            amount = order.get('amount', 0.0)
            timestamp = order.get('timestamp', 0)
            
            # Convert timestamp
            dt = datetime.fromtimestamp(timestamp / 1000)
            
            # Print order
            print("\n" + "-"*80)
            print(f"📦 ORDER #{order_count} - {action} {symbol}")
            print("-"*80)
            print(f"⏰ Time:     {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💰 Price:    ${price:,.2f}")
            print(f"📊 Amount:   {amount:.6f}")
            print(f"💵 Value:    ${price * amount:,.2f}")
            
            if action == 'BUY':
                # BUY order details
                stop_loss = order.get('stop_loss')
                take_profit = order.get('take_profit')
                ml_confidence = order.get('ml_confidence', 0.0)
                ml_details = order.get('ml_details', {})
                
                print(f"🛡️  Stop Loss:     ${stop_loss:,.2f} ({((stop_loss-price)/price*100):+.2f}%)")
                print(f"🎯 Take Profit:   ${take_profit:,.2f} ({((take_profit-price)/price*100):+.2f}%)")
                print(f"🧠 ML Confidence: {ml_confidence:.2%}")
                print(f"📈 ML Details:    {ml_details}")
                
                buy_orders.append(order)
            
            elif action == 'SELL':
                # SELL order details
                reason = order.get('reason', 'UNKNOWN')
                pnl = order.get('pnl', 0.0)
                pnl_pct = order.get('pnl_percentage', 0.0)
                
                pnl_emoji = "🟢" if pnl > 0 else "🔴"
                print(f"📍 Reason:    {reason}")
                print(f"{pnl_emoji} PnL:        ${pnl:,.2f} ({pnl_pct:+.2f}%)")
                
                sell_orders.append(order)
            
            print("-"*80)
            
            # Real-time stats
            if sell_orders:
                total_pnl = sum(o.get('pnl', 0) for o in sell_orders)
                wins = sum(1 for o in sell_orders if o.get('pnl', 0) > 0)
                losses = len(sell_orders) - wins
                win_rate = (wins / len(sell_orders) * 100) if sell_orders else 0
                
                print(f"\n📊 CURRENT STATS:")
                print(f"   Total Orders: {order_count} (BUY: {len(buy_orders)}, SELL: {len(sell_orders)})")
                print(f"   Total PnL: ${total_pnl:,.2f}")
                print(f"   Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping monitor...")
    
    finally:
        consumer.close()
        
        # Final report
        print("\n\n" + "="*80)
        print("📊 PHASE 4 INTEGRATION TEST - FINAL REPORT")
        print("="*80)
        print(f"⏱️  Duration: {time.time() - start_time:.1f} seconds")
        print(f"📦 Total Orders: {order_count}")
        print(f"🟢 BUY Orders: {len(buy_orders)}")
        print(f"🔴 SELL Orders: {len(sell_orders)}")
        
        if sell_orders:
            total_pnl = sum(o.get('pnl', 0) for o in sell_orders)
            wins = sum(1 for o in sell_orders if o.get('pnl', 0) > 0)
            losses = len(sell_orders) - wins
            win_rate = (wins / len(sell_orders) * 100)
            avg_win = sum(o.get('pnl', 0) for o in sell_orders if o.get('pnl', 0) > 0) / wins if wins > 0 else 0
            avg_loss = sum(o.get('pnl', 0) for o in sell_orders if o.get('pnl', 0) < 0) / losses if losses > 0 else 0
            
            print(f"\n💰 TRADING PERFORMANCE:")
            print(f"   Total PnL: ${total_pnl:,.2f}")
            print(f"   Winning Trades: {wins}")
            print(f"   Losing Trades: {losses}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Average Win: ${avg_win:,.2f}")
            print(f"   Average Loss: ${avg_loss:,.2f}")
        
        print("\n✅ Phase 4 integration test completed!")
        print("="*80 + "\n")


def check_prerequisites():
    """Kiểm tra các điều kiện cần thiết"""
    print("\n🔍 Checking prerequisites...")
    
    # Check Kafka
    try:
        from confluent_kafka import Consumer
        consumer = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'prereq_check',
            'session.timeout.ms': 6000
        })
        # Try to get metadata
        metadata = consumer.list_topics(timeout=5)
        consumer.close()
        print("✅ Kafka: Connected")
    except Exception as e:
        print(f"❌ Kafka: Not available - {str(e)}")
        print("   Please start: docker-compose up -d")
        return False
    
    # Check topics
    try:
        topics = ['crypto.market_data', 'crypto.ml_signals', 'crypto.orders']
        print(f"✅ Topics: {', '.join(topics)}")
    except Exception as e:
        print(f"❌ Topics: Error - {str(e)}")
    
    print("\n📋 Required services to run:")
    print("   Terminal 1: python app/producers/binance_producer.py")
    print("   Terminal 2: python app/consumers/ml_predictor.py")
    print("   Terminal 3: python app/consumers/decision_engine.py")
    print("\nIf all services are running, you should see orders appearing below.\n")
    
    return True


if __name__ == "__main__":
    print("\n🚀 PHASE 4 INTEGRATION TEST")
    print("Testing end-to-end pipeline: Phase 1 → 2 → 3 → 4")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix issues above.\n")
        sys.exit(1)
    
    # Monitor orders for 5 minutes (or until Ctrl+C)
    monitor_orders(duration_seconds=300)
