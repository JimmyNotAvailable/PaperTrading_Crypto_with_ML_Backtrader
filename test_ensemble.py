"""
test_ensemble.py
================
Test ensemble predictor với real-time data để validate:
1. Voting logic (≥2/3 models agree)
2. Confidence threshold (≥60%)
3. Signal generation (BUY/SELL/NEUTRAL)

Kiểm tra xem ensemble có cải thiện accuracy so với individual models không
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from app.ml.ensemble_predictor import EnsemblePredictor
from app.ml.load_historical_data import load_historical_data
from app.ml.feature_engineering import calculate_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ensemble_predictions():
    """Test ensemble với 100 samples gần nhất"""
    logger.info("=" * 60)
    logger.info("🧪 TESTING ENSEMBLE PREDICTOR")
    logger.info("=" * 60)
    
    # 1. Load data
    logger.info("\n📂 Loading test data...")
    df = load_historical_data('BTC', limit=200)
    logger.info(f"✅ Loaded {len(df)} samples")
    
    # 2. Calculate features
    logger.info("\n🔧 Calculating features...")
    df = calculate_features(df)
    df = df.dropna()
    logger.info(f"✅ {len(df)} samples ready")
    
    # 3. Initialize ensemble
    logger.info("\n🤖 Initializing ensemble...")
    ensemble = EnsemblePredictor(symbol='BTC/USDT', confidence_threshold=0.60)
    
    # 4. Test with last 50 samples
    test_samples = df.tail(50).copy()
    logger.info(f"\n📊 Testing with {len(test_samples)} samples")
    
    # Prepare features (exclude only metadata, KEEP OHLCV as models were trained with them!)
    feature_cols = [col for col in df.columns if col not in 
                   ['timestamp', 'close_time', 'symbol', 'target', 'price_change', 'date']]
    
    X_test = test_samples[feature_cols]
    
    # Track results
    signals = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
    high_confidence_trades = 0
    low_confidence_neutrals = 0
    
    predictions = []
    
    logger.info("\n" + "=" * 80)
    logger.info("Sample | Signal   | Confidence | RF   | SVM  | LR   | Should Trade")
    logger.info("-" * 80)
    
    for idx, (i, row) in enumerate(X_test.iterrows()):
        # Convert row to dict (same format as Kafka consumer will send)
        market_data = row.to_dict()
        
        # Get ensemble prediction
        result = ensemble.ensemble_predict(market_data)
        
        signals[result['signal']] += 1
        
        if result['should_trade']:
            high_confidence_trades += 1
        else:
            low_confidence_neutrals += 1
        
        # Extract individual votes from individual_preds
        rf_pred = result.get('individual_predictions', {}).get('random_forest', {}).get('pred', None)
        svm_pred = result.get('individual_predictions', {}).get('svm', {}).get('pred', None)
        lr_pred = result.get('individual_predictions', {}).get('logistic_regression', {}).get('pred', None)
        
        rf_vote = 'UP' if rf_pred == 1 else 'DOWN' if rf_pred == 0 else '?'
        svm_vote = 'UP' if svm_pred == 1 else 'DOWN' if svm_pred == 0 else '?'
        lr_vote = 'UP' if lr_pred == 1 else 'DOWN' if lr_pred == 0 else '?'
        
        # Display every 5th sample
        if idx % 5 == 0 or idx < 5:
            logger.info(
                f"{idx:6d} | {result['signal']:8s} | {result['confidence']:10.2%} | "
                f"{rf_vote:4s} | {svm_vote:4s} | {lr_vote:4s} | {result['should_trade']}"
            )
        
        predictions.append(result)
    
    # 5. Summary statistics
    logger.info("=" * 80)
    logger.info("\n📊 ENSEMBLE PREDICTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Predictions: {len(predictions)}")
    logger.info(f"\n🎯 Signal Distribution:")
    logger.info(f"   BUY:     {signals['BUY']:3d} ({signals['BUY']/len(predictions)*100:5.1f}%)")
    logger.info(f"   SELL:    {signals['SELL']:3d} ({signals['SELL']/len(predictions)*100:5.1f}%)")
    logger.info(f"   NEUTRAL: {signals['NEUTRAL']:3d} ({signals['NEUTRAL']/len(predictions)*100:5.1f}%)")
    
    logger.info(f"\n💡 Trade Decision:")
    logger.info(f"   High Confidence (Should Trade): {high_confidence_trades} "
                f"({high_confidence_trades/len(predictions)*100:.1f}%)")
    logger.info(f"   Low Confidence (Skip):          {low_confidence_neutrals} "
                f"({low_confidence_neutrals/len(predictions)*100:.1f}%)")
    
    # Average confidence by signal type
    avg_conf = {}
    for signal_type in ['BUY', 'SELL', 'NEUTRAL']:
        confs = [p['confidence'] for p in predictions if p['signal'] == signal_type]
        if confs:
            avg_conf[signal_type] = np.mean(confs)
        else:
            avg_conf[signal_type] = 0.0
    
    logger.info(f"\n📈 Average Confidence:")
    logger.info(f"   BUY:     {avg_conf['BUY']:.2%}")
    logger.info(f"   SELL:    {avg_conf['SELL']:.2%}")
    logger.info(f"   NEUTRAL: {avg_conf['NEUTRAL']:.2%}")
    
    # Model agreement analysis
    logger.info(f"\n🤝 Model Agreement:")
    
    def get_predictions(p):
        """Extract 3 predictions (UP/DOWN) from individual_preds"""
        preds = []
        for model_name in ['random_forest', 'svm', 'logistic_regression']:
            pred_val = p.get('individual_predictions', {}).get(model_name, {}).get('pred', None)
            if pred_val is not None:
                preds.append('UP' if pred_val == 1 else 'DOWN')
        return preds
    
    unanimous = sum(1 for p in predictions if len(set(get_predictions(p))) == 1)
    two_agree = sum(1 for p in predictions if len(set(get_predictions(p))) == 2)
    all_disagree = sum(1 for p in predictions if len(set(get_predictions(p))) == 3)
    
    logger.info(f"   Unanimous (3/3):  {unanimous} ({unanimous/len(predictions)*100:.1f}%)")
    logger.info(f"   Majority (2/3):   {two_agree} ({two_agree/len(predictions)*100:.1f}%)")
    logger.info(f"   No Agreement:     {all_disagree} ({all_disagree/len(predictions)*100:.1f}%)")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ ENSEMBLE TEST COMPLETE")
    logger.info("=" * 60)
    
    return predictions


def test_individual_vs_ensemble():
    """So sánh accuracy individual models vs ensemble"""
    logger.info("\n" + "=" * 60)
    logger.info("🆚 INDIVIDUAL vs ENSEMBLE COMPARISON")
    logger.info("=" * 60)
    
    # Load test data with labels
    df = load_historical_data('BTC', limit=1000)
    df = calculate_features(df)
    df = df.dropna()
    
    # Take test set (last 200 samples)
    test_df = df.tail(200).copy()
    
    # Calculate actual labels (price goes up next candle)
    test_df['actual_label'] = (test_df['close'].shift(-1) > test_df['close']).astype(int)
    test_df = test_df[:-1]  # Remove last row (no future price)
    
    # Prepare features (exclude only metadata, KEEP OHLCV as models were trained with them!)
    feature_cols = [col for col in test_df.columns if col not in 
                   ['timestamp', 'close_time', 'symbol', 'target', 'price_change', 'actual_label', 'date']]
    
    X_test = test_df[feature_cols]
    y_true = test_df['actual_label'].values
    
    # Initialize ensemble
    ensemble = EnsemblePredictor(symbol='BTC/USDT', confidence_threshold=0.60)
    
    # Get individual predictions from ensemble
    individual_correct = {'random_forest': 0, 'svm': 0, 'logistic_regression': 0}
    ensemble_correct = 0
    ensemble_trades = 0
    
    for i in range(len(X_test)):
        # Convert row to dict
        market_data = X_test.iloc[i].to_dict()
        result = ensemble.ensemble_predict(market_data)
        
        # Check individual models
        for model_name in ['random_forest', 'svm', 'logistic_regression']:
            pred_val = result.get('individual_predictions', {}).get(model_name, {}).get('pred', None)
            if pred_val is not None and pred_val == y_true[i]:
                individual_correct[model_name] += 1
        
        # Check ensemble (only count trades, not NEUTRAL)
        if result['should_trade']:
            ensemble_trades += 1
            pred = 1 if result['signal'] == 'BUY' else 0
            if pred == y_true[i]:
                ensemble_correct += 1
    
    # Calculate accuracies
    logger.info(f"\n📊 Accuracy Comparison (n={len(X_test)}):")
    logger.info(f"   Random Forest:        {individual_correct['random_forest']/len(X_test)*100:.2f}%")
    logger.info(f"   SVM:                  {individual_correct['svm']/len(X_test)*100:.2f}%")
    logger.info(f"   Logistic Regression:  {individual_correct['logistic_regression']/len(X_test)*100:.2f}%")
    
    if ensemble_trades > 0:
        ensemble_acc = ensemble_correct / ensemble_trades * 100
        logger.info(f"\n   Ensemble (trades only): {ensemble_acc:.2f}% ({ensemble_trades}/{len(X_test)} trades)")
    else:
        logger.info(f"\n   Ensemble: No trades (all NEUTRAL)")
    
    logger.info(f"\n💡 Insight:")
    logger.info(f"   Ensemble trades: {ensemble_trades}/{len(X_test)} ({ensemble_trades/len(X_test)*100:.1f}%)")
    logger.info(f"   Skipped (low confidence): {len(X_test) - ensemble_trades}")
    
    logger.info("\n" + "=" * 60)


if __name__ == '__main__':
    logger.info("🚀 Starting Ensemble Predictor Tests...\n")
    
    try:
        # Test 1: Prediction generation
        predictions = test_ensemble_predictions()
        
        # Test 2: Accuracy comparison
        test_individual_vs_ensemble()
        
        logger.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
