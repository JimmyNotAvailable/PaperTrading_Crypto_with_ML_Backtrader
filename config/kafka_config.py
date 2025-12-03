"""
Kafka configuration module

Centralized Kafka settings for the Crypto ML Trading Project.
Follows copilot-instructions.md patterns for path handling and env variables.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback if python-dotenv not installed
    pass

def get_kafka_producer_config() -> Dict[str, Any]:
    """
    Get Kafka producer configuration
    
    Returns:
        Dict with producer settings following best practices from RESTRUCTURING_PLAN_KAFKA.md
    """
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'client.id': os.getenv('KAFKA_CLIENT_ID', 'crypto_producer'),
        'compression.type': 'gzip',  # Tiết kiệm bandwidth
        'acks': 'all',  # Đảm bảo message không mất
        'retries': 3,
        'max.in.flight.requests.per.connection': 1,  # Đảm bảo ordering
        'linger.ms': 10,  # Batch messages for better throughput
        'batch.size': 16384  # 16KB batch size
    }

def get_kafka_consumer_config(group_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Kafka consumer configuration
    
    Args:
        group_id: Consumer group ID (default from env)
    
    Returns:
        Dict with consumer settings
    """
    if group_id is None:
        group_id = os.getenv('KAFKA_GROUP_ID', 'crypto_ml_group')
    
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': group_id,
        'client.id': os.getenv('KAFKA_CLIENT_ID', 'crypto_consumer'),
        'auto.offset.reset': 'latest',  # Chỉ đọc message mới
        'enable.auto.commit': True,
        'auto.commit.interval.ms': 5000,
        'max.poll.records': 100,
        'session.timeout.ms': 30000,
        'heartbeat.interval.ms': 10000
    }

def get_kafka_admin_config() -> Dict[str, Any]:
    """
    Get Kafka admin client configuration
    
    Returns:
        Dict with admin client settings
    """
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    }

# Kafka Topics
class KafkaTopics:
    """Kafka topic names - centralized definition"""
    MARKET_DATA = 'crypto.market_data'
    ML_SIGNALS = 'crypto.ml_signals'
    ORDERS = 'crypto.orders'
    
    @classmethod
    def all_topics(cls):
        """Get list of all topic names"""
        return [cls.MARKET_DATA, cls.ML_SIGNALS, cls.ORDERS]
