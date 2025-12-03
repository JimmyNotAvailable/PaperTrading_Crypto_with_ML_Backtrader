"""
hybrid_train_models.py
======================
Hybrid Training Strategy:
1. Train models trên HISTORICAL data (2017-2023) - 5000 samples
2. Validate trên historical test split
3. Final evaluation trên REAL-TIME data (Nov 2025) để test generalization

Mục tiêu: Đo khả năng model generalize từ historical → real-time
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from config.symbols_config import get_all_symbols, normalize_symbol, get_base_symbol
from app.ml.load_historical_data import load_historical_data, clean_historical_data
from app.ml.feature_engineering import calculate_features
from app.ml.anti_overfitting import apply_anti_overfitting
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models directory
MODELS_DIR = PROJECT_ROOT / "app" / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_realtime_data(symbol: str, limit: int = 500) -> pd.DataFrame:
    """
    Fetch real-time data từ Binance API (current Nov 2025)
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        limit: Number of recent candles to fetch
    
    Returns:
        DataFrame with OHLCV data
    """
    import ccxt
    
    logger.info(f"📡 Fetching {limit} real-time candles for {symbol} from Binance...")
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    # Convert symbol format: 'BTC/USDT' → 'BTCUSDT'
    binance_symbol = symbol.replace('/', '')
    
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        
        logger.info(f"✅ Fetched {len(df)} real-time candles")
        logger.info(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch real-time data: {e}")
        raise


def prepare_historical_datasets(symbol: str, limit: int = 5000):
    """
    Load historical data và split thành train/val/test
    
    Returns:
        Dict with train/val/test DataFrames
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📂 PHASE 1: HISTORICAL DATA PREPARATION")
    logger.info(f"{'='*60}")
    
    # Load historical data
    base = get_base_symbol(symbol)
    df_raw = load_historical_data(base, limit=limit)
    
    if df_raw is None or len(df_raw) == 0:
        raise ValueError(f"No historical data found for {base}")
    
    # Clean data
    df_clean = clean_historical_data(df_raw)
    df_clean['symbol'] = symbol  # Add symbol column
    
    logger.info(f"✅ Historical data ready: {len(df_clean)} samples")
    logger.info(f"   Date range: {df_clean['date'].min()} to {df_clean['date'].max()}")
    
    # Calculate features
    logger.info("\n🔧 Calculating features for historical data...")
    df_features = calculate_features(df_clean, include_target=True)
    
    logger.info(f"✅ Features calculated: {len(df_features)} samples")
    
    # Split: 70% train, 15% val, 15% test (temporal split)
    n = len(df_features)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    train_df = df_features.iloc[:train_end].copy()
    val_df = df_features.iloc[train_end:val_end].copy()
    test_df = df_features.iloc[val_end:].copy()
    
    logger.info(f"\n📊 Historical data split:")
    logger.info(f"   Train: {len(train_df)} samples ({train_df['date'].min()} to {train_df['date'].max()})")
    logger.info(f"   Val:   {len(val_df)} samples ({val_df['date'].min()} to {val_df['date'].max()})")
    logger.info(f"   Test:  {len(test_df)} samples ({test_df['date'].min()} to {test_df['date'].max()})")
    
    return {
        'train': train_df,
        'val': val_df,
        'test': test_df
    }


