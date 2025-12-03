"""
Symbols Configuration for Crypto ML Trading System
===================================================
Centralized configuration for all supported trading pairs.
This ensures consistency across all modules (Producer, Training, ML Consumer, Bot).

Supported Symbols:
- BTC (Bitcoin)
- ETH (Ethereum)  
- XRP (Ripple)
- SOL (Solana)
- BNB (Binance Coin)
"""

from typing import List, Dict

# Primary supported symbols
SUPPORTED_SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'XRP/USDT',
    'SOL/USDT',
    'BNB/USDT'
]

# Symbol mapping for different formats
SYMBOL_MAPPING = {
    'BTC': 'BTC/USDT',
    'ETH': 'ETH/USDT',
    'XRP': 'XRP/USDT',
    'SOL': 'SOL/USDT',
    'BNB': 'BNB/USDT',
    'BTCUSDT': 'BTC/USDT',
    'ETHUSDT': 'ETH/USDT',
    'XRPUSDT': 'XRP/USDT',
    'SOLUSDT': 'SOL/USDT',
    'BNBUSDT': 'BNB/USDT'
}

# Display names (for Discord Bot)
SYMBOL_DISPLAY_NAMES = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'XRP': 'Ripple',
    'SOL': 'Solana',
    'BNB': 'Binance Coin'
}

# CoinGecko IDs for fallback API
COINGECKO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'XRP': 'ripple',
    'SOL': 'solana',
    'BNB': 'binancecoin'
}

# Default symbol for system
DEFAULT_SYMBOL = 'BTC/USDT'


def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol input to CCXT format (e.g., 'BTC/USDT').
    
    Args:
        symbol: Input symbol in any format (BTC, BTCUSDT, btc, etc.)
        
    Returns:
        Normalized symbol in CCXT format
        
    Examples:
        >>> normalize_symbol('BTC')
        'BTC/USDT'
        >>> normalize_symbol('ETHUSDT')
        'ETH/USDT'
        >>> normalize_symbol('sol')
        'SOL/USDT'
    """
    symbol_upper = symbol.upper().strip()
    
    # Direct match
    if symbol_upper in SYMBOL_MAPPING:
        return SYMBOL_MAPPING[symbol_upper]
    
    # Try to match base currency
    for base in ['BTC', 'ETH', 'XRP', 'SOL', 'BNB']:
        if base in symbol_upper:
            return SYMBOL_MAPPING[base]
    
    # Default fallback
    return DEFAULT_SYMBOL


def get_base_symbol(symbol: str) -> str:
    """
    Extract base currency from symbol (e.g., 'BTC/USDT' -> 'BTC').
    
    Args:
        symbol: Symbol in any format
        
    Returns:
        Base currency code
        
    Examples:
        >>> get_base_symbol('BTC/USDT')
        'BTC'
        >>> get_base_symbol('ETHUSDT')
        'ETH'
    """
    normalized = normalize_symbol(symbol)
    return normalized.split('/')[0]


def get_binance_format(symbol: str) -> str:
    """
    Convert to Binance REST API format (e.g., 'BTC/USDT' -> 'BTCUSDT').
    
    Args:
        symbol: Symbol in any format
        
    Returns:
        Binance format (no slash)
        
    Examples:
        >>> get_binance_format('BTC/USDT')
        'BTCUSDT'
    """
    normalized = normalize_symbol(symbol)
    return normalized.replace('/', '')


def is_valid_symbol(symbol: str) -> bool:
    """
    Check if symbol is supported.
    
    Args:
        symbol: Symbol to validate
        
    Returns:
        True if supported, False otherwise
    """
    try:
        normalized = normalize_symbol(symbol)
        return normalized in SUPPORTED_SYMBOLS
    except:
        return False


def get_coingecko_id(symbol: str) -> str:
    """
    Get CoinGecko ID for fallback API.
    
    Args:
        symbol: Symbol in any format
        
    Returns:
        CoinGecko ID
    """
    base = get_base_symbol(symbol)
    return COINGECKO_IDS.get(base, 'bitcoin')


def get_all_symbols() -> List[str]:
    """
    Get list of all supported symbols in CCXT format.
    
    Returns:
        List of symbols
    """
    return SUPPORTED_SYMBOLS.copy()


def get_symbol_info(symbol: str) -> Dict[str, str]:
    """
    Get comprehensive info about a symbol.
    
    Args:
        symbol: Symbol in any format
        
    Returns:
        Dictionary with symbol information
    """
    base = get_base_symbol(symbol)
    return {
        'base': base,
        'ccxt_format': normalize_symbol(symbol),
        'binance_format': get_binance_format(symbol),
        'display_name': SYMBOL_DISPLAY_NAMES.get(base, base),
        'coingecko_id': COINGECKO_IDS.get(base, base.lower())
    }


if __name__ == "__main__":
    # Test the configuration
    print("🧪 Testing Symbols Configuration...\n")
    
    test_cases = ['BTC', 'eth', 'XRPUSDT', 'SOL/USDT', 'bnb']
    
    for test in test_cases:
        print(f"Input: {test}")
        info = get_symbol_info(test)
        print(f"  ✅ Normalized: {info['ccxt_format']}")
        print(f"  📊 Binance Format: {info['binance_format']}")
        print(f"  💎 Display: {info['display_name']}")
        print(f"  🪙 CoinGecko: {info['coingecko_id']}")
        print(f"  ✓ Valid: {is_valid_symbol(test)}\n")
    
    print(f"📋 All supported symbols: {get_all_symbols()}")
