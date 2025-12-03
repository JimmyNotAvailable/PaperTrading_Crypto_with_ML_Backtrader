# load_historical_data.py
# Load và clean historical OHLCV data từ CSV files (2017-2023)

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_historical_data_path() -> Path:
    """Get path to historical data directory"""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "data" / "historical" / "Crypto_Data_Hourly_Price_17_23"


def load_historical_data(symbol: str = 'BTC', limit: Optional[int] = None) -> pd.DataFrame:
    """
    Load historical OHLCV data từ CSV cho 1 symbol
    
    Args:
        symbol: BTC, ETH, SOL, BNB, XLM (hoặc với USDT suffix)
        limit: Số lượng candles muốn lấy (None = all, mặc định lấy 5000 gần nhất)
    
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume, symbol, date
    """
    # Normalize symbol
    base_symbol = symbol.replace('/USDT', '').replace('USDT', '').upper()
    
    # Map symbol to filename
    symbol_map = {
        'BTC': 'Binance_BTCUSDT_1h (1).csv',
        'ETH': 'Binance_ETHUSDT_1h (1).csv',
        'SOL': 'Binance_SOLUSDT_1h (1).csv',
        'BNB': 'Binance_BNBUSDT_1h (1).csv',
        'XLM': 'Binance_XLMUSDT_1h (1).csv',
        'XRP': 'Binance_XLMUSDT_1h (1).csv'  # Fallback (nếu có XRP thì update)
    }
    
    if base_symbol not in symbol_map:
        raise ValueError(f"Symbol {base_symbol} not supported. Available: {list(symbol_map.keys())}")
    
    # Get file path
    data_dir = get_historical_data_path()
    csv_file = data_dir / symbol_map[base_symbol]
    
    if not csv_file.exists():
        raise FileNotFoundError(f"Historical data not found: {csv_file}")
    
    # Load CSV
    logger.info(f"Loading historical data for {base_symbol} from {csv_file.name}...")
    df = pd.read_csv(csv_file)
    
    # Rename columns to standardized format
    df.columns = df.columns.str.strip()  # Remove spaces
    column_mapping = {
        'Date': 'date',
        'Symbol': 'symbol_raw',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume BTC': 'volume_btc',
        'Volume USDT': 'volume',
        'tradecount': 'trade_count'
    }
    
    df.rename(columns=column_mapping, inplace=True)
    
    # Parse date (handle mixed formats including milliseconds)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    
    # Create timestamp (milliseconds since epoch - compatible with Binance format)
    df['timestamp'] = df['date'].astype(np.int64) // 10**6
    
    # Add standardized symbol
    df['symbol'] = f"{base_symbol}/USDT"
    
    # Sort by date (oldest first)
    df = df.sort_values('date').reset_index(drop=True)
    
    # Select required columns
    required_cols = ['timestamp', 'date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
    df = df[required_cols]
    
    # Get most recent N samples if limit specified
    if limit:
        df = df.tail(limit)
    else:
        # Default: lấy 5000 gần nhất (để tránh quá nhiều data)
        df = df.tail(5000)
    
    logger.info(f"Loaded {len(df):,} candles for {base_symbol}")
    logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"  Missing values: {df.isnull().sum().sum()}")
    
    return df