def prepare_realtime_dataset(symbol: str, limit: int = 500):
    """
    Fetch real-time data và calculate features
    
    Returns:
        DataFrame with features for real-time evaluation
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📡 PHASE 2: REAL-TIME DATA PREPARATION")
    logger.info(f"{'='*60}")
    
    # Fetch real-time data
    df_realtime = fetch_realtime_data(symbol, limit=limit)
    
    # Calculate features
    logger.info("\n🔧 Calculating features for real-time data...")
    df_features = calculate_features(df_realtime, include_target=True)
    
    logger.info(f"✅ Real-time features ready: {len(df_features)} samples")
    logger.info(f"   Date range: {df_features['date'].min()} to {df_features['date'].max()}")
    
    return df_features


def train_models_hybrid(datasets: dict, symbol: str):
    """
    Train models với anti-overfitting pipeline
    
    Returns:
        Dict of trained models
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🎓 PHASE 3: MODEL TRAINING (Historical Data)")
    logger.info(f"{'='*60}")
    
    # Apply anti-overfitting
    feature_cols = [col for col in datasets['train'].columns 
                   if col not in ['date', 'symbol', 'target', 'timestamp']]
    
    logger.info(f"\n📊 Raw split - Train: {len(datasets['train'])}, Val: {len(datasets['val'])}, Test: {len(datasets['test'])}")
    logger.info("\n🛡️ Applying anti-overfitting pipeline...")
    
    datasets = apply_anti_overfitting(
        datasets=datasets,
        feature_cols=feature_cols,
        remove_outliers=True,
        balance_target='target'
    )
    
    logger.info(f"\n📊 After anti-overfitting:")
    logger.info(f"   Train: {len(datasets['train'])} samples")
    logger.info(f"   Val: {len(datasets['val'])} samples")
    logger.info(f"   Test: {len(datasets['test'])} samples")
    logger.info(f"   Features: {feature_cols}")
    logger.info(f"   Outliers removed: {datasets['outlier_stats']}")
    
    # Prepare training data
    X_train = datasets['train'][feature_cols]
    y_train = datasets['train']['target']
    X_val = datasets['val'][feature_cols]
    y_val = datasets['val']['target']
    
    # Train models
    models = {}
    
    # Random Forest
    logger.info("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)
    rf_acc = accuracy_score(y_val, rf.predict(X_val))
    models['random_forest'] = rf
    logger.info(f"   ✅ Random Forest Accuracy (Historical Val): {rf_acc:.4f}")
    logger.info(f"\n{classification_report(y_val, rf.predict(X_val), target_names=['DOWN', 'UP'])}")
    
    # SVM
    logger.info("\n🎯 Training SVM...")
    svm = SVC(kernel='rbf', C=1.0, gamma='scale', random_state=42)
    svm.fit(X_train, y_train)
    svm_acc = accuracy_score(y_val, svm.predict(X_val))
    models['svm'] = svm
    logger.info(f"   ✅ SVM Accuracy (Historical Val): {svm_acc:.4f}")
    logger.info(f"\n{classification_report(y_val, svm.predict(X_val), target_names=['DOWN', 'UP'])}")
    
    # Logistic Regression
    logger.info("\n📈 Training Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_acc = accuracy_score(y_val, lr.predict(X_val))
    models['logistic_regression'] = lr
    logger.info(f"   ✅ Logistic Regression Accuracy (Historical Val): {lr_acc:.4f}")
    logger.info(f"\n{classification_report(y_val, lr.predict(X_val), target_names=['DOWN', 'UP'])}")
    
    logger.info(f"\n{'='*60}")
    logger.info("📊 HISTORICAL VALIDATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Random Forest:         {rf_acc:.4f}")
    logger.info(f"SVM:                   {svm_acc:.4f}")
    logger.info(f"Logistic Regression:   {lr_acc:.4f}")
    logger.info(f"{'='*60}")
    
    # Store metadata
    models['feature_cols'] = feature_cols
    models['scalers'] = datasets['scalers']
    models['symbol'] = symbol
    
    return models


def evaluate_on_realtime(models: dict, realtime_df: pd.DataFrame):
    """
    Evaluate trained models trên real-time data
    
    Returns:
        Dict with evaluation metrics
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 PHASE 4: REAL-TIME EVALUATION (Nov 2025)")
    logger.info(f"{'='*60}")
    
    feature_cols = models['feature_cols']
    symbol = models['symbol']
    
    # Apply same scaling as training (per symbol)
    scaler = models['scalers'].get(symbol)
    if scaler is None:
        logger.warning(f"⚠️ No scaler found for {symbol}, using raw features")
        X_realtime = realtime_df[feature_cols]
    else:
        X_realtime = realtime_df[feature_cols].copy()
        X_realtime[feature_cols] = scaler.transform(X_realtime[feature_cols])
    
    y_realtime = realtime_df['target']
    
    logger.info(f"📊 Real-time test set: {len(realtime_df)} samples")
    logger.info(f"   Date range: {realtime_df['date'].min()} to {realtime_df['date'].max()}")
    
    results = {}
    
    # Random Forest
    logger.info("\n🌲 Random Forest on Real-Time:")
    rf_pred = models['random_forest'].predict(X_realtime)
    rf_acc = accuracy_score(y_realtime, rf_pred)
    results['random_forest'] = rf_acc
    logger.info(f"   ✅ Accuracy: {rf_acc:.4f}")
    logger.info(f"\n{classification_report(y_realtime, rf_pred, target_names=['DOWN', 'UP'])}")
    
    # SVM
    logger.info("\n🎯 SVM on Real-Time:")
    svm_pred = models['svm'].predict(X_realtime)
    svm_acc = accuracy_score(y_realtime, svm_pred)
    results['svm'] = svm_acc
    logger.info(f"   ✅ Accuracy: {svm_acc:.4f}")
    logger.info(f"\n{classification_report(y_realtime, svm_pred, target_names=['DOWN', 'UP'])}")
    
    # Logistic Regression
    logger.info("\n📈 Logistic Regression on Real-Time:")
    lr_pred = models['logistic_regression'].predict(X_realtime)
    lr_acc = accuracy_score(y_realtime, lr_pred)
    results['logistic_regression'] = lr_acc
    logger.info(f"   ✅ Accuracy: {lr_acc:.4f}")
    logger.info(f"\n{classification_report(y_realtime, lr_pred, target_names=['DOWN', 'UP'])}")
    
    logger.info(f"\n{'='*60}")
    logger.info("🚀 REAL-TIME EVALUATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Random Forest:         {rf_acc:.4f}")
    logger.info(f"SVM:                   {svm_acc:.4f}")
    logger.info(f"Logistic Regression:   {lr_acc:.4f}")
    logger.info(f"{'='*60}")
    
    return results


def save_models(models: dict, symbol: str):
    """Save trained models to disk"""
    base = get_base_symbol(symbol)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info(f"\n💾 Saving models...")
    
    for model_name in ['random_forest', 'svm', 'logistic_regression']:
        model = models[model_name]
        
        # Save timestamped version
        timestamped_path = MODELS_DIR / f"{model_name}_{base}_{timestamp}.joblib"
        joblib.dump(model, timestamped_path)
        logger.info(f"💾 Saved {model_name} ({base}) → {timestamped_path}")
        
        # Save latest version
        latest_path = MODELS_DIR / f"{model_name}_{base}_latest.joblib"
        joblib.dump(model, latest_path)
        logger.info(f"💾 Saved {model_name} ({base}) → {latest_path} (latest)")
    
    # Save metadata
    metadata = {
        'symbol': symbol,
        'feature_cols': models['feature_cols'],
        'timestamp': timestamp,
        'scalers': models['scalers']
    }
    
    metadata_path = MODELS_DIR / f"metadata_{base}_{timestamp}.joblib"
    joblib.dump(metadata, metadata_path)
    logger.info(f"💾 Saved metadata → {metadata_path}")


def main(symbol: str = 'BTC/USDT', historical_limit: int = 5000, realtime_limit: int = 500):
    """
    Main hybrid training pipeline
    
    Args:
        symbol: Trading pair
        historical_limit: Number of historical samples
        realtime_limit: Number of real-time samples
    """
    logger.info("🚀 Starting HYBRID Training Pipeline...")
    logger.info(f"📊 Strategy: Train on Historical (2017-2023) → Test on Real-Time (Nov 2025)")
    logger.info(f"🎯 Symbol: {symbol}")
    logger.info(f"📈 Historical samples: {historical_limit}")
    logger.info(f"📡 Real-time samples: {realtime_limit}")
    
    try:
        # Phase 1: Prepare historical data
        historical_datasets = prepare_historical_datasets(symbol, limit=historical_limit)
        
        # Phase 2: Prepare real-time data
        realtime_df = prepare_realtime_dataset(symbol, limit=realtime_limit)
        
        # Phase 3: Train models on historical
        models = train_models_hybrid(historical_datasets, symbol)
        
        # Phase 4: Evaluate on real-time
        realtime_results = evaluate_on_realtime(models, realtime_df)
        
        # Phase 5: Save models
        save_models(models, symbol)
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info("🏁 HYBRID TRAINING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Models trained on historical data (2017-2023)")
        logger.info(f"✅ Validated on real-time data (Nov 2025)")
        logger.info(f"📁 Models saved to: {MODELS_DIR}")
        logger.info(f"\n📝 Next steps:")
        logger.info("   1. Compare historical vs real-time accuracy")
        logger.info("   2. If real-time accuracy is acceptable (>60%), deploy model")
        logger.info("   3. If too low, consider retraining with recent data")
        
    except Exception as e:
        logger.error(f"❌ Hybrid training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hybrid ML Training: Historical → Real-Time')
    parser.add_argument('--symbol', type=str, default='BTC',
                       help='Symbol to train (default: BTC)')
    parser.add_argument('--historical', type=int, default=5000,
                       help='Number of historical samples (default: 5000)')
    parser.add_argument('--realtime', type=int, default=500,
                       help='Number of real-time samples (default: 500)')
    
    args = parser.parse_args()
    
    symbol = normalize_symbol(args.symbol)
    main(symbol=symbol, historical_limit=args.historical, realtime_limit=args.realtime)
