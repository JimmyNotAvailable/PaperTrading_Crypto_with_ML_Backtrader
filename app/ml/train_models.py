"""
ML Model Training Script for Crypto Trading
============================================
Trains 3 models following ToturialUpgrade.md recommendations:
1. Random Forest - Primary model for trend detection
2. SVM - Support Vector Machine for classification
3. Logistic Regression - Baseline probability model

Models are saved to app/ml/models/ directory for use by ML Consumer.
"""

import os
import sys
import ccxt
import pandas as pd
import joblib
import logging
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.feature_engineering import calculate_features, get_feature_columns
from ml.anti_overfitting import AntiOverfittingPipeline
from ml.load_historical_data import load_historical_data, clean_historical_data
from config.symbols_config import (
    SUPPORTED_SYMBOLS, normalize_symbol, get_base_symbol, 
    get_binance_format, get_all_symbols
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create models directory
MODELS_DIR = Path(__file__).parent / 'models'
MODELS_DIR.mkdir(exist_ok=True)


def fetch_historical_data(symbol: str = 'BTC/USDT', limit: int = 5000) -> pd.DataFrame:
    """
    Fetch historical OHLCV data - PRIORITY: CSV files > Binance API
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        limit: Number of candles to use (default 5000 for better training)
        
    Returns:
        DataFrame with OHLCV data
    """
    base_symbol = get_base_symbol(symbol)
    
    try:
        # TRY HISTORICAL CSV FIRST (2017-2023 data, much more samples)
        logger.info(f"📂 Loading historical data for {base_symbol}...")
        df = load_historical_data(base_symbol, limit=limit)
        df = clean_historical_data(df)
        logger.info(f"✅ Loaded {len(df):,} historical samples ({df['date'].min()} to {df['date'].max()})")
        return df
        
    except (FileNotFoundError, Exception) as e:
        # FALLBACK: Binance API (only ~1000 samples)
        logger.warning(f"⚠️ Historical data not available for {base_symbol}: {e}")
        logger.info(f"📥 Falling back to Binance API (limited to ~1000 samples)...")
        
        try:
            exchange = ccxt.binance({'enableRateLimit': True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=min(limit, 1000))
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            logger.info(f"✅ Fetched {len(df)} candles from Binance")
            return df
            
        except Exception as api_error:
            logger.error(f"❌ Binance API error: {api_error}")
            raise


def train_models(df: pd.DataFrame, symbol: str = 'BTC/USDT') -> dict:
    """
    Train all 3 ML models with anti-overfitting pipeline.
    
    Args:
        df: DataFrame with features and target
        symbol: Trading pair for per-symbol preprocessing
        
    Returns:
        Dictionary containing trained models
    """
    # Add symbol column if not present
    if 'symbol' not in df.columns:
        df['symbol'] = symbol
    
    # Add date column if not present (use timestamp)
    if 'date' not in df.columns:
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Prepare features and target
    feature_cols = get_feature_columns()
    
    # Time-based split (70% train, 15% val, 15% test)
    n = len(df)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    logger.info(f"📊 Raw split - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Apply anti-overfitting pipeline
    logger.info("\n🛡️ Applying anti-overfitting pipeline...")
    pipeline = AntiOverfittingPipeline(
        outlier_method='iqr',
        scale_method='robust'  # Better for outliers
    )
    
    result = pipeline.run_pipeline(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        feature_cols=feature_cols,
        remove_outliers=True,
        balance_target='target'  # Balance UP/DOWN classes
    )
    
    # Extract processed data
    train_clean = result['train']
    val_clean = result['val']
    test_clean = result['test']
    
    # Prepare final datasets
    X_train = train_clean[feature_cols]
    y_train = train_clean['target']
    
    X_val = val_clean[feature_cols]
    y_val = val_clean['target']
    
    X_test = test_clean[feature_cols]
    y_test = test_clean['target']
    
    logger.info(f"\n📊 After anti-overfitting:")
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Val: {len(X_val)} samples")
    logger.info(f"   Test: {len(X_test)} samples")
    logger.info(f"   Features: {feature_cols}")
    logger.info(f"   Outliers removed: {result['outlier_stats']}")
    
    models = {}
    
    # 1. Random Forest - Primary model
    logger.info("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1  # Use all CPU cores
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_pred)
    
    logger.info(f"   ✅ Random Forest Accuracy: {rf_acc:.4f}")
    logger.info(f"\n{classification_report(y_test, rf_pred, target_names=['DOWN', 'UP'])}")
    
    models['random_forest'] = rf
    
    # 2. SVM - Classification with probability
    logger.info("\n🎯 Training SVM...")
    svm = SVC(
        probability=True,  # Enable probability estimates
        kernel='rbf',      # Radial basis function kernel
        random_state=42
    )
    svm.fit(X_train, y_train)
    svm_pred = svm.predict(X_test)
    svm_acc = accuracy_score(y_test, svm_pred)
    
    logger.info(f"   ✅ SVM Accuracy: {svm_acc:.4f}")
    logger.info(f"\n{classification_report(y_test, svm_pred, target_names=['DOWN', 'UP'])}")
    
    models['svm'] = svm
    
    # 3. Logistic Regression - Baseline
    logger.info("\n📈 Training Logistic Regression...")
    lr = LogisticRegression(random_state=42, max_iter=1000)
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_acc = accuracy_score(y_test, lr_pred)
    
    logger.info(f"   ✅ Logistic Regression Accuracy: {lr_acc:.4f}")
    logger.info(f"\n{classification_report(y_test, lr_pred, target_names=['DOWN', 'UP'])}")
    
    models['logistic_regression'] = lr
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 TRAINING SUMMARY")
    logger.info("="*60)
    logger.info(f"Random Forest:         {rf_acc:.4f}")
    logger.info(f"SVM:                   {svm_acc:.4f}")
    logger.info(f"Logistic Regression:   {lr_acc:.4f}")
    logger.info("="*60)
    
    return models


def save_models(models: dict, symbol: str = 'BTC/USDT') -> None:
    """
    Save trained models to disk.
    
    Args:
        models: Dictionary of trained models
        symbol: Trading pair for model identification
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_symbol = get_base_symbol(symbol)
    
    for model_name, model in models.items():
        # Save with timestamp and symbol
        filename = f"{model_name}_{base_symbol}_{timestamp}.joblib"
        filepath = MODELS_DIR / filename
        
        joblib.dump(model, filepath)
        logger.info(f"💾 Saved {model_name} ({base_symbol}) → {filepath}")
        
        # Also save as "latest" version for this symbol
        latest_filename = f"{model_name}_{base_symbol}_latest.joblib"
        latest_filepath = MODELS_DIR / latest_filename
        joblib.dump(model, latest_filepath)
        logger.info(f"💾 Saved {model_name} ({base_symbol}) → {latest_filepath} (latest)")


def main(train_all_symbols: bool = False, specific_symbol: str = None, use_historical: bool = True):
    """Main training pipeline.
    
    Args:
        train_all_symbols: If True, train models for all supported symbols
        specific_symbol: Train for a specific symbol only (e.g., 'BTC', 'ETH')
        use_historical: If True, use historical CSV data (recommended for better accuracy)
    """
    logger.info("🚀 Starting ML Model Training Pipeline...")
    logger.info(f"📁 Models will be saved to: {MODELS_DIR.absolute()}")
    logger.info(f"📊 Data source: {'Historical CSV (2017-2023)' if use_historical else 'Binance API'}")
    
    # Determine which symbols to train
    if specific_symbol:
        symbols_to_train = [normalize_symbol(specific_symbol)]
        logger.info(f"🎯 Training for specific symbol: {symbols_to_train[0]}")
    elif train_all_symbols:
        symbols_to_train = get_all_symbols()
        logger.info(f"🌐 Training for ALL symbols: {', '.join([get_base_symbol(s) for s in symbols_to_train])}")
    else:
        symbols_to_train = ['BTC/USDT']  # Default
        logger.info(f"🎯 Training for default symbol: BTC/USDT")
    
    logger.info(f"📊 Total symbols to train: {len(symbols_to_train)}")
    
    # Determine data limit based on source
    data_limit = 5000 if use_historical else 1000
    logger.info(f"📈 Using {data_limit} samples per symbol")
    logger.info("="*60 + "\n")
    
    trained_count = 0
    failed_count = 0
    
    for symbol in symbols_to_train:
        try:
            base = get_base_symbol(symbol)
            logger.info(f"\n{'='*60}")
            logger.info(f"🪙 Training models for {base} ({symbol})")
            logger.info(f"{'='*60}")
            
            # Step 1: Fetch data (historical CSV or Binance API)
            df_raw = fetch_historical_data(symbol=symbol, limit=data_limit)
            
            # Step 2: Feature engineering
            logger.info("\n🔧 Calculating features...")
            df_features = calculate_features(df_raw, include_target=True)
            logger.info(f"✅ Features calculated: {len(df_features)} samples ready for training")
            
            # Step 3: Train models (with anti-overfitting)
            models = train_models(df_features, symbol=symbol)
            
            # Step 4: Save models
            logger.info("\n💾 Saving models...")
            save_models(models, symbol=symbol)
            
            trained_count += 1
            logger.info(f"\n✅ {base} training completed successfully!")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"\n❌ {get_base_symbol(symbol)} training failed: {e}")
            import traceback
            traceback.print_exc()
            continue  # Continue with next symbol
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("🏁 Training Pipeline Summary")
    logger.info("="*60)
    logger.info(f"✅ Successfully trained: {trained_count} symbols")
    logger.info(f"❌ Failed: {failed_count} symbols")
    logger.info(f"📁 Models saved to: {MODELS_DIR.absolute()}")
    logger.info(f"\n📝 Next steps:")
    logger.info("   1. Verify models exist in app/ml/models/")
    logger.info("   2. Run ML Consumer: python app/consumers/ml_predictor.py")
    logger.info("   3. Send test data via Producer to see predictions")
    
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Train ML models for crypto trading')
    parser.add_argument(
        '--all', 
        action='store_true', 
        help='Train models for all supported symbols (BTC, ETH, XRP, SOL, BNB)'
    )
    parser.add_argument(
        '--symbol', 
        type=str, 
        help='Train for specific symbol only (e.g., BTC, ETH, XRP, SOL, BNB)'
    )
    
    args = parser.parse_args()
    
    main(train_all_symbols=args.all, specific_symbol=args.symbol)
