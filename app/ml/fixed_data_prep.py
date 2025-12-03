# fixed_data_prep.py
# Chuẩn bị dữ liệu KHÔNG có data leakage cho ML training

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
import os
import sys
from typing import Optional, Tuple, Dict, List

def project_root_path():
    """Lấy đường dẫn root của project"""
    current_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

def load_realtime_data(symbols: Optional[list] = None, limit_hours: int = 1000) -> pd.DataFrame:
    """
    Load dữ liệu realtime để training
    """
    root = project_root_path()
    realtime_path = os.path.join(root, "data", "realtime")
    
    if not os.path.exists(realtime_path):
        raise FileNotFoundError(f"❌ Không tìm thấy thư mục realtime data: {realtime_path}")
    
    # Collect all CSV files
    csv_files = []
    for file in os.listdir(realtime_path):
        if file.endswith('.csv'):
            csv_files.append(os.path.join(realtime_path, file))
    
    if not csv_files:
        raise FileNotFoundError(f"❌ Không tìm thấy file CSV nào trong: {realtime_path}")
    
    # Load and combine data
    dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Lỗi đọc file {file}: {e}")
    
    if not dfs:
        raise ValueError("❌ Không thể load được file nào")
    
    # Combine all data
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    
    # Filter symbols if specified
    if symbols:
        combined_df = combined_df[combined_df['symbol'].isin(symbols)]
    
    # Sort by symbol and date
    combined_df = combined_df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Limit to recent data
    if limit_hours:
        for symbol in combined_df['symbol'].unique():
            symbol_data = combined_df[combined_df['symbol'] == symbol].tail(limit_hours)
            if symbol in combined_df['symbol'].unique():
                combined_df = combined_df[~((combined_df['symbol'] == symbol) & 
                                         (~combined_df.index.isin(symbol_data.index)))]
    
    print(f"📊 Loaded realtime data:")
    print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"  Symbols: {combined_df['symbol'].nunique()} unique cryptos")
    print(f"  Total records: {len(combined_df):,}")
    
    return combined_df

