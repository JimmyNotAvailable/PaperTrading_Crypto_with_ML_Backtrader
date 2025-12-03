"""
ensemble_predictor.py
=====================
Ensemble predictor với confidence voting cho 3 models
Chỉ trade khi ≥2/3 models đồng ý và confidence ≥60%

Tích hợp với Kafka consumer để gửi signals đến Backtrader
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from typing import Dict, Tuple, Optional, List
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from config.symbols_config import get_base_symbol

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models directory
MODELS_DIR = PROJECT_ROOT / "app" / "ml" / "models"


class EnsemblePredictor:
    """
    Ensemble của 3 models với confidence-weighted voting
    
    Strategy:
    - Load 3 optimized models (RF, SVM, LR)
    - Mỗi model vote UP/DOWN với confidence score
    - Chỉ trade khi ≥2/3 models đồng ý VÀ confidence ≥ threshold
    - Ngược lại: signal = NEUTRAL (không trade)
    """
    
    def __init__(self, symbol: str = 'BTC/USDT', confidence_threshold: float = 0.60,
                 use_optimized: bool = True):
        """
        Args:
            symbol: Trading pair
            confidence_threshold: Minimum confidence để trade (default 0.60 = 60%)
            use_optimized: Dùng optimized models hay baseline models
        """
        self.symbol = symbol
        self.base = get_base_symbol(symbol)
        self.confidence_threshold = confidence_threshold
        self.use_optimized = use_optimized
        
        self.models = {}
        self.metadata = None
        self.feature_cols = []
        self.scalers = None
        
        self.load_models()
        
    def load_models(self):
        """Load 3 models từ disk"""
        prefix = "optimized_" if self.use_optimized else ""
        model_types = ['random_forest', 'svm', 'logistic_regression']
        
        logger.info(f"📂 Loading {'optimized' if self.use_optimized else 'baseline'} models for {self.base}...")
        
        for model_type in model_types:
            model_path = MODELS_DIR / f"{prefix}{model_type}_{self.base}_latest.joblib"
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model not found: {model_path}\n"
                    f"Please run: python app/ml/{'optimized_' if self.use_optimized else ''}train_models.py --symbol {self.base}"
                )
            
            self.models[model_type] = joblib.load(model_path)
            logger.info(f"✅ Loaded {model_type}")
        
        # Load metadata
        metadata_path = MODELS_DIR / f"{prefix}metadata_{self.base}_latest.joblib"
        
        if metadata_path.exists():
            self.metadata = joblib.load(metadata_path)
            self.feature_cols = self.metadata.get('feature_cols', [])
            self.scalers = self.metadata.get('scalers', {})
            logger.info(f"✅ Loaded metadata: {len(self.feature_cols)} features")
        else:
            logger.warning(f"⚠️ Metadata not found, will use default feature columns")
    
    def prepare_features(self, market_data: Dict) -> pd.DataFrame:
        """
        Chuẩn bị features từ market data
        
        Args:
            market_data: Dict với OHLCV + indicators
            {
                'open': 96000, 'high': 96500, 'low': 95800, 'close': 96200,
                'volume': 15000, 'SMA_10': 95900, 'RSI_14': 58.3, ...
            }
        
        Returns:
            DataFrame với features đã scaled
        """
        # Convert dict to DataFrame
        df = pd.DataFrame([market_data])
        
        # Ensure correct column order
        if self.feature_cols:
            # Reindex to match training features
            df = df.reindex(columns=self.feature_cols, fill_value=0)
        
        # Apply scaling if available
        if self.scalers and self.symbol in self.scalers:
            scaler = self.scalers[self.symbol]
            df[self.feature_cols] = scaler.transform(df[self.feature_cols])
        
        return df
    
    def predict_single_model(self, model_name: str, features: pd.DataFrame) -> Tuple[int, float]:
        """
        Dự đoán từ 1 model
        
        Returns:
            (prediction, confidence)
            - prediction: 0=DOWN, 1=UP
            - confidence: 0.0-1.0
        """
        model = self.models[model_name]
        
        # Prediction
        pred = model.predict(features)[0]
        
        # Confidence (probability của class dự đoán)
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(features)[0]
            confidence = proba[pred]  # Confidence của class được chọn
        else:
            # Fallback nếu model không có predict_proba
            confidence = 0.5
        
        return int(pred), float(confidence)
    
    def ensemble_predict(self, market_data: Dict) -> Dict:
        """
        Ensemble prediction với confidence voting
        
        Args:
            market_data: Dict với OHLCV + indicators
        
        Returns:
            {
                'signal': 'BUY' | 'SELL' | 'NEUTRAL',
                'confidence': 0.0-1.0,
                'votes': {'UP': 2, 'DOWN': 1},
                'individual_predictions': {
                    'random_forest': {'pred': 1, 'conf': 0.72},
                    'svm': {'pred': 1, 'conf': 0.65},
                    'logistic_regression': {'pred': 0, 'conf': 0.55}
                },
                'should_trade': True/False
            }
        """
        # Prepare features
        features = self.prepare_features(market_data)
        
        # Collect predictions from all models
        votes = {'UP': 0, 'DOWN': 0}
        confidences = []
        individual_preds = {}
        
        for model_name in self.models.keys():
            pred, conf = self.predict_single_model(model_name, features)
            
            vote = 'UP' if pred == 1 else 'DOWN'
            votes[vote] += 1
            confidences.append(conf)
            
            individual_preds[model_name] = {'pred': pred, 'conf': conf}
        
        # Determine final signal
        if votes['UP'] > votes['DOWN']:
            signal = 'BUY'
            avg_confidence = np.mean([p['conf'] for p in individual_preds.values() if p['pred'] == 1])
        elif votes['DOWN'] > votes['UP']:
            signal = 'SELL'
            avg_confidence = np.mean([p['conf'] for p in individual_preds.values() if p['pred'] == 0])
        else:
            # Tie - không trade
            signal = 'NEUTRAL'
            avg_confidence = np.mean(confidences)
        
        # Apply confidence threshold
        should_trade = (
            signal != 'NEUTRAL' and 
            avg_confidence >= self.confidence_threshold and
            max(votes.values()) >= 2  # Ít nhất 2/3 models đồng ý
        )
        
        if not should_trade and signal != 'NEUTRAL':
            signal = 'NEUTRAL'  # Override signal nếu confidence thấp
        
        return {
            'signal': signal,
            'confidence': float(avg_confidence),
            'votes': votes,
            'individual_predictions': individual_preds,
            'should_trade': should_trade,
            'symbol': self.symbol,
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def get_signal_explanation(self, result: Dict) -> str:
        """Generate human-readable explanation của prediction"""
        lines = [
            f"\n{'='*60}",
            f"🔮 ENSEMBLE PREDICTION - {result['symbol']}",
            f"{'='*60}",
            f"Signal: {result['signal']}",
            f"Confidence: {result['confidence']:.2%}",
            f"Votes: UP={result['votes']['UP']}, DOWN={result['votes']['DOWN']}",
            f"Should Trade: {'✅ YES' if result['should_trade'] else '❌ NO'}",
            f"\nIndividual Models:"
        ]
        
        for model_name, pred in result['individual_predictions'].items():
            signal = 'UP' if pred['pred'] == 1 else 'DOWN'
            lines.append(f"  {model_name:<25} {signal:<6} (conf: {pred['conf']:.2%})")
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)


def test_ensemble():
    """Test ensemble predictor với sample data"""
    logger.info("🧪 Testing Ensemble Predictor...")
    
    # Sample market data (cần có đầy đủ features từ feature_engineering.py)
    sample_data = {
        'open': 96000.0,
        'high': 96500.0,
        'low': 95800.0,
        'close': 96200.0,
        'volume': 15000.0,
        'SMA_10': 95900.0,
        'SMA_50': 94500.0,
        'EMA_12': 96100.0,
        'EMA_26': 95700.0,
        'RSI_14': 58.3,
        'MACD': 150.0,
        'MACD_signal': 120.0,
        'MACD_hist': 30.0,
        'BB_UPPER': 97000.0,
        'BB_MID': 96000.0,
        'BB_LOWER': 95000.0,
        'BB_WIDTH': 0.021,
        'ATR_14': 500.0,
        'Volume_SMA': 14000.0,
        'Volume_Ratio': 1.07,
        'Price_Change_Pct': 0.5,
        'Volatility_20': 0.015,
        'HL_Ratio': 0.0073,
        'Returns_1': 0.002,
        'Returns_5': 0.015,
        'Returns_10': 0.025
    }
    
    # Create ensemble
    ensemble = EnsemblePredictor(
        symbol='BTC/USDT',
        confidence_threshold=0.60,
        use_optimized=True
    )
    
    # Predict
    result = ensemble.ensemble_predict(sample_data)
    
    # Show results
    print(ensemble.get_signal_explanation(result))
    
    # Test with different thresholds
    logger.info("\n🔬 Testing different confidence thresholds:")
    for threshold in [0.50, 0.60, 0.70]:
        ensemble.confidence_threshold = threshold
        result = ensemble.ensemble_predict(sample_data)
        logger.info(f"  Threshold {threshold:.0%}: Signal={result['signal']}, Should Trade={result['should_trade']}")


if __name__ == "__main__":
    test_ensemble()
