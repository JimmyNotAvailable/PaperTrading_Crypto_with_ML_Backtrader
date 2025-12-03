"""
check_old_models.py
===================
Load và test các models đã train trước đó để so sánh accuracy
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, classification_report

PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from app.ml.load_historical_data import load_historical_data, clean_historical_data
from app.ml.feature_engineering import calculate_features
from app.ml.hybrid_train_models import fetch_realtime_data

def load_and_test_model(model_path: Path, test_df: pd.DataFrame, feature_cols: list, scaler=None):
    """Load model và test accuracy"""
    print(f"\n{'='*60}")
    print(f"Testing: {model_path.name}")
    print(f"{'='*60}")
    
    # Load model
    model = joblib.load(model_path)
    
    # Prepare test data
    X_test = test_df[feature_cols].copy()
    y_test = test_df['target']
    
    # Apply scaling if provided
    if scaler is not None:
        X_test = scaler.transform(X_test)
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Calculate accuracy
    acc = accuracy_score(y_test, y_pred)
    
    print(f"Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print(f"\n{classification_report(y_test, y_pred, target_names=['DOWN', 'UP'], zero_division=0)}")
    
    return acc


def main():
    print("🔍 Checking Old Models Performance...")
    print("="*60)
    
    # Prepare test data (real-time Nov 2025)
    print("\n📡 Fetching real-time test data...")
    realtime_df = fetch_realtime_data('BTC/USDT', limit=500)
    realtime_features = calculate_features(realtime_df, include_target=True)
    
    print(f"✅ Real-time test set ready: {len(realtime_features)} samples")
    print(f"   Date range: {realtime_features['date'].min()} to {realtime_features['date'].max()}")
    print(f"   Class distribution: DOWN={sum(realtime_features['target']==0)}, UP={sum(realtime_features['target']==1)}")
    
    # Feature columns (from training)
    feature_cols = [col for col in realtime_features.columns 
                   if col not in ['date', 'symbol', 'target', 'timestamp']]
    
    print(f"\n📊 Features: {len(feature_cols)} indicators")
    print(f"   {feature_cols[:10]}...")
    
    # Get all BTC models sorted by date
    models_dir = PROJECT_ROOT / "app" / "ml" / "models"
    
    # Test models from different training sessions
    model_sessions = [
        "20251129_103243",  # First session today
        "20251129_105052",  # Second session
        "20251129_105407",  # Third session
        "20251129_111152",  # Fourth session (train_models.py)
        "20251129_111610",  # Fifth session (hybrid_train_models.py)
    ]
    
    results = {}
    
    for session in model_sessions:
        print(f"\n{'#'*60}")
        print(f"SESSION: {session}")
        print(f"{'#'*60}")
        
        # Load metadata to get scaler if exists
        metadata_path = models_dir / f"metadata_BTC_{session}.joblib"
        scaler = None
        
        if metadata_path.exists():
            try:
                metadata = joblib.load(metadata_path)
                if 'scalers' in metadata and 'BTC/USDT' in metadata['scalers']:
                    scaler = metadata['scalers']['BTC/USDT']
                    print("✅ Loaded scaler from metadata")
            except Exception as e:
                print(f"⚠️ Could not load metadata: {e}")
        
        session_results = {}
        
        # Test each model type
        for model_type in ['random_forest', 'svm', 'logistic_regression']:
            model_path = models_dir / f"{model_type}_BTC_{session}.joblib"
            
            if model_path.exists():
                try:
                    acc = load_and_test_model(model_path, realtime_features, feature_cols, scaler)
                    session_results[model_type] = acc
                except Exception as e:
                    print(f"❌ Error testing {model_type}: {e}")
                    session_results[model_type] = 0.0
            else:
                print(f"⚠️ Model not found: {model_path.name}")
        
        results[session] = session_results
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 FINAL COMPARISON - ALL SESSIONS")
    print(f"{'='*60}")
    print(f"\n{'Session':<20} {'RF':<10} {'SVM':<10} {'LogReg':<10} {'Best':<10}")
    print("-"*60)
    
    for session, scores in results.items():
        rf_acc = scores.get('random_forest', 0.0)
        svm_acc = scores.get('svm', 0.0)
        lr_acc = scores.get('logistic_regression', 0.0)
        best = max(rf_acc, svm_acc, lr_acc)
        
        print(f"{session:<20} {rf_acc*100:>6.2f}%   {svm_acc*100:>6.2f}%   {lr_acc*100:>6.2f}%   {best*100:>6.2f}%")
    
    print("\n" + "="*60)
    print("📝 KEY FINDINGS:")
    print("="*60)
    
    # Find best model across all sessions
    best_acc = 0
    best_model = None
    best_session = None
    
    for session, scores in results.items():
        for model_type, acc in scores.items():
            if acc > best_acc:
                best_acc = acc
                best_model = model_type
                best_session = session
    
    print(f"\n🏆 Best Model: {best_model} from {best_session}")
    print(f"   Accuracy on Real-Time (Nov 2025): {best_acc*100:.2f}%")
    print(f"\n⚠️ If old models show >60% accuracy, investigate:")
    print("   1. Different feature engineering (check metadata)")
    print("   2. Different train/test split")
    print("   3. Different preprocessing (outlier removal, scaling)")
    print("   4. Train data from different time period")


if __name__ == "__main__":
    main()
