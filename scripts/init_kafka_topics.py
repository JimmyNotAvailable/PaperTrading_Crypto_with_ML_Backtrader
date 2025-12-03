#!/usr/bin/env python3
"""
Khởi tạo Kafka topics cho Crypto ML Trading Project

Topics được tạo:
- crypto.market_data: OHLCV data từ Binance (24h retention)
- crypto.ml_signals: ML predictions với confidence (7d retention)
- crypto.orders: Trading decisions từ Backtrader (30d retention)

Usage:
    python scripts/init_kafka_topics.py
"""

import logging
import sys

try:
    from confluent_kafka.admin import AdminClient, NewTopic
except ImportError as e:
    print("❌ Error: confluent-kafka not installed")
    print("💡 Install it: pip install confluent-kafka")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_topics():
    """Tạo các Kafka topics cần thiết"""
    
    try:
        admin_client = AdminClient({
            'bootstrap.servers': 'localhost:9092'
        })
        
        topics = [
            NewTopic(
                topic='crypto.market_data',
                num_partitions=3,
                replication_factor=1,
                config={
                    'retention.ms': '86400000',  # 24 hours
                    'compression.type': 'gzip',
                    'cleanup.policy': 'delete'
                }
            ),
            NewTopic(
                topic='crypto.ml_signals',
                num_partitions=3,
                replication_factor=1,
                config={
                    'retention.ms': '604800000',  # 7 days
                    'compression.type': 'gzip',
                    'cleanup.policy': 'delete'
                }
            ),
            NewTopic(
                topic='crypto.orders',
                num_partitions=1,
                replication_factor=1,
                config={
                    'retention.ms': '2592000000',  # 30 days
                    'compression.type': 'gzip',
                    'cleanup.policy': 'compact'
                }
            )
        ]
        
        logger.info("🚀 Creating Kafka topics...")
        
        # Tạo topics
        fs = admin_client.create_topics(topics, validate_only=False)
        
        # Wait for operation to finish
        for topic, f in fs.items():
            try:
                f.result()  # Block until topic is created
                logger.info(f"✅ Topic '{topic}' created successfully")
            except Exception as e:
                error_msg = str(e)
                if "Topic already exists" in error_msg or "TOPIC_ALREADY_EXISTS" in error_msg:
                    logger.warning(f"⚠️ Topic '{topic}' already exists, skipping...")
                else:
                    logger.error(f"❌ Failed to create topic '{topic}': {e}")
                    raise
        
        logger.info("✅ All Kafka topics initialized successfully!")
        logger.info("📊 Topics created:")
        logger.info("   - crypto.market_data (3 partitions, 24h retention)")
        logger.info("   - crypto.ml_signals (3 partitions, 7d retention)")
        logger.info("   - crypto.orders (1 partition, 30d retention)")
        logger.info("\n💡 Verify topics at: http://localhost:8080 (Kafka UI)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating topics: {e}")
        logger.error("\n🔍 Troubleshooting:")
        logger.error("   1. Ensure Kafka is running: docker-compose up -d kafka")
        logger.error("   2. Check Kafka logs: docker logs crypto_kafka")
        logger.error("   3. Verify bootstrap server: localhost:9092")
        return False

if __name__ == "__main__":
    success = create_topics()
    sys.exit(0 if success else 1)
