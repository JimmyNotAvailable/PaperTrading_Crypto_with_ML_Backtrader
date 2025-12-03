"""
Feature Engineering Module for Crypto ML Trading
=================================================
Shared module used by both training scripts and real-time ML consumer.
Ensures consistent feature calculation logic across training and production.

Features calculated:
- SMA_10, SMA_50: Simple Moving Averages
- EMA_12, EMA_26: Exponential Moving Averages
- RSI_14: Relative Strength Index
- MACD, MACD_signal, MACD_hist: MACD indicators
- BB_UPPER, BB_LOWER, BB_MID: Bollinger Bands
- ATR_14: Average True Range (volatility)
- Volume_SMA: Volume moving average
- Price_Change_Pct: Price change percentage
- Volatility_20: 20-period rolling volatility
- target: Binary classification (1=price up, 0=price down) - training only
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Optional


def calculate_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """
    Calculate technical indicators for ML features.
    
    Args:
        df: DataFrame with OHLCV columns (open, high, low, close, volume)
        include_target: If True, calculate 'target' column for training.
                       Set False for real-time prediction.
    
    Returns:
        DataFrame with added feature columns
        
    Example:
        >>> df = pd.DataFrame({
        ...     'close': [100, 101, 102, 103, 104],
        ...     'volume': [1000, 1100, 1200, 1300, 1400]
        ... })
        >>> df_features = calculate_features(df, include_target=True)
    """
    df = df.copy()
    
    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    
    # 1. Trend Indicators
    df['SMA_10'] = ta.sma(df['close'], length=10)
    df['SMA_50'] = ta.sma(df['close'], length=50)
    df['EMA_12'] = ta.ema(df['close'], length=12)
    df['EMA_26'] = ta.ema(df['close'], length=26)
    
    # 2. Momentum Indicators
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    
    # MACD (Moving Average Convergence Divergence)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        df['MACD'] = macd.iloc[:, 0]
        df['MACD_signal'] = macd.iloc[:, 1]
        df['MACD_hist'] = macd.iloc[:, 2]
    else:
        df['MACD'] = 0
        df['MACD_signal'] = 0
        df['MACD_hist'] = 0
    
    # 3. Volatility Indicators
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20, lower_std=2.0, upper_std=2.0)
    if bb is not None and not bb.empty:
        df['BB_UPPER'] = bb.iloc[:, 0]
        df['BB_MID'] = bb.iloc[:, 1]
        df['BB_LOWER'] = bb.iloc[:, 2]
        # BB Width (normalized volatility indicator)
        df['BB_WIDTH'] = (df['BB_UPPER'] - df['BB_LOWER']) / df['BB_MID']
    else:
        df['BB_UPPER'] = df['close']
        df['BB_MID'] = df['close']
        df['BB_LOWER'] = df['close']
        df['BB_WIDTH'] = 0
    
    # ATR (Average True Range)
    df['ATR_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # 4. Volume Indicators
    df['Volume_SMA'] = ta.sma(df['volume'], length=20)
    df['Volume_Ratio'] = df['volume'] / (df['Volume_SMA'] + 1e-9)  # Avoid division by zero
    
    # 5. Price-based Features
    df['Price_Change_Pct'] = df['close'].pct_change()
    df['Volatility_20'] = df['close'].rolling(window=20).std()
    
    # High-Low range
    df['HL_Ratio'] = (df['high'] - df['low']) / (df['close'] + 1e-9)
    
    # 6. Lag Features (past price momentum)
    df['Returns_1'] = df['close'].pct_change(1)
    df['Returns_5'] = df['close'].pct_change(5)
    df['Returns_10'] = df['close'].pct_change(10)
    
    # 7. Target Variable (Only for training)
    if include_target:
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # Drop NaN rows caused by indicator calculations
    df.dropna(inplace=True)
    
    return df


def get_feature_columns() -> list[str]:
    """
    Return list of feature column names used for ML models.
    
    Returns:
        List of feature column names
    """
    return [
        # Price-based
        'close', 'open', 'high', 'low', 'volume',
        
        # Trend
        'SMA_10', 'SMA_50', 'EMA_12', 'EMA_26',
        
        # Momentum
        'RSI_14', 'MACD', 'MACD_signal', 'MACD_hist',
        
        # Volatility
        'BB_WIDTH', 'ATR_14', 'Volatility_20', 'HL_Ratio',
        
        # Volume
        'Volume_SMA', 'Volume_Ratio',
        
        # Price changes
        'Price_Change_Pct', 'Returns_1', 'Returns_5', 'Returns_10'
    ]


def validate_features(df: pd.DataFrame) -> bool:
    """
    Validate that all required features exist in DataFrame.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if all features exist, False otherwise
    """
    required_features = get_feature_columns()
    return all(col in df.columns for col in required_features)


if __name__ == "__main__":
    # Test feature engineering with sample data
    print("🧪 Testing Feature Engineering Module...")
    
    # Create sample OHLCV data
    import numpy as np
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    sample_data = pd.DataFrame({
        'timestamp': [int(d.timestamp() * 1000) for d in dates],
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 5000, 100)
    })
    
    # Calculate features
    df_features = calculate_features(sample_data, include_target=True)
    
    print(f"✅ Original data: {len(sample_data)} rows")
    print(f"✅ After feature engineering: {len(df_features)} rows")
    print(f"✅ Columns: {list(df_features.columns)}")
    print(f"\n📊 Sample features:")
    print(df_features[get_feature_columns() + ['target']].tail())
    
    # Validate
    if validate_features(df_features):
        print("\n✅ All features validated successfully!")
    else:
        print("\n❌ Feature validation failed!")
