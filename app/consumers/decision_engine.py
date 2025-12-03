"""
Decision Engine Consumer - Phase 4
Lắng nghe ML signals từ Kafka, ra quyết định trading với Backtrader,
và gửi orders vào Kafka topic crypto.orders

Luồng:
Phase 3: ML Consumer → crypto.ml_signals
Phase 4: Decision Engine → đọc crypto.ml_signals → Backtrader → crypto.orders

Theo thiết kế ToturialUpgrade.md
"""
import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional
from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.virtual_exchange import VirtualExchange

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class DecisionEngine:
    """
    Decision Engine - Hệ thống ra quyết định giao dịch
    
    Chức năng:
    1. Lắng nghe ML signals từ Kafka (crypto.ml_signals)
    2. Áp dụng risk management rules:
       - Stop Loss: 2%
       - Take Profit: 5%
       - RSI check để tránh mua đỉnh
    3. Sử dụng Virtual Exchange để simulate trading
    4. Gửi orders vào Kafka (crypto.orders)
    """
    
    def __init__(
        self,
        kafka_bootstrap_servers: str = 'localhost:9092',
        initial_balance: float = 10000.0
    ):
        """
        Khởi tạo Decision Engine
        
        Args:
            kafka_bootstrap_servers: Kafka server address
            initial_balance: Số dư ban đầu cho Virtual Exchange
        """
        # Kafka Consumer (lắng nghe ML signals)
        self.consumer = Consumer({
            'bootstrap.servers': kafka_bootstrap_servers,
            'group.id': 'decision_engine_group',
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True
        })
        
        # Kafka Producer (gửi orders)
        self.producer = Producer({
            'bootstrap.servers': kafka_bootstrap_servers,
            'client.id': 'decision-engine-producer'
        })
        
        # Topics
        self.ml_signals_topic = 'crypto.ml_signals'
        self.orders_topic = 'crypto.orders'
        
        # Subscribe to ML signals
        self.consumer.subscribe([self.ml_signals_topic])
        
        # Virtual Exchange
        self.exchange = VirtualExchange(
            initial_balance=initial_balance,
            commission_rate=0.001,  # 0.1% phí
            max_position_size=0.95  # 95% max position
        )
        
        # Strategy parameters (từ ToturialUpgrade.md)
        self.stop_loss_pct = 0.02   # 2% Stop Loss
        self.take_profit_pct = 0.05  # 5% Take Profit
        self.rsi_overbought = 70     # RSI > 70 không mua
        self.min_confidence = 0.60   # Min confidence để trade
        
        # Tracking
        self.last_prices: Dict[str, float] = {}  # symbol -> last_price
        self.last_rsi: Dict[str, float] = {}     # symbol -> last_rsi
        
        logger.info("🎯 Decision Engine initialized")
        logger.info(f"   Listening to: {self.ml_signals_topic}")
        logger.info(f"   Publishing to: {self.orders_topic}")
        logger.info(f"   Initial Balance: ${initial_balance:,.2f}")
        logger.info(f"   Risk Parameters: SL {self.stop_loss_pct*100}%, TP {self.take_profit_pct*100}%")
    
    def delivery_report(self, err, msg):
        """Callback cho Kafka producer"""
        if err is not None:
            logger.error(f'❌ Order delivery failed: {err}')
        else:
            logger.debug(f'✅ Order delivered to {msg.topic()}')
    
    def send_order(self, order_data: Dict):
        """
        Gửi order vào Kafka topic crypto.orders
        
        Args:
            order_data: Dict chứa thông tin order
        """
        try:
            message = json.dumps(order_data).encode('utf-8')
            self.producer.produce(
                self.orders_topic,
                key=order_data['symbol'].encode('utf-8'),
                value=message,
                callback=self.delivery_report
            )
            self.producer.poll(0)
            
            logger.info(f"📤 Order sent to Kafka: {order_data['action']} {order_data['symbol']}")
        
        except Exception as e:
            logger.error(f"❌ Failed to send order: {str(e)}")
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """
        Tính kích thước position
        
        Args:
            symbol: Ký hiệu coin
            price: Giá hiện tại
        
        Returns:
            Số lượng coin cần mua
        """
        available_balance = self.exchange.get_available_balance()
        position_value = available_balance * 0.95  # 95% của balance
        
        # Tính số lượng coin
        amount = position_value / price
        
        return amount
    
    def should_buy(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        price: float,
        features: Dict
    ) -> tuple[bool, str]:
        """
        Quyết định có nên MUA không
        
        Theo logic ToturialUpgrade.md:
        1. Signal: Model dự đoán "Tăng" (BUY)
        2. Strategy:
           - Kiểm tra ví tiền (Balance)
           - Kiểm tra rủi ro (Risk Management)
           - Kiểm tra chỉ báo phụ (RSI < 70) để tránh mua đỉnh
        3. Action: Gửi lệnh mua
        
        Returns:
            (should_buy, reason)
        """
        # 1. Kiểm tra signal
        if signal != 'BUY':
            return False, f"Signal is {signal}"
        
        # 2. Kiểm tra confidence
        if confidence < self.min_confidence:
            return False, f"Confidence {confidence:.2%} < {self.min_confidence:.2%}"
        
        # 3. Kiểm tra đã có position chưa
        if symbol in self.exchange.positions:
            return False, f"Already have position for {symbol}"
        
        # 4. Kiểm tra balance
        can_open, reason = self.exchange.can_open_position(
            symbol,
            price,
            self.calculate_position_size(symbol, price)
        )
        if not can_open:
            return False, reason
        
        # 5. Kiểm tra RSI (nếu có)
        if 'RSI_14' in features:
            rsi = features['RSI_14']
            self.last_rsi[symbol] = rsi
            
            if rsi > self.rsi_overbought:
                return False, f"RSI {rsi:.1f} > {self.rsi_overbought} (overbought)"
        
        return True, "All conditions met"
    
    def should_sell(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        price: float,
        features: Dict
    ) -> tuple[bool, str]:
        """
        Quyết định có nên BÁN không
        
        Returns:
            (should_sell, reason)
        """
        # 1. Kiểm tra có position không
        if symbol not in self.exchange.positions:
            return False, "No position"
        
        position = self.exchange.positions[symbol]
        
        # 2. Kiểm tra ML signal SELL
        if signal == 'SELL':
            return True, "ML signal SELL"
        
        # 3. Kiểm tra Stop Loss
        loss_pct = (price - position.entry_price) / position.entry_price
        if loss_pct <= -self.stop_loss_pct:
            return True, f"Stop Loss: {loss_pct:.2%}"
        
        # 4. Kiểm tra Take Profit
        if loss_pct >= self.take_profit_pct:
            return True, f"Take Profit: {loss_pct:.2%}"
        
        # 5. Kiểm tra RSI oversold (nếu có)
        if 'RSI_14' in features:
            rsi = features['RSI_14']
            if rsi < 30:  # Oversold
                return True, f"RSI {rsi:.1f} < 30 (oversold)"
        
        return False, "Hold position"
    
    def process_ml_signal(self, message_value: bytes):
        """
        Xử lý ML signal từ Kafka
        
        Args:
            message_value: JSON message từ Kafka
        """
        try:
            # Parse message
            data = json.loads(message_value.decode('utf-8'))
            
            symbol = data.get('symbol', 'UNKNOWN')
            signal = data.get('signal', 'NEUTRAL')
            price = data.get('price', 0.0)
            timestamp = data.get('timestamp', int(time.time() * 1000))
            
            # ML details
            details = data.get('details', {})
            confidence = details.get('confidence', 0.0)
            
            # Features
            features = data.get('features', {})
            
            # Update tracking
            self.last_prices[symbol] = price
            
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 ML SIGNAL RECEIVED: {symbol}")
            logger.info(f"   Signal: {signal}")
            logger.info(f"   Price: ${price:,.2f}")
            logger.info(f"   Confidence: {confidence:.2%}")
            logger.info(f"   Details: {details}")
            
            # Kiểm tra Stop Loss / Take Profit cho positions hiện tại
            if symbol in self.exchange.positions:
                trade = self.exchange.check_stop_loss_take_profit(symbol, price, timestamp)
                if trade:
                    # Gửi order SELL vào Kafka
                    order = {
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': price,
                        'amount': trade.amount,
                        'timestamp': timestamp,
                        'reason': 'STOP_LOSS' if trade.pnl < 0 else 'TAKE_PROFIT',
                        'pnl': trade.pnl,
                        'pnl_percentage': trade.pnl_percentage
                    }
                    self.send_order(order)
                    return
            
            # Quyết định BUY
            should_buy, buy_reason = self.should_buy(symbol, signal, confidence, price, features)
            if should_buy:
                # Tính position size
                amount = self.calculate_position_size(symbol, price)
                
                # Tính Stop Loss và Take Profit
                stop_loss = price * (1 - self.stop_loss_pct)
                take_profit = price * (1 + self.take_profit_pct)
                
                # Mở position
                position = self.exchange.open_position(
                    symbol=symbol,
                    price=price,
                    amount=amount,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    signal_details=details
                )
                
                if position:
                    # Gửi order BUY vào Kafka
                    order = {
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': price,
                        'amount': amount,
                        'timestamp': timestamp,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'ml_signal': signal,
                        'ml_confidence': confidence,
                        'ml_details': details,
                        'status': 'FILLED'
                    }
                    self.send_order(order)
            else:
                logger.info(f"   ⏸️  No BUY: {buy_reason}")
            
            # Quyết định SELL
            should_sell, sell_reason = self.should_sell(symbol, signal, confidence, price, features)
            if should_sell:
                # Đóng position
                trade = self.exchange.close_position(symbol, price, timestamp, sell_reason)
                
                if trade:
                    # Gửi order SELL vào Kafka
                    order = {
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': price,
                        'amount': trade.amount,
                        'timestamp': timestamp,
                        'reason': sell_reason,
                        'pnl': trade.pnl,
                        'pnl_percentage': trade.pnl_percentage,
                        'status': 'FILLED'
                    }
                    self.send_order(order)
            
            logger.info(f"{'='*70}\n")
        
        except Exception as e:
            logger.error(f"❌ Error processing ML signal: {str(e)}", exc_info=True)
    
    def start(self):
        """Bắt đầu Decision Engine"""
        logger.info("🚀 Decision Engine Service Started...")
        logger.info(f"📡 Consuming from: {self.ml_signals_topic}")
        logger.info(f"📤 Producing to: {self.orders_topic}")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            message_count = 0
            
            while True:
                # Poll message từ Kafka
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                # Process ML signal
                message_count += 1
                logger.debug(f"📥 Message #{message_count} received from {msg.topic()}")
                
                self.process_ml_signal(msg.value())
                
                # Flush producer
                self.producer.flush()
                
                # In statistics mỗi 10 messages
                if message_count % 10 == 0:
                    self.exchange.print_statistics()
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopping Decision Engine...")
        
        finally:
            # Print final statistics
            logger.info("\n" + "="*70)
            logger.info("📊 FINAL STATISTICS")
            logger.info("="*70)
            self.exchange.print_statistics()
            
            # Close connections
            self.consumer.close()
            logger.info("✅ Decision Engine stopped gracefully")


def main():
    """Main function"""
    # Get config từ environment
    kafka_bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    initial_balance = float(os.getenv('VIRTUAL_EXCHANGE_BALANCE', '10000.0'))
    
    # Create và start Decision Engine
    engine = DecisionEngine(
        kafka_bootstrap_servers=kafka_bootstrap,
        initial_balance=initial_balance
    )
    
    engine.start()


if __name__ == "__main__":
    main()
