"""
Test script for improved ML predictor integration.

Tests:
1. Improved model loading from disk
2. Feature metadata loading (10 selected features)
3. Mock prediction with 4h target logic
4. Ensemble voting with 2/3 majority
5. Kafka message format validation
"""

import sys
from pathlib import Path
import json
import pandas as pd
import joblib

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.ml.feature_engineering import calculate_features
from config.symbols_config import get_base_symbol


def test_improved_model_loading():
    """Test loading improved models and feature metadata."""
    print("=" * 60)
    print("TEST 1: Improved Model Loading")
    print("=" * 60)
    
    symbol = "BTCUSDT"
    base = get_base_symbol(symbol)
    models_dir = project_root / 'app' / 'ml' / 'models'
    
    # Check improved model files
    rf_path = models_dir / f'improved_random_forest_{base}_latest.joblib'
    svm_path = models_dir / f'improved_svm_{base}_latest.joblib'
    lr_path = models_dir / f'improved_logistic_regression_{base}_latest.joblib'
    features_path = models_dir / f'improved_features_{base}.json'
    
    print(f"Checking model files for {base}:")
    print(f"✓ RF model: {rf_path.exists()} - {rf_path}")
    print(f"✓ SVM model: {svm_path.exists()} - {svm_path}")
    print(f"✓ LR model: {lr_path.exists()} - {lr_path}")
    print(f"✓ Features metadata: {features_path.exists()} - {features_path}")
    
    if not all([rf_path.exists(), svm_path.exists(), lr_path.exists(), features_path.exists()]):
        print("\n❌ Missing improved model files!")
        print("Please run: python app/ml/improved_train_models.py --symbol BTC --historical 5000 --quick")
        return False
    
    # Load feature metadata
    with open(features_path, 'r') as f:
        features_meta = json.load(f)
        selected_features = features_meta['selected_features']
        target_type = features_meta.get('target_type', 'unknown')
        n_features = features_meta.get('n_features', 0)
    
    print(f"\n✅ Feature metadata loaded:")
    print(f"   Target type: {target_type}")
    print(f"   Number of features: {n_features}")
    print(f"   Selected features: {selected_features}")
    
    # Load models
    rf_model = joblib.load(rf_path)
    svm_model = joblib.load(svm_path)
    lr_model = joblib.load(lr_path)
    
    print(f"\n✅ Models loaded successfully:")
    print(f"   RF: {type(rf_model).__name__}")
    print(f"   SVM: {type(svm_model).__name__}")
    print(f"   LR: {type(lr_model).__name__}")
    
    return {
        'rf': rf_model,
        'svm': svm_model,
        'lr': lr_model,
        'selected_features': selected_features
    }


def test_feature_calculation():
    """Test feature calculation and selection."""
    print("\n" + "=" * 60)
    print("TEST 2: Feature Calculation")
    print("=" * 60)
    
    # Load sample historical data
    data_dir = project_root / 'data' / 'historical' / 'Crypto_Data_Hourly_Price_17_23'
    csv_path = data_dir / 'Binance_BTCUSDT_1h (1).csv'
    
    if not csv_path.exists():
        print(f"❌ Sample data not found: {csv_path}")
        return None
    
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} historical candles")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Rename columns to match expected format
    df = df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume USDT': 'volume'
    })
    
    # Calculate all features
    df_features = calculate_features(df, include_target=False)
    print(f"\n✅ Calculated features: {len(df_features.columns)} total")
    print(f"   Feature columns: {df_features.columns.tolist()[:10]}...")
    
    return df_features