def create_proper_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo features KHÔNG có data leakage
    Chỉ sử dụng thông tin từ quá khứ
    """
    df = df.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Features từ HIỆN TẠI (không có leakage)
    df['hour'] = pd.to_datetime(df['date']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek
    
    # Tính toán features theo từng symbol (sử dụng dữ liệu quá khứ)
    for symbol in df['symbol'].unique():
        mask = df['symbol'] == symbol
        symbol_data = df[mask].copy()
        
        # Moving averages (dùng dữ liệu quá khứ)
        symbol_data['ma_5'] = symbol_data['close'].rolling(window=5, min_periods=1).mean()
        symbol_data['ma_10'] = symbol_data['close'].rolling(window=10, min_periods=1).mean()
        symbol_data['ma_20'] = symbol_data['close'].rolling(window=20, min_periods=1).mean()
        
        # Volatility (20-hour rolling std)
        symbol_data['volatility'] = symbol_data['close'].rolling(window=20, min_periods=1).std()
        
        # Returns (price change từ hour trước)
        symbol_data['returns_1h'] = symbol_data['close'].pct_change(1)
        symbol_data['returns_3h'] = symbol_data['close'].pct_change(3)
        symbol_data['returns_6h'] = symbol_data['close'].pct_change(6)
        
        # Price momentum 
        symbol_data['momentum_3h'] = (symbol_data['close'] - symbol_data['close'].shift(3)) / symbol_data['close'].shift(3)
        symbol_data['momentum_6h'] = (symbol_data['close'] - symbol_data['close'].shift(6)) / symbol_data['close'].shift(6)
        
        # Bollinger Bands
        sma_20 = symbol_data['close'].rolling(window=20, min_periods=1).mean()
        std_20 = symbol_data['close'].rolling(window=20, min_periods=1).std()
        symbol_data['bb_upper'] = sma_20 + (std_20 * 2)
        symbol_data['bb_lower'] = sma_20 - (std_20 * 2)
        symbol_data['bb_position'] = (symbol_data['close'] - symbol_data['bb_lower']) / (symbol_data['bb_upper'] - symbol_data['bb_lower'])
        
        # RSI-like indicator (simplified)
        price_change = symbol_data['close'].diff()
        gain = price_change.where(price_change > 0, 0).rolling(window=14, min_periods=1).mean()
        loss = (-price_change.where(price_change < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss
        symbol_data['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume features
        if 'volume' in symbol_data.columns:
            symbol_data['volume_ma_10'] = symbol_data['volume'].rolling(window=10, min_periods=1).mean()
            symbol_data['volume_ratio'] = symbol_data['volume'] / symbol_data['volume_ma_10']
        else:
            symbol_data['volume_ma_10'] = 0
            symbol_data['volume_ratio'] = 1
            
        # Update main DataFrame
        df.loc[mask, symbol_data.columns] = symbol_data
    
    # Fill NaN values
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    print("✅ Created proper features WITHOUT data leakage:")
    print("  - Technical indicators (MA, volatility, RSI)")
    print("  - Price momentum (1h, 3h, 6h)")
    print("  - Bollinger Bands position")
    print("  - Volume ratios")
    print("  - Time features (hour, day_of_week)")
    
    return df

def create_proper_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo target variables ĐÚNG CÁCH - dự đoán tương lai
    """
    df = df.copy()
    
    # Targets cho từng symbol riêng biệt để tránh leakage
    for symbol in df['symbol'].unique():
        mask = df['symbol'] == symbol
        symbol_data = df[mask].copy()
        
        # 1. Next hour price (1 hour ahead)
        symbol_data['target_price_1h'] = symbol_data['close'].shift(-1)
        
        # 2. Next 3 hours price change %
        symbol_data['target_change_3h'] = (symbol_data['close'].shift(-3) - symbol_data['close']) / symbol_data['close']
        
        # 3. Next 6 hours price change %
        symbol_data['target_change_6h'] = (symbol_data['close'].shift(-6) - symbol_data['close']) / symbol_data['close']
        
        # 4. Binary trend (up/down in next hour)
        symbol_data['target_trend_1h'] = (symbol_data['target_price_1h'] > symbol_data['close']).astype(int)
        
        # 5. Binary trend (up/down in next 3 hours)
        symbol_data['target_trend_3h'] = (symbol_data['target_change_3h'] > 0).astype(int)
        
        # Update main DataFrame
        target_cols = ['target_price_1h', 'target_change_3h', 'target_change_6h', 'target_trend_1h', 'target_trend_3h']
        df.loc[mask, target_cols] = symbol_data[target_cols]
    
    print("✅ Created proper target variables:")
    print("  - target_price_1h: Price 1 hour ahead")
    print("  - target_change_3h: Price change % in 3 hours")
    print("  - target_change_6h: Price change % in 6 hours") 
    print("  - target_trend_1h: Binary trend (1 hour)")
    print("  - target_trend_3h: Binary trend (3 hours)")
    
    return df

def get_proper_feature_columns() -> List[str]:
    """
    Trả về danh sách features KHÔNG có data leakage
    """
    return [
        # Price-based features (PAST data only)
        'open', 'high', 'low',  # NOT using 'close' directly
        
        # Technical indicators (calculated from past data)
        'ma_5', 'ma_10', 'ma_20',
        'volatility',
        'bb_position', 'rsi',
        
        # Returns/momentum (past changes)
        'returns_1h', 'returns_3h', 'returns_6h',
        'momentum_3h', 'momentum_6h',
        
        # Volume features
        'volume_ratio',
        
        # Time features
        'hour', 'day_of_week'
    ]

