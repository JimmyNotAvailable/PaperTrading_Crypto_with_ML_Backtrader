"""
ML Predictor Consumer Service
==============================
Real-time ML prediction service that:
1. Consumes market data from Kafka topic 'crypto.market_data'
2. Maintains buffer of recent candles for feature calculation
3. Uses ensemble of 3 models (Random Forest, SVM, Logistic Regression)
4. Produces predictions to Kafka topic 'crypto.ml_signals'

Architecture follows Step_3.md and ToturialUpgrade.md guidelines.
"""

import json
import os
import sys
import joblib
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional
from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.feature_engineering import calculate_features, get_feature_columns
from config.symbols_config import (
    get_base_symbol, is_valid_symbol, get_symbol_info
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class MLPredictor:
    """
    Real-time ML prediction service with buffer and ensemble models.
    """
    
    def __init__(self):
        # Kafka configuration
        self.consumer = Consumer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'group.id': 'ml_predictor_group',
            'auto.offset.reset': 'latest'
        })
        
        self.producer = Producer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        })
        
        self.consumer.subscribe(['crypto.market_data'])
        self.produce_topic = 'crypto.ml_signals'
        
        # Load models
        models_dir = Path(__file__).parent.parent / 'ml' / 'models'
        logger.info("⏳ Loading ML models...")
        
        # Models storage: {symbol: {rf, svm, lr}}
        self.models: Dict[str, Dict] = {}
        
        # Data buffer per symbol - need 52 candles minimum (50 for SMA_50 + 2 for safety)
        self.data_buffers: Dict[str, List[Dict]] = {}
        self.min_required_data = 52
        
        # Statistics per symbol
        self.predictions_count: Dict[str, int] = {}
        self.signals_buy: Dict[str, int] = {}
        self.signals_sell: Dict[str, int] = {}
        self.signals_neutral: Dict[str, int] = {}
    
    def load_models_for_symbol(self, symbol: str) -> bool:
        """
        Load ML models for a specific symbol.
        
        Args:
            symbol: Symbol to load models for
            
        Returns:
            True if successful, False otherwise
        """
        base = get_base_symbol(symbol)
        
        if base in self.models:
            return True  # Already loaded
        
        models_dir = Path(__file__).parent.parent / 'ml' / 'models'
        
        try:
            # Improved model paths with feature metadata
            rf_path = models_dir / f'improved_random_forest_{base}_latest.joblib'
            svm_path = models_dir / f'improved_svm_{base}_latest.joblib'
            lr_path = models_dir / f'improved_logistic_regression_{base}_latest.joblib'
            features_path = models_dir / f'improved_features_{base}.json'
            
            # Check if improved models exist
            if not all([rf_path.exists(), svm_path.exists(), lr_path.exists(), features_path.exists()]):
                logger.warning(f"⚠️ Improved models not found for {base}")
                logger.info(f"   Please run: python app/ml/improved_train_models.py --symbol {base} --historical 5000 --quick")
                return False
            
            # Load feature metadata
            with open(features_path, 'r') as f:
                features_meta = json.load(f)
                selected_features = features_meta['selected_features']
                logger.info(f"📋 [{base}] Loaded {len(selected_features)} selected features")
            
            self.models[base] = {
                'rf': joblib.load(rf_path),
                'svm': joblib.load(svm_path),
                'lr': joblib.load(lr_path),
                'selected_features': selected_features  # Store features with models
            }
            
            # Initialize tracking for this symbol
            self.data_buffers[base] = []
            self.predictions_count[base] = 0
            self.signals_buy[base] = 0
            self.signals_sell[base] = 0
            self.signals_neutral[base] = 0
            
            logger.info(f"✅ Loaded improved models for {base} (4h trend prediction)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load models for {base}: {e}")
            return False
    
    def predict(self, current_data: Dict) -> None:
        """
        Process incoming message with pre-calculated features and generate prediction.
        
        Args:
            current_data: Dictionary with features already calculated by producer
                         Format: {'symbol': str, 'timestamp': int, 'price': float, 
                                  'features': dict, 'n_features': int}
        """
        symbol = current_data.get('symbol', 'BTCUSDT')
        base = get_base_symbol(symbol)
        
        # Load models for this symbol if not already loaded
        if not self.load_models_for_symbol(symbol):
            return  # Skip if models not available
        
        # Check if message has pre-calculated features (new format)
        if 'features' in current_data and isinstance(current_data['features'], dict):
            # NEW FORMAT: Features already calculated by producer
            features_dict = current_data['features']
            
            # Get models and selected features for this symbol
            models = self.models[base]
            selected_features = models['selected_features']  # 10 features from RFE
            
            # Verify all required features are present
            missing_features = [f for f in selected_features if f not in features_dict]
            if missing_features:
                logger.warning(f"⚠️ [{base}] Missing features: {missing_features}")
                return
            
            try:
                # Create DataFrame from features dict (single row)
                last_row = pd.DataFrame([{f: features_dict[f] for f in selected_features}])
            except Exception as e:
                logger.error(f"❌ [{base}] Error creating DataFrame from features: {e}")
                return
            
        else:
            # OLD FORMAT: Raw OHLCV data, need to calculate features
            # Add to buffer for this symbol
            self.data_buffers[base].append(current_data)
            
            # Maintain buffer size (keep last 100 candles)
            if len(self.data_buffers[base]) > 100:
                self.data_buffers[base].pop(0)
            
            # Check if we have enough data (Cold Start problem)
            if len(self.data_buffers[base]) < self.min_required_data:
                logger.info(
                    f"⏳ [{base}] Accumulating data: {len(self.data_buffers[base])}/{self.min_required_data}"
                )
                return
            
            try:
                # Create DataFrame from buffer
                df = pd.DataFrame(self.data_buffers[base])
                
                # Calculate features using shared module (ensures consistency)
                df_features = calculate_features(df, include_target=False)
                
                if df_features.empty:
                    logger.warning(f"⚠️ [{base}] Feature calculation returned empty DataFrame")
                    return
                
                # Get models and selected features for this symbol
                models = self.models[base]
                selected_features = models['selected_features']  # 10 features from RFE
                
                # Get only selected features (10 features from RFE)
                last_row = df_features.iloc[[-1]][selected_features]
                
            except Exception as e:
                logger.error(f"❌ [{base}] Error calculating features: {e}")
                return
        
        try:
            # Get models
            models = self.models[base]
            
            # Predict with all 3 improved models (calibrated)
            rf_pred = models['rf'].predict(last_row)[0]
            rf_prob = models['rf'].predict_proba(last_row)[0][1]  # Calibrated probability
            svm_pred = models['svm'].predict(last_row)[0]
            svm_prob = models['svm'].predict_proba(last_row)[0][1]  # Calibrated probability
            lr_pred = models['lr'].predict(last_row)[0]
            lr_prob = models['lr'].predict_proba(last_row)[0][1]  # Calibrated probability
            
            # Ensemble logic with 2/3 majority voting (4h trend prediction)
            # Lower confidence threshold (55-60%) for 4h targets vs 60% for 1h
            votes_up = sum([rf_pred == 1, svm_pred == 1, lr_pred == 1])
            votes_down = sum([rf_pred == 0, svm_pred == 0, lr_pred == 0])
            avg_confidence = (rf_prob + svm_prob + lr_prob) / 3
            
            signal = "NEUTRAL"
            
            if votes_up >= 2 and avg_confidence > 0.55:  # 2/3 majority + 55% confidence
                signal = "BUY"
                self.signals_buy[base] += 1
            elif votes_down >= 2 and avg_confidence < 0.45:  # 2/3 majority DOWN
                signal = "SELL"
                self.signals_sell[base] += 1
            else:
                self.signals_neutral[base] += 1
            
            # Prepare result payload with 4h prediction metadata
            price = current_data.get('price', current_data.get('close', 0))
            
            result = {
                "timestamp": int(current_data['timestamp']),  # Convert to native int
                "symbol": str(current_data['symbol']),  # Ensure string
                "price": float(price),  # Ensure float
                "signal": signal,
                "prediction_type": "4h_trend",  # NEW: Indicates 4-hour trend prediction
                "hold_periods": 4,  # NEW: Recommended hold duration (4 candles)
                "details": {
                    "random_forest": {
                        "prediction": int(rf_pred),
                        "confidence": round(float(rf_prob), 4)
                    },
                    "svm": {
                        "prediction": int(svm_pred),
                        "confidence": round(float(svm_prob), 4)
                    },
                    "logistic_regression": {
                        "prediction": int(lr_pred),
                        "confidence": round(float(lr_prob), 4)
                    },
                    "ensemble": {
                        "votes_up": int(votes_up),  # Convert to native int
                        "votes_down": int(votes_down),  # Convert to native int
                        "avg_confidence": round(float(avg_confidence), 4)
                    }
                },
                "features": {
                    "close": float(last_row['close'].iloc[0]) if 'close' in selected_features else None,
                    "SMA_10": float(last_row['SMA_10'].iloc[0]) if 'SMA_10' in selected_features else None,
                    "SMA_50": float(last_row['SMA_50'].iloc[0]) if 'SMA_50' in selected_features else None,
                    "RSI_14": float(last_row['RSI_14'].iloc[0]) if 'RSI_14' in selected_features else None,
                    "MACD": float(last_row['MACD'].iloc[0]) if 'MACD' in selected_features else None,
                    "MACD_hist": float(last_row['MACD_hist'].iloc[0]) if 'MACD_hist' in selected_features else None,
                    "BB_LOWER": float(last_row['BB_LOWER'].iloc[0]) if 'BB_LOWER' in selected_features else None,
                    "Volume_SMA": float(last_row['Volume_SMA'].iloc[0]) if 'Volume_SMA' in selected_features else None,
                    "Volatility_20": float(last_row['Volatility_20'].iloc[0]) if 'Volatility_20' in selected_features else None,
                    "Returns_5": float(last_row['Returns_5'].iloc[0]) if 'Returns_5' in selected_features else None
                }
            }
            
            # Send to Kafka
            self.producer.produce(
                self.produce_topic,
                json.dumps(result).encode('utf-8')
            )
            self.producer.flush()
            
            self.predictions_count[base] += 1
            
            # Log prediction with 4h context
            signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            logger.info(
                f"{signal_emoji} [{base}:{self.predictions_count[base]}] {signal} (4h trend) | "
                f"Price: ${price:,.2f} | "
                f"Votes: {votes_up}↑/{votes_down}↓ | "
                f"Avg Conf: {avg_confidence:.2%} | "
                f"RF:{rf_prob:.2f} SVM:{svm_prob:.2f} LR:{lr_prob:.2f}"
            )
            
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self) -> None:
        """Start the ML prediction service."""
        logger.info("🚀 ML Predictor Service Started...")
        logger.info(f"📡 Consuming from: crypto.market_data")
        logger.info(f"📤 Producing to: {self.produce_topic}")
        logger.info(f"🔄 Minimum data required: {self.min_required_data} candles")
        logger.info("-" * 60)
        
        try:
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"Kafka error: {msg.error()}")
                    continue
                
                # Decode message
                data = json.loads(msg.value().decode('utf-8'))
                
                # Make prediction
                self.predict(data)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Service interrupted by user")
        finally:
            self.consumer.close()
            logger.info(f"\n📊 Session statistics:")
            logger.info("=" * 60)
            
            for symbol in self.predictions_count.keys():
                total = self.predictions_count.get(symbol, 0)
                if total > 0:
                    logger.info(f"\n{symbol}:")
                    logger.info(f"   Total predictions: {total}")
                    logger.info(f"   BUY signals: {self.signals_buy.get(symbol, 0)}")
                    logger.info(f"   SELL signals: {self.signals_sell.get(symbol, 0)}")
                    logger.info(f"   NEUTRAL: {self.signals_neutral.get(symbol, 0)}")
            
            logger.info("\n" + "=" * 60)
            logger.info("🛑 ML Predictor Service Stopped")


if __name__ == "__main__":
    try:
        service = MLPredictor()
        service.start()
    except Exception as e:
        logger.error(f"❌ Failed to start service: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
