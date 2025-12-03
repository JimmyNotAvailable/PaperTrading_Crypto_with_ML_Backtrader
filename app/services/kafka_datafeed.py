"""
Kafka Data Feed for Backtrader
Real-time streaming data from Kafka topics → Backtrader engine

Workflow:
    crypto.market_data (Kafka) → KafkaDataFeed → Backtrader Strategy → Trading decisions
"""
import backtrader as bt  # type: ignore
import logging
from confluent_kafka import Consumer
from datetime import datetime
from typing import Optional
import json
import time

logger = logging.getLogger(__name__)


class KafkaDataFeed(bt.DataBase):  # type: ignore
    """
    Real-time data feed từ Kafka topic
    Tương thích với Backtrader data feed interface
    """
    
    params = (
        ('kafka_brokers', 'localhost:9092'),
        ('kafka_topic', 'crypto.market_data'),
        ('symbol', 'BTCUSDT'),
        ('consumer_group', 'backtrader_consumer'),
        ('fromdate', None),
        ('todate', None),
    )
    
    def __init__(self):
        super(KafkaDataFeed, self).__init__()
        
        # Kafka consumer setup
        self.consumer = Consumer({
            'bootstrap.servers': self.params.kafka_brokers,  # type: ignore
            'group.id': f"{self.params.consumer_group}_{self.params.symbol}",  # type: ignore
            'auto.offset.reset': 'latest',  # Real-time chỉ lấy data mới
            'enable.auto.commit': True
        })
        
        self.consumer.subscribe([self.params.kafka_topic])  # type: ignore
        
        # Buffer for incoming data
        self.data_buffer = []
        self.current_index = 0
        self._eof = False
        
        logger.info(f"[KHOI TAO] KafkaDataFeed cho {self.params.symbol}")  # type: ignore
        logger.info(f"   Topic: {self.params.kafka_topic}")  # type: ignore
    
    def start(self):  # type: ignore
        """Called when data feed starts"""
        super(KafkaDataFeed, self).start()
        logger.info(f"[BAT DAU] KafkaDataFeed cho {self.params.symbol}")  # type: ignore
    
    def _load(self):  # type: ignore
        """
        Load next data point from Kafka
        Returns True if data loaded, False if no more data
        """
        # Poll Kafka for new message
        msg = self.consumer.poll(timeout=1.0)
        
        if msg is None:
            # No message yet, wait
            return None
        
        if msg.error():
            logger.error(f"❌ Kafka error: {msg.error()}")
            return False
        
        try:
            # Parse message
            data = json.loads(msg.value().decode('utf-8'))
            
            # Filter by symbol
            if data.get('symbol') != self.params.symbol:  # type: ignore
                return None  # Skip, not our symbol
            
            # Convert to Backtrader format
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            
            # Set OHLCV data
            self.lines.datetime[0] = bt.date2num(timestamp)  # type: ignore
            self.lines.open[0] = float(data.get('open', data['price']))  # type: ignore
            self.lines.high[0] = float(data.get('high', data['price']))  # type: ignore
            self.lines.low[0] = float(data.get('low', data['price']))  # type: ignore
            self.lines.close[0] = float(data['price'])  # type: ignore
            self.lines.volume[0] = float(data.get('volume', 0))  # type: ignore
            self.lines.openinterest[0] = 0  # type: ignore
            
            logger.debug(f"[DU LIEU] [{self.params.symbol}] Tai: ${data['price']:,.2f}")  # type: ignore
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error parsing Kafka message: {str(e)}")
            return None
    
    def stop(self):  # type: ignore
        """Called when data feed stops"""
        super(KafkaDataFeed, self).stop()
        self.consumer.close()
        logger.info(f"⏹️ KafkaDataFeed stopped for {self.params.symbol}")  # type: ignore


class BatchedKafkaDataFeed(bt.DataBase):  # type: ignore
    """
    Batched Kafka data feed - thu thập nhiều messages trước khi feed vào Backtrader
    Phù hợp cho backtesting với historical data từ Kafka
    """
    
    params = (
        ('kafka_brokers', 'localhost:9092'),
        ('kafka_topic', 'crypto.market_data'),
        ('symbol', 'BTCUSDT'),
        ('consumer_group', 'backtrader_batch_consumer'),
        ('batch_size', 100),  # Số messages thu thập trước
        ('fromdate', None),
        ('todate', None),
    )
    
    def __init__(self):
        super(BatchedKafkaDataFeed, self).__init__()
        
        # Kafka consumer
        self.consumer = Consumer({
            'bootstrap.servers': self.params.kafka_brokers,  # type: ignore
            'group.id': f"{self.params.consumer_group}_{self.params.symbol}",  # type: ignore
            'auto.offset.reset': 'earliest',  # Đọc từ đầu
            'enable.auto.commit': False
        })
        
        self.consumer.subscribe([self.params.kafka_topic])  # type: ignore
        
        # Data buffer
        self.data_buffer = []
        self.current_index = 0
        self._preloaded = False
        
        logger.info(f"[KHOI TAO] BatchedKafkaDataFeed cho {self.params.symbol}")  # type: ignore
    
    def _preload_data(self):
        """Preload batch of data from Kafka"""
        if self._preloaded:
            return
        
        logger.info(f"📥 Preloading {self.params.batch_size} messages...")  # type: ignore
        
        loaded = 0
        timeout_count = 0
        max_timeouts = 5
        
        while loaded < self.params.batch_size and timeout_count < max_timeouts:  # type: ignore
            msg = self.consumer.poll(timeout=1.0)
            
            if msg is None:
                timeout_count += 1
                continue
            
            if msg.error():
                logger.error(f"❌ Kafka error: {msg.error()}")
                break
            
            try:
                data = json.loads(msg.value().decode('utf-8'))
                
                # Filter by symbol
                if data.get('symbol') != self.params.symbol:  # type: ignore
                    continue
                
                # Add to buffer
                self.data_buffer.append({
                    'timestamp': datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
                    'open': float(data.get('open', data['price'])),
                    'high': float(data.get('high', data['price'])),
                    'low': float(data.get('low', data['price'])),
                    'close': float(data['price']),
                    'volume': float(data.get('volume', 0))
                })
                
                loaded += 1
                
            except Exception as e:
                logger.error(f"❌ Error parsing message: {str(e)}")
                continue
        
        logger.info(f"[TAI DU LIEU] Da tai truoc {len(self.data_buffer)} diem du lieu")
        self._preloaded = True
    
    def start(self):  # type: ignore
        """Called when data feed starts"""
        super(BatchedKafkaDataFeed, self).start()
        self._preload_data()
    
    def _load(self):  # type: ignore
        """Load next data point from buffer"""
        if self.current_index >= len(self.data_buffer):
            return False  # No more data
        
        data = self.data_buffer[self.current_index]
        
        # Set OHLCV
        self.lines.datetime[0] = bt.date2num(data['timestamp'])  # type: ignore
        self.lines.open[0] = data['open']  # type: ignore
        self.lines.high[0] = data['high']  # type: ignore
        self.lines.low[0] = data['low']  # type: ignore
        self.lines.close[0] = data['close']  # type: ignore
        self.lines.volume[0] = data['volume']  # type: ignore
        self.lines.openinterest[0] = 0  # type: ignore
        
        self.current_index += 1
        return True
    
    def stop(self):  # type: ignore
        """Called when data feed stops"""
        super(BatchedKafkaDataFeed, self).stop()
        self.consumer.close()
        logger.info(f"⏹️ BatchedKafkaDataFeed stopped")
