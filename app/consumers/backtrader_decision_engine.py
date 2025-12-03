"""
Backtrader-based Decision Engine for Phase 4
Refactored version using Backtrader execution engine instead of Virtual Exchange

Architecture:
    Kafka crypto.ml_signals → Backtrader Strategy → Execution → SQLite Logs → Kafka crypto.orders

Advantages over Virtual Exchange:
    1. Zero latency (local execution)
    2. Built-in commission/slippage handling
    3. SQLite logging for Streamlit dashboard
    4. Professional backtesting framework
    5. Better for demo (no external dependencies)
"""
import logging
import json
import signal
import sys
from pathlib import Path
from confluent_kafka import Consumer, Producer
from datetime import datetime
from typing import Dict, Any, Optional
import backtrader as bt  # type: ignore

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.backtrader_broker import BacktraderBroker, MLKafkaStrategy, TradeLogger
from app.services.kafka_datafeed import KafkaDataFeed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktraderDecisionEngine:
    """
    Decision Engine sử dụng Backtrader làm execution engine
    Thay thế Virtual Exchange để tối ưu cho demo và dashboard
    """
    
    def __init__(
        self,
        kafka_brokers: str = 'localhost:9092',
        input_topic: str = 'crypto.ml_signals',
        output_topic: str = 'crypto.orders',
        market_data_topic: str = 'crypto.market_data',
        initial_cash: float = 10000.0,
        commission: float = 0.001,
        db_path: str = 'data/trading_logs.db',
        symbols: Optional[list] = None
    ):
        """
        Initialize Backtrader Decision Engine
        
        Args:
            kafka_brokers: Kafka bootstrap servers
            input_topic: Topic to consume ML signals from
            output_topic: Topic to produce orders to
            market_data_topic: Topic with market OHLCV data
            initial_cash: Starting capital
            commission: Trading commission (0.1% = 0.001)
            db_path: SQLite database for logging
            symbols: List of symbols to trade (default: ['BTCUSDT', 'ETHUSDT'])
        """
        self.kafka_brokers = kafka_brokers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.market_data_topic = market_data_topic
        self.db_path = db_path
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        
        # Kafka consumer for ML signals
        self.consumer = Consumer({
            'bootstrap.servers': kafka_brokers,
            'group.id': 'backtrader_decision_engine',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        })
        self.consumer.subscribe([input_topic])
        
        # Kafka producer for orders
        self.producer = Producer({'bootstrap.servers': kafka_brokers})
        
        # Trade logger
        self.trade_logger = TradeLogger(db_path)
        
        # Backtrader brokers - một cho mỗi symbol
        self.brokers = {}
        self.strategies = {}
        
        # Active positions tracking
        self.active_positions = {}
        
        # Risk management parameters
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.min_confidence = 0.60
        self.rsi_overbought = 70
        
        self._running = True
        
        logger.info(f"[KHOI TAO] Backtrader Decision Engine")
        logger.info(f"   Kafka Input: {input_topic}")
        logger.info(f"   Kafka Output: {output_topic}")
        logger.info(f"   Du lieu thi truong: {market_data_topic}")
        logger.info(f"   Von ban dau: ${initial_cash:,.2f}")
        logger.info(f"   Phi giao dich: {commission * 100}%")
        logger.info(f"   Ma giao dich: {', '.join(self.symbols)}")
        logger.info(f"   Database: {db_path}")
    
    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        logger.info("\n[CANH BAO] Nhan duoc tin hieu tat dich vu...")
        self._running = False
    
    def _process_ml_signal(self, signal_data: Dict[str, Any]):
        """
        Process ML signal and make trading decision
        
        Args:
            signal_data: ML signal from Kafka
        """
        symbol = signal_data.get('symbol', 'UNKNOWN')
        prediction = signal_data.get('prediction', 'NEUTRAL')
        confidence = signal_data.get('confidence', 0.0)
        price = signal_data.get('price', 0.0)
        details = signal_data.get('details', {})
        
        logger.info("\n" + "="*70)
        logger.info(f"[TIN HIEU ML] {symbol}")
        logger.info(f"   Du bao: {prediction}")
        logger.info(f"   Gia: ${price:,.2f}")
        logger.info(f"   Do tin cay: {confidence:.2%}")
        logger.info(f"   Chi tiet: {details}")
        
        # Decision logic based on ML signal + risk management
        action = None
        reason = None
        
        # Check BUY conditions
        if prediction == 'BUY':
            if confidence < self.min_confidence:
                reason = f"Do tin cay {confidence:.2%} < {self.min_confidence:.2%}"
                logger.info(f"   [BO QUA] Khong MUA: {reason}")
            elif symbol in self.active_positions:
                reason = f"Da co vi the cho {symbol}"
                logger.info(f"   [BO QUA] Khong MUA: {reason}")
            else:
                # BUY action
                action = 'BUY'
                reason = f"ML Signal BUY with {confidence:.2%} confidence"
                
                # Calculate position size
                cash_available = 10000.0  # Simplified for now
                position_value = cash_available * 0.95
                amount = position_value / price
                
                # Record position
                self.active_positions[symbol] = {
                    'entry_price': price,
                    'amount': amount,
                    'entry_time': datetime.now().isoformat(),
                    'ml_signal': prediction,
                    'ml_confidence': confidence,
                    'stop_loss': price * (1 - self.stop_loss_pct),
                    'take_profit': price * (1 + self.take_profit_pct)
                }
                
                # Tính Risk/Reward ratio
                sl_price = self.active_positions[symbol]['stop_loss']
                tp_price = self.active_positions[symbol]['take_profit']
                risk_amount = (price - sl_price) * amount
                reward_amount = (tp_price - price) * amount
                rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
                
                logger.info(f"   [QUYET DINH MUA] {reason}")
                logger.info(f"      Khoi luong: {amount:.6f} {symbol[:3]}")
                logger.info(f"      Gia tri: ${position_value:,.2f}")
                logger.info(f"      Stop Loss: ${sl_price:,.2f} (-{self.stop_loss_pct*100:.1f}%)")
                logger.info(f"      Take Profit: ${tp_price:,.2f} (+{self.take_profit_pct*100:.1f}%)")
                logger.info(f"      Risk/Reward: 1:{rr_ratio:.2f}")
        
        # Check SELL conditions
        elif prediction == 'SELL':
            if symbol not in self.active_positions:
                reason = "Chua co vi the de ban"
                logger.info(f"   [BO QUA] Khong BAN: {reason}")
            else:
                action = 'SELL'
                position = self.active_positions[symbol]
                
                # Calculate PnL
                entry_price = position['entry_price']
                pnl = (price - entry_price) * position['amount']
                pnl_pct = ((price - entry_price) / entry_price) * 100
                
                reason = f"Tin hieu ML BAN | Loi nhuan: {pnl_pct:+.2f}%"
                
                logger.info(f"   [QUYET DINH BAN] {reason}")
                logger.info(f"      Gia vao: ${entry_price:,.2f} -> Gia ra: ${price:,.2f}")
                logger.info(f"      Loi/Lo: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
                logger.info(f"      Khoi luong: {position['amount']:.6f} {symbol[:3]}")
                
                # Remove position
                del self.active_positions[symbol]
        
        # Check Stop Loss / Take Profit for existing positions
        elif symbol in self.active_positions:
            position = self.active_positions[symbol]
            entry_price = position['entry_price']
            
            # Stop Loss
            if price <= position['stop_loss']:
                action = 'SELL'
                pnl_pct = ((price - entry_price) / entry_price) * 100
                pnl = (price - entry_price) * position['amount']
                reason = f"Kich hoat Cat lo: {pnl_pct:.2f}%"
                
                logger.warning(f"   [CAT LO] {reason}")
                logger.warning(f"      Gia vao: ${entry_price:,.2f} -> Gia ra: ${price:,.2f}")
                logger.warning(f"      Thua lo: ${pnl:,.2f}")
                del self.active_positions[symbol]
            
            # Take Profit
            elif price >= position['take_profit']:
                action = 'SELL'
                pnl_pct = ((price - entry_price) / entry_price) * 100
                pnl = (price - entry_price) * position['amount']
                reason = f"Kich hoat Chot loi: {pnl_pct:.2f}%"
                
                logger.info(f"   [CHOT LOI] {reason}")
                logger.info(f"      Gia vao: ${entry_price:,.2f} -> Gia ra: ${price:,.2f}")
                logger.info(f"      Loi nhuan: ${pnl:+,.2f}")
                del self.active_positions[symbol]
        
        logger.info("="*70)
        
        # Produce order to Kafka if action decided
        if action and reason:
            self._produce_order(symbol, action, price, signal_data, reason)
    
    def _produce_order(
        self,
        symbol: str,
        action: str,
        price: float,
        signal_data: Dict[str, Any],
        reason: str
    ):
        """
        Produce trading order to Kafka
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            price: Execution price
            signal_data: Original ML signal data
            reason: Reason for the decision
        """
        order = {
            'symbol': symbol,
            'action': action,
            'price': price,
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'ml_signal': signal_data.get('prediction'),
            'ml_confidence': signal_data.get('confidence'),
            'ml_details': signal_data.get('details', {})
        }
        
        # Add position details for BUY
        if action == 'BUY' and symbol in self.active_positions:
            position = self.active_positions[symbol]
            order['amount'] = position['amount']
            order['value'] = position['amount'] * price
            order['stop_loss'] = position['stop_loss']
            order['take_profit'] = position['take_profit']
        
        # Produce to Kafka
        try:
            self.producer.produce(
                self.output_topic,
                key=symbol.encode('utf-8'),
                value=json.dumps(order).encode('utf-8')
            )
            self.producer.flush()
            logger.info(f"[KAFKA] Lenh {action} {symbol} da gui thanh cong")
        except Exception as e:
            logger.error(f"[LOI] Gui lenh that bai: {str(e)}")
        
        # Log to SQLite for dashboard
        try:
            self.trade_logger.log_trade({
                'symbol': symbol,
                'action': action,
                'price': price,
                'amount': order.get('amount', 0),
                'value': order.get('value', 0),
                'commission': order.get('value', 0) * 0.001 if 'value' in order else 0,
                'reason': reason,
                'ml_signal': signal_data.get('prediction'),
                'ml_confidence': signal_data.get('confidence'),
                'ml_details': signal_data.get('details', {})
            })
        except Exception as e:
            logger.error(f"[LOI] Ghi log giao dich that bai: {str(e)}")
    
    def run(self):
        """Main event loop"""
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("[BAT DAU] Dich vu Backtrader Decision Engine")
        logger.info(f"[KAFKA] Tieu thu tu topic: {self.input_topic}")
        logger.info(f"[KAFKA] San xuat toi topic: {self.output_topic}")
        logger.info("Nhan Ctrl+C de dung\n")
        
        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"[LOI KAFKA] {msg.error()}")
                    continue
                
                try:
                    # Parse ML signal
                    signal_data = json.loads(msg.value().decode('utf-8'))
                    
                    # Process signal
                    self._process_ml_signal(signal_data)
                    
                except Exception as e:
                    logger.error(f"[LOI] Xu ly message that bai: {str(e)}")
                    continue
        
        except KeyboardInterrupt:
            logger.info("\n[DUNG] Nhan duoc lenh ngat tu ban phim")
        
        finally:
            logger.info("\n[TAT DICH VU] Dang dong ket noi...")
            self.consumer.close()
            self.producer.flush()
            
            # Log final statistics
            logger.info("\n" + "="*70)
            logger.info("[TONG KET PHIEN GIAO DICH]")
            logger.info("="*70)
            logger.info(f"So vi the dang mo: {len(self.active_positions)}")
            for symbol, pos in self.active_positions.items():
                logger.info(f"   {symbol}:")
                logger.info(f"      Gia vao: ${pos['entry_price']:,.2f}")
                logger.info(f"      Khoi luong: {pos['amount']:.6f}")
                logger.info(f"      Stop Loss: ${pos['stop_loss']:,.2f}")
                logger.info(f"      Take Profit: ${pos['take_profit']:,.2f}")
            logger.info("="*70)


def main():
    """Entry point"""
    engine = BacktraderDecisionEngine(
        kafka_brokers='localhost:9092',
        input_topic='crypto.ml_signals',
        output_topic='crypto.orders',
        initial_cash=10000.0,
        commission=0.001,
        db_path='data/trading_logs.db'
    )
    
    engine.run()


if __name__ == '__main__':
    main()