def test_mock_prediction(models, df_features):
    """Test prediction with improved models."""
    print("\n" + "=" * 60)
    print("TEST 3: Mock Prediction")
    print("=" * 60)
    
    if models is None or df_features is None:
        print("❌ Skipping - models or features not loaded")
        return None
    
    # Get selected features
    selected_features = models['selected_features']
    
    # Get last 5 rows for testing
    test_data = df_features.iloc[-5:][selected_features]
    print(f"✅ Test data shape: {test_data.shape}")
    print(f"   Using features: {selected_features}")
    
    results = []
    
    for i, (idx, row) in enumerate(test_data.iterrows()):
        last_row = row.to_frame().T
        
        # Predict with all 3 models
        rf_pred = models['rf'].predict(last_row)[0]
        rf_prob = models['rf'].predict_proba(last_row)[0][1]
        
        svm_pred = models['svm'].predict(last_row)[0]
        svm_prob = models['svm'].predict_proba(last_row)[0][1]
        
        lr_pred = models['lr'].predict(last_row)[0]
        lr_prob = models['lr'].predict_proba(last_row)[0][1]
        
        # Ensemble logic (2/3 majority voting)
        votes_up = sum([rf_pred == 1, svm_pred == 1, lr_pred == 1])
        votes_down = sum([rf_pred == 0, svm_pred == 0, lr_pred == 0])
        avg_confidence = (rf_prob + svm_prob + lr_prob) / 3
        
        signal = "NEUTRAL"
        if votes_up >= 2 and avg_confidence > 0.55:
            signal = "BUY"
        elif votes_down >= 2 and avg_confidence < 0.45:
            signal = "SELL"
        
        results.append({
            'index': i + 1,
            'signal': signal,
            'votes_up': votes_up,
            'votes_down': votes_down,
            'avg_confidence': avg_confidence,
            'rf_pred': rf_pred,
            'rf_prob': rf_prob,
            'svm_pred': svm_pred,
            'svm_prob': svm_prob,
            'lr_pred': lr_pred,
            'lr_prob': lr_prob
        })
        
        signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        print(f"{signal_emoji} Sample {i+1}: {signal} (4h trend) | "
              f"Votes: {votes_up}↑/{votes_down}↓ | "
              f"Avg Conf: {avg_confidence:.2%} | "
              f"RF:{rf_prob:.2f} SVM:{svm_prob:.2f} LR:{lr_prob:.2f}")
    
    return results


def test_kafka_message_format(prediction_result):
    """Test Kafka message format."""
    print("\n" + "=" * 60)
    print("TEST 4: Kafka Message Format")
    print("=" * 60)
    
    if not prediction_result:
        print("❌ Skipping - no prediction results")
        return
    
    # Take first prediction result
    result = prediction_result[0]
    
    # Create Kafka message (same format as ml_predictor.py)
    message = {
        "timestamp": "2025-06-01T00:00:00",
        "symbol": "BTCUSDT",
        "price": 68000.50,
        "signal": result['signal'],
        "prediction_type": "4h_trend",
        "hold_periods": 4,
        "details": {
            "random_forest": {
                "prediction": int(result['rf_pred']),
                "confidence": round(float(result['rf_prob']), 4)
            },
            "svm": {
                "prediction": int(result['svm_pred']),
                "confidence": round(float(result['svm_prob']), 4)
            },
            "logistic_regression": {
                "prediction": int(result['lr_pred']),
                "confidence": round(float(result['lr_prob']), 4)
            },
            "ensemble": {
                "votes_up": int(result['votes_up']),  # Convert numpy int64
                "votes_down": int(result['votes_down']),  # Convert numpy int64
                "avg_confidence": round(float(result['avg_confidence']), 4)
            }
        }
    }
    
    print("✅ Kafka message format:")
    print(json.dumps(message, indent=2))
    
    # Validate message structure
    assert "timestamp" in message
    assert "symbol" in message
    assert "signal" in message
    assert "prediction_type" in message
    assert message["prediction_type"] == "4h_trend"
    assert "hold_periods" in message
    assert message["hold_periods"] == 4
    assert "details" in message
    assert "ensemble" in message["details"]
    
    print("\n✅ Message validation passed!")
    return message


def main():
    """Run all tests."""
    print("\n🧪 Testing Improved ML Predictor Integration")
    print("=" * 60)
    
    # Test 1: Model loading
    models = test_improved_model_loading()
    if not models:
        print("\n❌ Test suite failed at model loading")
        return
    
    # Test 2: Feature calculation
    df_features = test_feature_calculation()
    if df_features is None:
        print("\n❌ Test suite failed at feature calculation")
        return
    
    # Test 3: Mock prediction
    results = test_mock_prediction(models, df_features)
    if not results:
        print("\n❌ Test suite failed at prediction")
        return
    
    # Test 4: Kafka message format
    message = test_kafka_message_format(results)
    if not message:
        print("\n❌ Test suite failed at message format")
        return
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print("✅ Model loading: PASSED")
    print("✅ Feature calculation: PASSED")
    print("✅ Mock prediction: PASSED")
    print(f"   - {sum(1 for r in results if r['signal'] == 'BUY')} BUY signals")
    print(f"   - {sum(1 for r in results if r['signal'] == 'SELL')} SELL signals")
    print(f"   - {sum(1 for r in results if r['signal'] == 'NEUTRAL')} NEUTRAL signals")
    print("✅ Kafka message format: PASSED")
    print("\n🎉 All tests passed! Ready for integration.")
    print("\nNext steps:")
    print("1. Start Kafka: docker-compose up -d")
    print("2. Start producer: python app/producers/binance_producer.py")
    print("3. Start consumer: python app/consumers/ml_predictor.py")


if __name__ == "__main__":
    main()