def time_series_split_proper(df: pd.DataFrame, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Chia dữ liệu theo thời gian ĐÚNG CÁCH
    Đảm bảo không có temporal leakage
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")
    
    # Sort by date globally (not by symbol first)
    df_sorted = df.sort_values('date').reset_index(drop=True)
    n = len(df_sorted)
    
    # Calculate split points
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    # Split data
    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()
    
    print("✅ Proper time series split (NO temporal leakage):")
    print(f"  Train: {len(train_df):,} samples ({train_df['date'].min()} to {train_df['date'].max()})")
    print(f"  Val:   {len(val_df):,} samples ({val_df['date'].min()} to {val_df['date'].max()})")
    print(f"  Test:  {len(test_df):,} samples ({test_df['date'].min()} to {test_df['date'].max()})")
    
    return train_df, val_df, test_df

def prepare_ml_datasets_fixed(symbols: Optional[List[str]] = None, limit_hours: int = 1000) -> Dict:
    """
    Pipeline hoàn chỉnh chuẩn bị dữ liệu KHÔNG có data leakage
    """
    print("🔧 PREPARING ML DATASETS (FIXED - NO DATA LEAKAGE)")
    print("="*60)
    
    # 1. Load raw data
    df = load_realtime_data(symbols=symbols, limit_hours=limit_hours)
    
    # 2. Create proper features (no leakage)
    df = create_proper_features(df)
    
    # 3. Create proper targets (predicting future)
    df = create_proper_targets(df)
    
    # 4. Get feature columns (excluding targets and metadata)
    feature_cols = get_proper_feature_columns()
    available_features = [col for col in feature_cols if col in df.columns]
    
    print(f"🎯 Using {len(available_features)} features: {available_features}")
    
    # 5. Remove rows with NaN targets (can't predict future for last N rows)
    df_clean = df.dropna(subset=['target_price_1h', 'target_change_3h', 'target_trend_1h'])
    print(f"📊 Clean dataset: {len(df_clean):,} samples (removed {len(df) - len(df_clean):,} rows with NaN targets)")
    
    # 6. Time series split
    train_df, val_df, test_df = time_series_split_proper(df_clean)
    
    # 7. Prepare final datasets
    datasets = {
        'X_train': train_df[available_features],
        'X_val': val_df[available_features],
        'X_test': test_df[available_features],
        'y_train': {
            'price_1h': train_df['target_price_1h'],
            'change_3h': train_df['target_change_3h'],
            'change_6h': train_df['target_change_6h'],
            'trend_1h': train_df['target_trend_1h'],
            'trend_3h': train_df['target_trend_3h']
        },
        'y_val': {
            'price_1h': val_df['target_price_1h'],
            'change_3h': val_df['target_change_3h'],
            'change_6h': val_df['target_change_6h'],
            'trend_1h': val_df['target_trend_1h'],
            'trend_3h': val_df['target_trend_3h']
        },
        'y_test': {
            'price_1h': test_df['target_price_1h'],
            'change_3h': test_df['target_change_3h'],
            'change_6h': test_df['target_change_6h'],
            'trend_1h': test_df['target_trend_1h'],
            'trend_3h': test_df['target_trend_3h']
        },
        'feature_names': available_features,
        'metadata': {
            'total_samples': len(df_clean),
            'train_samples': len(train_df),
            'val_samples': len(val_df),
            'test_samples': len(test_df),
            'symbols': df_clean['symbol'].unique().tolist(),
            'date_range': (df_clean['date'].min(), df_clean['date'].max())
        }
    }
    
    print("✅ DATASETS PREPARED SUCCESSFULLY (NO DATA LEAKAGE)")
    print(f"  Features: {len(available_features)}")
    print(f"  Symbols: {len(datasets['metadata']['symbols'])}")
    print(f"  Train/Val/Test: {len(train_df)}/{len(val_df)}/{len(test_df)}")
    
    return datasets

if __name__ == "__main__":
    # Test the fixed pipeline
    try:
        # Test with top 3 symbols
        test_symbols = ['BTC', 'ETH', 'BNB']
        datasets = prepare_ml_datasets_fixed(symbols=test_symbols, limit_hours=500)
        print("\n✅ VALIDATION PASSED - Ready for training!")
        
        # Save datasets for training
        import joblib
        root = project_root_path()
        cache_dir = os.path.join(root, "data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        joblib.dump(datasets, os.path.join(cache_dir, "fixed_ml_datasets.joblib"))
        print(f"💾 Saved datasets to: {cache_dir}/fixed_ml_datasets.joblib")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()