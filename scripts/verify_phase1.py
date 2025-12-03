#!/usr/bin/env python3
"""
Test Script: Verify Phase 1 Infrastructure Setup

Kiểm tra:
- ✅ All required packages installed
- ✅ Config modules load correctly  
- ✅ Logger works properly
- ✅ Environment variables can be loaded
- ✅ Kafka configuration is valid

Usage:
    python scripts/verify_phase1.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test tất cả imports cần thiết"""
    print("🔍 Testing imports...")
    
    try:
        # Core dependencies
        try:
            import confluent_kafka
            print(f"  ✅ confluent_kafka: {confluent_kafka.version()}")
        except ImportError:
            print(f"  ❌ confluent_kafka: NOT INSTALLED")
            print(f"     💡 Run: pip install confluent-kafka")
            raise
        
        try:
            import requests
            print(f"  ✅ requests: {requests.__version__}")
        except ImportError:
            print(f"  ❌ requests: NOT INSTALLED")
            print(f"     💡 Run: pip install requests")
            raise
        
        try:
            import dotenv
            print(f"  ✅ python-dotenv: OK")
        except ImportError:
            print(f"  ❌ python-dotenv: NOT INSTALLED")
            print(f"     💡 Run: pip install python-dotenv")
            raise
        
        # Project modules
        from app.utils.logger import get_logger
        print(f"  ✅ app.utils.logger: OK")
        
        from app.utils.config_loader import (
            get_kafka_bootstrap_servers,
            get_discord_token
        )
        print(f"  ✅ app.utils.config_loader: OK")
        
        from config.kafka_config import (
            get_kafka_producer_config,
            get_kafka_consumer_config,
            KafkaTopics
        )
        print(f"  ✅ config.kafka_config: OK")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_logger():
    """Test logger functionality"""
    print("\n🔍 Testing logger...")
    
    try:
        from app.utils.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Test log message")
        print("  ✅ Logger works correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Logger failed: {e}")
        return False

def test_config_loader():
    """Test config loader"""
    print("\n🔍 Testing config loader...")
    
    try:
        from app.utils.config_loader import (
            get_kafka_bootstrap_servers,
            get_kafka_group_id,
            get_mongodb_uri,
            get_log_level
        )
        
        kafka_servers = get_kafka_bootstrap_servers()
        print(f"  ✅ Kafka servers: {kafka_servers}")
        
        group_id = get_kafka_group_id()
        print(f"  ✅ Kafka group ID: {group_id}")
        
        mongo_uri = get_mongodb_uri()
        print(f"  ✅ MongoDB URI: {mongo_uri}")
        
        log_level = get_log_level()
        print(f"  ✅ Log level: {log_level}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Config loader failed: {e}")
        return False

def test_kafka_config():
    """Test Kafka configuration"""
    print("\n🔍 Testing Kafka config...")
    
    try:
        from config.kafka_config import (
            get_kafka_producer_config,
            get_kafka_consumer_config,
            KafkaTopics
        )
        
        producer_config = get_kafka_producer_config()
        print(f"  ✅ Producer config: {producer_config['bootstrap.servers']}")
        
        consumer_config = get_kafka_consumer_config()
        print(f"  ✅ Consumer config: {consumer_config['group.id']}")
        
        topics = KafkaTopics.all_topics()
        print(f"  ✅ Topics defined: {', '.join(topics)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Kafka config failed: {e}")
        return False

def test_env_file():
    """Test .env file exists"""
    print("\n🔍 Checking .env file...")
    
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if env_file.exists():
        print(f"  ✅ .env file exists")
        return True
    else:
        print(f"  ⚠️ .env file NOT found")
        print(f"  💡 Create it from template:")
        print(f"     cp .env.example .env")
        if env_example.exists():
            print(f"  ✅ .env.example template available")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("🚀 PHASE 1 INFRASTRUCTURE VERIFICATION")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Logger", test_logger()))
    results.append(("Config Loader", test_config_loader()))
    results.append(("Kafka Config", test_kafka_config()))
    results.append(("Environment File", test_env_file()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("="*60)
    if all_passed:
        print("✅ All tests passed! Phase 1 infrastructure is ready.")
        print("\n📝 Next steps:")
        print("   1. Start Kafka: docker-compose up -d")
        print("   2. Init topics: python scripts/init_kafka_topics.py")
        print("   3. Test producer: python app/producers/binance_producer.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\n🔍 Troubleshooting:")
        print("   1. Ensure virtual environment is activated")
        print("   2. Install dependencies: pip install -r requirements.txt")
        print("   3. Create .env file: cp .env.example .env")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
