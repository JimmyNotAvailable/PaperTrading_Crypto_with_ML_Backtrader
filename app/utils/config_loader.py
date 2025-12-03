"""
Safe environment variable loader for Crypto ML Trading Project

Follows security patterns from copilot-instructions.md:
- Load from .env file (NEVER commit)
- Provide secure defaults
- Validate critical variables
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False
    import warnings
    warnings.warn(
        "python-dotenv not installed. Environment variables will only be loaded from system. "
        "Install it: pip install python-dotenv",
        ImportWarning
    )
    
    def load_dotenv(*args, **kwargs) -> bool:
        """Fallback if python-dotenv not installed"""
        return False

# Auto-load .env file
def load_env_file():
    """Load environment variables from .env file"""
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        return True
    return False

# Load on import
_env_loaded = load_env_file()

def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Safely get environment variable
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Raise error if not found and no default
    
    Returns:
        Environment variable value or default
    
    Raises:
        ValueError: If required=True and variable not found
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' not found")
    
    return value

def get_discord_token() -> Optional[str]:
    """
    Get Discord bot token following priority from copilot-instructions.md:
    1. DISCORD_BOT_TOKEN (recommended)
    2. BOT_TOKEN (legacy)
    3. None
    
    Returns:
        Discord bot token or None
    """
    token = get_env('DISCORD_BOT_TOKEN')
    if token:
        return token
    
    # Legacy support
    token = get_env('BOT_TOKEN')
    if token:
        return token
    
    return None

def get_kafka_bootstrap_servers() -> str:
    """Get Kafka bootstrap servers with default"""
    return get_env('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092') or 'localhost:9092'

def get_kafka_group_id() -> str:
    """Get Kafka consumer group ID with default"""
    return get_env('KAFKA_GROUP_ID', 'crypto_ml_group') or 'crypto_ml_group'

def get_mongodb_uri() -> str:
    """Get MongoDB URI with default"""
    return get_env('MONGODB_URI', 'mongodb://localhost:27017/crypto') or 'mongodb://localhost:27017/crypto'

def get_log_level() -> str:
    """Get log level with default"""
    return get_env('LOG_LEVEL', 'INFO') or 'INFO'
