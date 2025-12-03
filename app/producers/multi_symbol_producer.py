"""
Multi-Symbol Market Data Producer
==================================
Enhanced version that can produce data for multiple symbols simultaneously.
Supports BTC, ETH, XRP, SOL, BNB.

Usage:
    # Single symbol (default BTC)
    python app/producers/multi_symbol_producer.py
    
    # All symbols
    python app/producers/multi_symbol_producer.py --all
    
    # Specific symbols
    python app/producers/multi_symbol_producer.py --symbols BTC ETH XRP
"""
import json
import time
import os
import ccxt
import logging
import argparse
import sys
from pathlib import Path
from confluent_kafka import Producer
from dotenv import load_dotenv
from typing import List
from concurrent.futures import ThreadPoolExecutor

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.symbols_config import (
    SUPPORTED_SYMBOLS, normalize_symbol, get_base_symbol, 
    get_binance_format, get_all_symbols
)

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


class MultiSymbolProducer:
    """Producer that can handle multiple symbols simultaneously."""
    
    def __init__(self, symbols: List[str] = None, timeframe: str = '1m'):
        """
        Initialize Multi-Symbol Producer.
        
        Args:
            symbols: List of symbols to track (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframe: Timeframe for candles (1m, 5m, 1h, etc.)
        """
        self.symbols = symbols or ['BTC/USDT']
        self.timeframe = timeframe
        
        # Normalize all symbols
        self.symbols = [normalize_symbol(s) for s in self.symbols]
        
        # Kafka Producer
        kafka_conf = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'client.id': 'crypto-multi-producer',
            'retries': 5
        }
        self.producer = Producer(kafka_conf)
        self.topic = 'crypto.market_data'
        
        # Binance connection via CCXT
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        logger.info(f"🚀 Multi-Symbol Producer initialized")
        logger.info(f"📊 Tracking {len(self.symbols)} symbols: {', '.join([get_base_symbol(s) for s in self.symbols])}")
        logger.info(f"⏰ Timeframe: {self.timeframe}")
    
    def delivery_report(self, err, msg):
        """Callback for message delivery confirmation."""
        if err is not None:
            logger.error(f'❌ Send failed: {err}')
        else:
            logger.debug(f'✅ Sent {msg.key().decode("utf-8")} to {msg.topic()}')
    
    def fetch_and_send_single(self, symbol: str) -> bool:
        """
        Fetch data for a single symbol and send to Kafka.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch latest candle
            candles = self.exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=1)
            
            if not candles:
                logger.warning(f"⚠️ [{get_base_symbol(symbol)}] No data received")
                return False
            
            candle = candles[0]
            
            # Prepare payload
            payload = {
                'symbol': get_binance_format(symbol),
                'timestamp': candle[0],
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4],
                'volume': candle[5],
                'source': 'binance'
            }
            
            # Send to Kafka
            key = symbol.encode('utf-8')
            value = json.dumps(payload).encode('utf-8')
            
            self.producer.produce(
                self.topic,
                key=key,
                value=value,
                callback=self.delivery_report
            )
            self.producer.poll(0)
            
            logger.info(
                f"📡 [{get_base_symbol(symbol)}] Price: ${payload['close']:,.2f} | "
                f"Vol: {payload['volume']:,.0f}"
            )
            
            return True
            
        except ccxt.NetworkError as e:
            logger.error(f"🌐 [{get_base_symbol(symbol)}] Network error: {e}")
            return False
        except Exception as e:
            logger.error(f"🔥 [{get_base_symbol(symbol)}] Error: {e}")
            return False
    
    def fetch_and_produce_sequential(self) -> None:
        """Fetch data for all symbols sequentially (simple but slower)."""
        logger.info("🔄 Starting sequential data collection...")
        logger.info("=" * 60)
        
        while True:
            try:
                for symbol in self.symbols:
                    self.fetch_and_send_single(symbol)
                    time.sleep(0.5)  # Small delay between symbols
                
                # Wait before next round
                logger.info("⏳ Waiting 5s before next round...")
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("\n⚠️ Interrupted by user")
                break
    
    def fetch_and_produce_parallel(self) -> None:
        """Fetch data for all symbols in parallel (faster, more efficient)."""
        logger.info("🚀 Starting parallel data collection...")
        logger.info("=" * 60)
        
        with ThreadPoolExecutor(max_workers=len(self.symbols)) as executor:
            while True:
                try:
                    # Fetch all symbols in parallel
                    futures = [
                        executor.submit(self.fetch_and_send_single, symbol) 
                        for symbol in self.symbols
                    ]
                    
                    # Wait for all to complete
                    results = [f.result() for f in futures]
                    
                    success_count = sum(results)
                    logger.info(
                        f"✅ Round complete: {success_count}/{len(self.symbols)} successful"
                    )
                    
                    # Wait before next round
                    logger.info("⏳ Waiting 5s before next round...")
                    time.sleep(5)
                    
                except KeyboardInterrupt:
                    logger.info("\n⚠️ Interrupted by user")
                    break
    
    def close(self) -> None:
        """Clean up resources."""
        self.producer.flush()
        logger.info("🛑 Producer stopped")


def main():
    """Main entry point with CLI support."""
    parser = argparse.ArgumentParser(description='Multi-Symbol Crypto Data Producer')
    parser.add_argument(
        '--all',
        action='store_true',
        help='Produce data for all supported symbols (BTC, ETH, XRP, SOL, BNB)'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Specific symbols to produce (e.g., BTC ETH XRP)'
    )
    parser.add_argument(
        '--timeframe',
        default='1m',
        help='Timeframe for candles (default: 1m)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel fetching (faster, recommended for multiple symbols)'
    )
    
    args = parser.parse_args()
    
    # Determine symbols
    if args.all:
        symbols = get_all_symbols()
    elif args.symbols:
        symbols = [normalize_symbol(s) for s in args.symbols]
    else:
        symbols = ['BTC/USDT']  # Default
    
    # Create producer
    producer = MultiSymbolProducer(symbols=symbols, timeframe=args.timeframe)
    
    try:
        if args.parallel and len(symbols) > 1:
            producer.fetch_and_produce_parallel()
        else:
            producer.fetch_and_produce_sequential()
    except KeyboardInterrupt:
        pass
    finally:
        producer.close()


if __name__ == "__main__":
    main()
