#!/usr/bin/env python3
"""
Kafka Producer: Thu thập dữ liệu crypto từ Binance → Kafka topic

Producer Service Pattern (from RESTRUCTURING_PLAN_KAFKA.md):
- Fetch OHLCV data from Binance API
- Produce to crypto.market_data topic
- Message key = symbol (for ordering)
- Compression = gzip (bandwidth optimization)

Message Schema (from KAFKA_TOPICS_SCHEMA.md):
{
    "symbol": "BTCUSDT",
    "timestamp": 1701187200000,
    "price": 68000.50,
    "open": 67500.00,
    "high": 68500.00,
    "low": 67200.00,
    "volume": 12345.67,
    "price_change_pct": 2.15
}

Usage:
    python app/producers/binance_producer.py
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import dependencies with error handling
try:
    from confluent_kafka import Producer
except ImportError:
    print("❌ Error: confluent-kafka not installed")
    print("💡 Install it: pip install confluent-kafka")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ Error: requests not installed")
    print("💡 Install it: pip install requests")
    sys.exit(1)

from app.utils.logger import get_logger
from app.utils.config_loader import get_kafka_bootstrap_servers
from config.kafka_config import get_kafka_producer_config, KafkaTopics
from app.ml.feature_engineering import calculate_features
import pandas as pd

logger = get_logger(__name__)

class BinanceKafkaProducer:
    """
    Producer service: Binance API → Kafka topic crypto.market_data
    
    Features:
    - Real-time price data from Binance
    - Automatic retry on API failures
    - Message validation before sending
    - Kafka delivery callbacks
    """
    
    def __init__(self):
        """Initialize Binance Kafka Producer"""
        # Kafka configuration
        kafka_config = get_kafka_producer_config()
        
        try:
            self.producer = Producer(kafka_config)
        except Exception as e:
            logger.error(f"❌ Failed to create Kafka producer: {e}")
            logger.error("🔍 Check if Kafka is running: docker-compose up -d kafka")
            raise
        
        self.topic = KafkaTopics.MARKET_DATA
        
        # Binance API configuration
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Supported symbols (from copilot-instructions.md)
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOGEUSDT',
            'XRPUSDT', 'DOTUSDT', 'LTCUSDT', 'LINKUSDT',
            'BCHUSDT', 'XLMUSDT'
        ]
        
        # Load feature metadata for each symbol with improved models
        self.features_metadata = {}
        self._load_feature_metadata()
        
        # Buffer for historical data (need 50+ candles for MA_50, etc.)
        self.historical_buffers = {symbol: [] for symbol in self.symbols}
        
        logger.info("🚀 BinanceKafkaProducer initialized")
        logger.info(f"📡 Kafka: {kafka_config['bootstrap.servers']}")
        logger.info(f"📊 Topic: {self.topic}")
        logger.info(f"💰 Symbols: {', '.join(self.symbols)}")
    
    def _load_feature_metadata(self):
        """
        Load improved feature metadata for each symbol
        Maps symbol base (BTC, ETH, etc.) to selected features
        """
        models_dir = project_root / "app" / "ml" / "models"
        
        # Symbols with trained improved models
        trained_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']
        
        for symbol_base in trained_symbols:
            features_file = models_dir / f"improved_features_{symbol_base}.json"
            
            if features_file.exists():
                try:
                    with open(features_file, 'r') as f:
                        metadata = json.load(f)
                        self.features_metadata[symbol_base] = metadata['selected_features']
                        logger.info(f"✅ Loaded {len(metadata['selected_features'])} features for {symbol_base}")
                except Exception as e:
                    logger.error(f"❌ Error loading features for {symbol_base}: {e}")
                    # Fallback to all features if metadata missing
                    self.features_metadata[symbol_base] = None
            else:
                logger.warning(f"⚠️ No feature metadata for {symbol_base}, will use all features")
                self.features_metadata[symbol_base] = None
    
    def delivery_report(self, err, msg):
        """
        Callback khi message được gửi (or failed)
        
        Args:
            err: Error object (None if success)
            msg: Message object
        """
        if err is not None:
            logger.error(f'❌ Message delivery failed: {err}')
        else:
            logger.debug(f'✅ Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}')
    
    def fetch_klines(self, symbol: str, limit: int = 100, max_retries: int = 3) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu klines (candlestick) từ Binance API để tính features
        
        Args:
            symbol: Crypto symbol (e.g., 'BTCUSDT')
            limit: Number of recent klines to fetch (default 100 for MA_50 calculation)
            max_retries: Maximum number of retry attempts
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Get klines (1h interval)
                klines_url = f"{self.binance_api}/klines"
                params = {
                    'symbol': symbol,
                    'interval': '1h',
                    'limit': limit
                }
                response = requests.get(klines_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    klines = response.json()
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                    
                    # Keep only OHLCV columns
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    
                    # Convert types
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    # Add symbol column
                    df['symbol'] = symbol
                    
                    # Rename timestamp to date for compatibility
                    df.rename(columns={'timestamp': 'date'}, inplace=True)
                    
                    return df
                    logger.error(f"❌ Binance API error {response.status_code} for {symbol}")
                    if attempt < max_retries - 1:
                        logger.info(f"♻️ Retrying {symbol}... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(1)  # Wait before retry
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                logger.error(f"⏱️ Timeout fetching data for {symbol}")
                if attempt < max_retries - 1:
                    logger.info(f"♻️ Retrying {symbol}... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(1)
                    continue
                return None
            except Exception as e:
                logger.error(f"❌ Error fetching {symbol}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"♻️ Retrying {symbol}... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(1)
                    continue
                return None
        
        return None  # All retries failed
    
    def calculate_symbol_features(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """
        Tính toán features cho symbol dựa trên OHLCV data
        
        Args:
            df: DataFrame with OHLCV data (at least 50 rows for MA_50)
            symbol: Crypto symbol (e.g., 'BTCUSDT')
        
        Returns:
            Dict with selected features or None if calculation fails
        """
        try:
            # Calculate ALL 26 features (needed for dependencies)
            df_with_features = calculate_features(df, include_target=False)
            
            # Get the latest row (most recent data)
            latest = df_with_features.iloc[-1]
            
            # Get base symbol (BTC from BTCUSDT)
            symbol_base = symbol.replace('USDT', '')
            
            # Get selected features for this symbol
            selected_features = self.features_metadata.get(symbol_base)
            
            if selected_features:
                # Extract only selected features
                features_dict = {feat: float(latest[feat]) for feat in selected_features}
            else:
                # Fallback: Use all calculated features
                feature_cols = [col for col in df_with_features.columns 
                               if col not in ['date', 'symbol', 'timestamp', 'close_time']]
                features_dict = {feat: float(latest[feat]) for feat in feature_cols}
            
            # Add metadata
            result = {
                'symbol': symbol,
                'timestamp': int(latest['date'].timestamp() * 1000) if pd.notna(latest['date']) else int(time.time() * 1000),
                'price': float(latest['close']),
                'features': features_dict,
                'n_features': len(features_dict)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculating features for {symbol}: {e}")
            return None
    
    def _validate_market_data(self, data: Dict) -> bool:
        """
        Validate market data before sending to Kafka
        
        Validation rules from KAFKA_TOPICS_SCHEMA.md:
        - price, open, high, low must be > 0
        - high >= low
        - volume >= 0
        
        Args:
            data: Market data dict
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Price validations
            if data['price'] <= 0 or data['open'] <= 0:
                return False
            if data['high'] <= 0 or data['low'] <= 0:
                return False
            
            # High/Low relationship
            if data['high'] < data['low']:
                return False
            
            # Volume
            if data['volume'] < 0:
                return False
            
            return True
            
        except (KeyError, TypeError) as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def produce_market_data(self, interval_seconds: int = 60):
        """
        Main loop: Thu thập và gửi dữ liệu vào Kafka
        
        Args:
            interval_seconds: Thời gian chờ giữa các lần fetch (seconds)
        """
        logger.info(f"🚀 Starting Binance Producer (interval: {interval_seconds}s)...")
        logger.info(f"⏹️ Press Ctrl+C to stop")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*60}")
                
                success_count = 0
                fail_count = 0
                
                for symbol in self.symbols:
                    # Fetch klines data (100 candles for MA_50 calculation)
                    df = self.fetch_klines(symbol, limit=100)
                    
                    if df is not None and len(df) >= 50:
                        # Calculate features
                        data = self.calculate_symbol_features(df, symbol)
                        
                        if data:
                            try:
                                # Serialize to JSON
                                message = json.dumps(data).encode('utf-8')
                                
                                # Send to Kafka (key = symbol for ordering)
                                self.producer.produce(
                                    self.topic,
                                    key=symbol.encode('utf-8'),
                                    value=message,
                                    callback=self.delivery_report
                                )
                                
                                logger.info(f"📤 {symbol}: ${data['price']:,.2f} ({data['n_features']} features)")
                                success_count += 1
                                
                            except Exception as e:
                                logger.error(f"❌ Failed to produce {symbol}: {e}")
                                fail_count += 1
                        else:
                            logger.warning(f"⚠️ Feature calculation failed for {symbol}")
                            fail_count += 1
                    else:
                        logger.warning(f"⚠️ Insufficient klines data for {symbol} (need 50+)")
                        fail_count += 1
                
                # Flush buffer to ensure delivery
                self.producer.flush()
                
                logger.info(f"\n✅ Success: {success_count}/{len(self.symbols)}")
                if fail_count > 0:
                    logger.warning(f"❌ Failed: {fail_count}/{len(self.symbols)}")
                
                logger.info(f"💤 Sleeping {interval_seconds}s until next iteration...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️ Producer stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in producer loop: {e}")
            raise
        finally:
            # Cleanup
            logger.info("🧹 Flushing remaining messages...")
            self.producer.flush()
            logger.info("✅ Producer shutdown complete")

def main():
    """Main entry point"""
    try:
        producer = BinanceKafkaProducer()
        producer.produce_market_data(interval_seconds=60)
    except Exception as e:
        logger.error(f"❌ Failed to start producer: {e}")
        logger.error("\n🔍 Troubleshooting:")
        logger.error("   1. Ensure Kafka is running: docker-compose up -d kafka")
        logger.error("   2. Check Kafka logs: docker logs crypto_kafka")
        logger.error("   3. Verify .env file: KAFKA_BOOTSTRAP_SERVERS=localhost:9092")
        sys.exit(1)

if __name__ == "__main__":
    main()
