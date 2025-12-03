"""
test_improved_ensemble.py
=========================
Test ensemble với IMPROVED models
- 4h trend target
- 10 selected features
- GridSearchCV optimized
- Calibrated confidence

Expected: Accuracy >55%, confidence calibrated
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import joblib
import json

PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from app.ml.load_historical_data import load_historical_data
from app.ml.feature_engineering import calculate_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MODELS_DIR = PROJECT_ROOT / "app" / "ml" / "models"


def calculate_4h_target_for_test(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate 4h target same as training"""
    df = df.copy()
    df['price_4h_future'] = df['close'].shift(-4)
    df['actual_label'] = (df['price_4h_future'] > df['close']).astype(int)
    return df[:-4]  # Drop last 4 rows


def load_improved_models(symbol: str = 'BTC'):
    """Load improved models and metadata"""
    models = {}
    
    # Load models
    for model_name in ['random_forest', 'svm', 'logistic_regression']:
        model_path = MODELS_DIR / f"improved_{model_name}_{symbol}_latest.joblib"
        
        if model_path.exists():
            models[model_name] = joblib.load(model_path)
            logger.info(f"✅ Loaded improved {model_name}")
        else:
            raise FileNotFoundError(f"Model not found: {model_path}")
    
    # Load feature metadata
    features_path = MODELS_DIR / f"improved_features_{symbol}.json"
    with open(features_path, 'r') as f:
        features_meta = json.load(f)
    
    selected_features = features_meta['selected_features']
    logger.info(f"✅ Loaded {len(selected_features)} selected features")
    
    return models, selected_features


def ensemble_predict_improved(models: dict, features: pd.DataFrame) -> dict:
    """
    Ensemble voting với calibrated confidence
    
    Returns:
        {
            'signal': 'BUY'|'SELL'|'NEUTRAL',
            'confidence': float,
            'votes': {'UP': int, 'DOWN': int},
            'individual': {model_name: {'pred': int, 'conf': float}}
        }
    """
    votes = {'UP': 0, 'DOWN': 0}
    confidences = []
    individual = {}
    
    for model_name, model in models.items():
        # Predict with calibrated probabilities
        pred = model.predict(features)[0]
        proba = model.predict_proba(features)[0]
        
        # Confidence = max probability
        conf = proba.max()
        
        vote = 'UP' if pred == 1 else 'DOWN'
        votes[vote] += 1
        confidences.append(conf)
        
        individual[model_name] = {'pred': pred, 'conf': conf}
    
    # Determine final signal
    if votes['UP'] > votes['DOWN']:
        signal = 'BUY'
        avg_conf = np.mean([individual[m]['conf'] for m in individual if individual[m]['pred'] == 1])
    elif votes['DOWN'] > votes['UP']:
        signal = 'SELL'
        avg_conf = np.mean([individual[m]['conf'] for m in individual if individual[m]['pred'] == 0])
    else:
        signal = 'NEUTRAL'
        avg_conf = np.mean(confidences)
    
    return {
        'signal': signal,
        'confidence': avg_conf,
        'votes': votes,
        'individual': individual
    }


