"""
Quick Demo - Phase 4 Decision Engine
Script nhanh để demo Phase 4 với dữ liệu giả lập

Không cần chạy Producer/ML Consumer thật, script này sẽ:
1. Tạo fake ML signals
2. Gửi vào crypto.ml_signals
3. Decision Engine sẽ nhận và xử lý
4. Xem kết quả trong crypto.orders

Usage:
    Terminal 1: python demo_phase4.py --send-signals
    Terminal 2: python app/consumers/decision_engine.py
    Terminal 3: python test_phase4_integration.py
"""
import os
import sys
import json
import time
import random
from datetime import datetime
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()


class FakeMLSignalGenerator:
    """Generate fake ML signals để test Decision Engine"""
    
    def __init__(self, kafka_bootstrap='localhost:9092'):
        self.producer = Producer({'bootstrap.servers': kafka_bootstrap})
        self.topic = 'crypto.ml_signals'
        
        # Giá hiện tại giả lập
        self.current_prices = {
            'BTCUSDT': 68000.0,
            'ETHUSDT': 3500.0,
            'SOLUSDT': 145.0,
            'BNBUSDT': 620.0,
            'XRPUSDT': 0.65
        }
        
        # Trend giả lập (để tạo signals hợp lý)
        self.trends = {
            'BTCUSDT': 'up',
            'ETHUSDT': 'up',
            'SOLUSDT': 'down',
            'BNBUSDT': 'up',
            'XRPUSDT': 'down'
        }
    
    def update_price(self, symbol):
        """Cập nhật giá theo trend"""
        trend = self.trends[symbol]
        
        # Random walk với bias theo trend
        if trend == 'up':
            change = random.uniform(-0.002, 0.005)  # Bias tăng
        else:
            change = random.uniform(-0.005, 0.002)  # Bias giảm
        
        self.current_prices[symbol] *= (1 + change)
        return self.current_prices[symbol]
    
    def generate_signal(self, symbol):
        """
        Tạo ML signal giả lập
        
        Logic:
        - Trend up → 70% BUY, 20% NEUTRAL, 10% SELL
        - Trend down → 70% SELL, 20% NEUTRAL, 10% BUY
        """
        trend = self.trends[symbol]
        price = self.update_price(symbol)
        
        # Random signal theo trend
        rand = random.random()
        
        if trend == 'up':
            if rand < 0.70:
                signal = 'BUY'
                confidence = random.uniform(0.60, 0.90)
            elif rand < 0.90:
                signal = 'NEUTRAL'
                confidence = random.uniform(0.40, 0.60)
            else:
                signal = 'SELL'
                confidence = random.uniform(0.50, 0.70)
        else:  # trend down
            if rand < 0.70:
                signal = 'SELL'
                confidence = random.uniform(0.60, 0.90)
            elif rand < 0.90:
                signal = 'NEUTRAL'
                confidence = random.uniform(0.40, 0.60)
            else:
                signal = 'BUY'
                confidence = random.uniform(0.50, 0.70)
        
        # Generate features (giả lập)
        features = {
            'close': price,
            'SMA_10': price * random.uniform(0.98, 1.02),
            'SMA_50': price * random.uniform(0.95, 1.05),
            'RSI_14': random.uniform(30, 70) if signal == 'BUY' else random.uniform(40, 80),
            'MACD': random.uniform(-100, 100),
            'MACD_signal': random.uniform(-100, 100),
            'BB_UPPER': price * 1.02,
            'BB_MID': price,
            'BB_LOWER': price * 0.98,
            'Volume_SMA': random.uniform(1000, 5000)
        }
        
        # Create signal message
        message = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'price': round(price, 2),
            'prediction': signal,  # ← Changed from 'signal' to 'prediction'
            'confidence': confidence,  # ← Added explicit confidence at top level
            'details': {
                'random_forest': 1 if signal == 'BUY' else 0,
                'svm': 1 if signal == 'BUY' else 0,
                'lr_confidence': confidence,
                'confidence': confidence
            },
            'features': features
        }
        
        return message
    
    def send_signal(self, symbol):
        """Gửi signal vào Kafka"""
        message = self.generate_signal(symbol)
        
        # Send to Kafka
        self.producer.produce(
            self.topic,
            key=symbol.encode('utf-8'),
            value=json.dumps(message).encode('utf-8')
        )
        self.producer.poll(0)
        
        # Log
        signal = message['prediction']  # ← Changed from 'signal' to 'prediction'
        price = message['price']
        confidence = message['confidence']  # ← Get from top level
        
        signal_emoji = '[MUA]' if signal == 'BUY' else '[BAN]' if signal == 'SELL' else '[TRUNG립]'
        print(f"{signal_emoji} {symbol}: {signal} @ ${price:,.2f} (Do tin cay: {confidence:.2%})")
        
        return message
    
    def run_demo(self, duration_seconds=300, interval_seconds=10):
        """
        Chạy demo - gửi signals liên tục
        
        Args:
            duration_seconds: Thời gian chạy (mặc định 5 phút)
            interval_seconds: Khoảng cách giữa các signals (mặc định 10s)
        """
        print("\n" + "="*80)
        print("[DEMO] BO TAO TIN HIEU ML GIA LAP")
        print("="*80)
        print(f"Topic Kafka: {self.topic}")
        print(f"Thoi gian chay: {duration_seconds} giay")
        print(f"Khoang cach: {interval_seconds} giay")
        print(f"Ma giao dich: {', '.join(self.current_prices.keys())}")
        print("="*80 + "\n")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while (time.time() - start_time) < duration_seconds:
                iteration += 1
                print(f"\n--- Iteration #{iteration} ---")
                
                # Send signal cho mỗi symbol
                for symbol in self.current_prices.keys():
                    self.send_signal(symbol)
                    time.sleep(0.5)  # Delay nhỏ giữa các symbols
                
                # Flush producer
                self.producer.flush()
                
                # Random đổi trend (10% chance)
                if random.random() < 0.1:
                    symbol = random.choice(list(self.trends.keys()))
                    old_trend = self.trends[symbol]
                    new_trend = 'down' if old_trend == 'up' else 'up'
                    self.trends[symbol] = new_trend
                    print(f"[XU HUONG] {symbol} thay doi: {old_trend} -> {new_trend}")
                
                # Wait
                print(f"\n[CHO] Cho {interval_seconds} giay...")
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n\n[DUNG] Dang dung demo...")
        
        finally:
            self.producer.flush()
            print("\n[HOAN THANH] Demo ket thuc!")
            print(f"[THONG KE] Tong so lan lap: {iteration}")
            print(f"[THONG KE] Tong so tin hieu: {iteration * len(self.current_prices)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 4 Demo - Fake ML Signal Generator')
    parser.add_argument('--send-signals', action='store_true', help='Send fake signals to Kafka')
    parser.add_argument('--duration', type=int, default=300, help='Duration in seconds (default: 300)')
    parser.add_argument('--interval', type=int, default=10, help='Interval between signals (default: 10)')
    
    args = parser.parse_args()
    
    if args.send_signals:
        generator = FakeMLSignalGenerator()
        generator.run_demo(
            duration_seconds=args.duration,
            interval_seconds=args.interval
        )
    else:
        print("\nUsage:")
        print("  python demo_phase4.py --send-signals")
        print("\nOptions:")
        print("  --duration SECONDS    Duration to run (default: 300)")
        print("  --interval SECONDS    Interval between signals (default: 10)")
        print("\nExample:")
        print("  python demo_phase4.py --send-signals --duration 600 --interval 15")
        print("\nThen in another terminal:")
        print("  python app/consumers/decision_engine.py")


if __name__ == "__main__":
    main()