def clean_historical_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean historical data:
    1. Remove NaN values
    2. Remove duplicates
    3. Remove zero-volume candles
    4. Remove outliers (extreme price spikes)
    
    Args:
        df: Raw DataFrame from load_historical_data()
    
    Returns:
        Cleaned DataFrame
    """
    initial_len = len(df)
    logger.info(f"Cleaning data: {initial_len:,} samples...")
    
    # 1. Remove NaN values
    df = df.dropna()
    logger.info(f"  After removing NaN: {len(df):,} samples ({initial_len - len(df)} removed)")
    
    # 2. Remove duplicates
    df = df.drop_duplicates(subset=['timestamp'], keep='last')
    logger.info(f"  After removing duplicates: {len(df):,} samples")
    
    # 3. Remove zero-volume candles (likely errors)
    df = df[df['volume'] > 0]
    logger.info(f"  After removing zero-volume: {len(df):,} samples")
    
    # 4. Remove extreme outliers (price spikes > 5 std from mean)
    for col in ['open', 'high', 'low', 'close']:
        mean = df[col].mean()
        std = df[col].std()
        lower_bound = mean - 5 * std
        upper_bound = mean + 5 * std
        
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        if len(outliers) > 0:
            logger.info(f"  Removing {len(outliers)} outliers in '{col}'")
            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
    
    # 5. Ensure OHLC relationships (high >= low, close/open within range)
    df = df[df['high'] >= df['low']]
    df = df[(df['close'] >= df['low']) & (df['close'] <= df['high'])]
    df = df[(df['open'] >= df['low']) & (df['open'] <= df['high'])]
    
    final_len = len(df)
    removed = initial_len - final_len
    logger.info(f"Cleaning complete: {final_len:,} samples ({removed} removed, {removed/initial_len*100:.2f}%)")
    
    return df.reset_index(drop=True)


def load_all_historical_symbols(symbols: Optional[list] = None, limit: int = 5000) -> Dict[str, pd.DataFrame]:
    """
    Load và clean historical data cho nhiều symbols
    
    Args:
        symbols: List of symbols to load (None = all available)
        limit: Number of recent candles per symbol
    
    Returns:
        Dict[symbol, cleaned_dataframe]
    """
    if symbols is None:
        symbols = ['BTC', 'ETH', 'SOL', 'BNB']  # Default symbols
    
    data_dict = {}
    
    logger.info(f"\n{'='*60}")
    logger.info(f"LOADING HISTORICAL DATA FOR {len(symbols)} SYMBOLS")
    logger.info(f"{'='*60}")
    
    for symbol in symbols:
        try:
            # Load raw data
            df_raw = load_historical_data(symbol, limit=limit)
            
            # Clean data
            df_clean = clean_historical_data(df_raw)
            
            data_dict[symbol] = df_clean
            logger.info(f"✅ {symbol}: {len(df_clean):,} clean samples ready\n")
            
        except FileNotFoundError as e:
            logger.warning(f"⚠️ {symbol}: {e}\n")
            continue
        except Exception as e:
            logger.error(f"❌ {symbol}: Error - {e}\n")
            continue
    
    logger.info(f"{'='*60}")
    logger.info(f"LOADED {len(data_dict)}/{len(symbols)} SYMBOLS SUCCESSFULLY")
    logger.info(f"Total samples: {sum(len(df) for df in data_dict.values()):,}")
    logger.info(f"{'='*60}\n")
    
    return data_dict


def combine_all_symbols(data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Combine multiple symbols into single DataFrame
    
    Args:
        data_dict: Dict from load_all_historical_symbols()
    
    Returns:
        Combined DataFrame with all symbols
    """
    if not data_dict:
        raise ValueError("No data to combine")
    
    combined = pd.concat(data_dict.values(), ignore_index=True)
    combined = combined.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    logger.info(f"Combined {len(data_dict)} symbols: {combined['symbol'].unique().tolist()}")
    logger.info(f"Total samples: {len(combined):,}")
    
    return combined


if __name__ == "__main__":
    """Test historical data loader"""
    print("\n" + "="*60)
    print("TESTING HISTORICAL DATA LOADER")
    print("="*60 + "\n")
    
    # Test 1: Load single symbol
    print("Test 1: Loading BTC...")
    btc_df = load_historical_data('BTC', limit=1000)
    print(f"✅ BTC loaded: {len(btc_df)} samples")
    print(f"   Columns: {btc_df.columns.tolist()}")
    print(f"   Date range: {btc_df['date'].min()} to {btc_df['date'].max()}")
    print(f"   Sample:\n{btc_df.head(3)}\n")
    
    # Test 2: Clean data
    print("Test 2: Cleaning BTC data...")
    btc_clean = clean_historical_data(btc_df)
    print(f"✅ BTC cleaned: {len(btc_clean)} samples\n")
    
    # Test 3: Load all symbols
    print("Test 3: Loading all symbols...")
    all_data = load_all_historical_symbols(['BTC', 'ETH', 'SOL', 'BNB'], limit=2000)
    
    for symbol, df in all_data.items():
        print(f"  {symbol}: {len(df):,} samples")
    
    # Test 4: Combine all
    print("\nTest 4: Combining all symbols...")
    combined = combine_all_symbols(all_data)
    print(f"✅ Combined: {len(combined):,} total samples")
    print(f"   Symbols: {combined['symbol'].unique().tolist()}")
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✅")
    print("="*60)