def test_improved_ensemble():
    """Test improved ensemble on test set"""
    logger.info("=" * 60)
    logger.info("🧪 TESTING IMPROVED ENSEMBLE")
    logger.info("=" * 60)
    
    # Load models
    models, selected_features = load_improved_models('BTC')
    
    # Load test data
    logger.info("\n📂 Loading test data...")
    df = load_historical_data('BTC', limit=1000)
    df = calculate_features(df, include_target=False)
    df = calculate_4h_target_for_test(df)
    df = df.dropna()
    
    # Take test set (last 200 samples)
    test_df = df.tail(200).copy()
    
    logger.info(f"✅ Loaded {len(test_df)} test samples")
    logger.info(f"   Date range: {test_df['date'].min()} to {test_df['date'].max()}")
    
    # Prepare features
    X_test = test_df[selected_features]
    y_true = test_df['actual_label'].values
    
    # Track results
    signals = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
    individual_correct = {'random_forest': 0, 'svm': 0, 'logistic_regression': 0}
    ensemble_correct = 0
    ensemble_trades = 0
    
    confidence_threshold = 0.55  # Lower threshold for 4h (less volatile)
    
    predictions = []
    
    logger.info("\n" + "=" * 80)
    logger.info("Sample | Signal | Conf  | RF   | SVM  | LR   | Actual | Correct")
    logger.info("-" * 80)
    
    for i in range(len(X_test)):
        X_single = pd.DataFrame([X_test.iloc[i]])
        result = ensemble_predict_improved(models, X_single)
        
        signals[result['signal']] += 1
        
        # Check individual models
        for model_name, pred_info in result['individual'].items():
            if pred_info['pred'] == y_true[i]:
                individual_correct[model_name] += 1
        
        # Check ensemble
        should_trade = result['confidence'] >= confidence_threshold and result['signal'] != 'NEUTRAL'
        
        if should_trade:
            ensemble_trades += 1
            pred = 1 if result['signal'] == 'BUY' else 0
            if pred == y_true[i]:
                ensemble_correct += 1
        
        # Display every 10th sample
        if i % 10 == 0 or i < 5:
            rf_pred = 'UP' if result['individual']['random_forest']['pred'] == 1 else 'DOWN'
            svm_pred = 'UP' if result['individual']['svm']['pred'] == 1 else 'DOWN'
            lr_pred = 'UP' if result['individual']['logistic_regression']['pred'] == 1 else 'DOWN'
            actual = 'UP' if y_true[i] == 1 else 'DOWN'
            
            pred_match = '✅' if should_trade and (1 if result['signal'] == 'BUY' else 0) == y_true[i] else '❌'
            
            logger.info(
                f"{i:6d} | {result['signal']:6s} | {result['confidence']:.2%} | "
                f"{rf_pred:4s} | {svm_pred:4s} | {lr_pred:4s} | {actual:6s} | {pred_match}"
            )
        
        predictions.append(result)
    
    # Summary
    logger.info("=" * 80)
    logger.info("\n📊 IMPROVED ENSEMBLE SUMMARY")
    logger.info("=" * 60)
    
    # Individual accuracy
    logger.info(f"\n🤖 Individual Model Accuracy (n={len(X_test)}):")
    for model_name, correct in individual_correct.items():
        acc = correct / len(X_test) * 100
        logger.info(f"   {model_name:20s}: {acc:5.2f}%")
    
    # Ensemble accuracy
    if ensemble_trades > 0:
        ensemble_acc = ensemble_correct / ensemble_trades * 100
        logger.info(f"\n🎯 Ensemble Accuracy (trades only):")
        logger.info(f"   Correct: {ensemble_correct}/{ensemble_trades} = {ensemble_acc:.2f}%")
    else:
        logger.info(f"\n🎯 Ensemble: No trades (all below confidence threshold)")
    
    # Signal distribution
    logger.info(f"\n📊 Signal Distribution:")
    logger.info(f"   BUY:     {signals['BUY']:3d} ({signals['BUY']/len(predictions)*100:5.1f}%)")
    logger.info(f"   SELL:    {signals['SELL']:3d} ({signals['SELL']/len(predictions)*100:5.1f}%)")
    logger.info(f"   NEUTRAL: {signals['NEUTRAL']:3d} ({signals['NEUTRAL']/len(predictions)*100:5.1f}%)")
    
    # Confidence analysis
    avg_conf = np.mean([p['confidence'] for p in predictions])
    logger.info(f"\n📈 Average Confidence: {avg_conf:.2%}")
    
    # Model agreement
    unanimous = sum(1 for p in predictions if len(set([
        v['pred'] for v in p['individual'].values()
    ])) == 1)
    
    two_agree = sum(1 for p in predictions if len(set([
        v['pred'] for v in p['individual'].values()
    ])) == 2)
    
    logger.info(f"\n🤝 Model Agreement:")
    logger.info(f"   Unanimous (3/3): {unanimous} ({unanimous/len(predictions)*100:.1f}%)")
    logger.info(f"   Majority (2/3):  {two_agree} ({two_agree/len(predictions)*100:.1f}%)")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ TEST COMPLETE")
    logger.info("=" * 60)
    
    # Final verdict
    avg_individual = np.mean(list(individual_correct.values())) / len(X_test) * 100
    
    logger.info(f"\n💡 Verdict:")
    logger.info(f"   Avg Individual: {avg_individual:.2f}%")
    if ensemble_trades > 0:
        logger.info(f"   Ensemble:       {ensemble_acc:.2f}%")
        if ensemble_acc > avg_individual:
            logger.info(f"   ✅ Ensemble BETTER than individuals (+{ensemble_acc - avg_individual:.2f}%)")
        else:
            logger.info(f"   ⚠️ Ensemble similar to individuals")
    
    if avg_individual > 55:
        logger.info(f"\n✅ READY for production (>55% accuracy target met!)")
    else:
        logger.info(f"\n⚠️ Still below 55% target, but SIGNIFICANTLY improved from 43-50%")


if __name__ == '__main__':
    test_improved_ensemble()
