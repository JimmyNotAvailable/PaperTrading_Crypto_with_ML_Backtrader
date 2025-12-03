"""
Centralized logging configuration for Crypto ML Trading Project

Usage:
    from app.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Message")
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        format_string: Custom format string (optional)
    """
    # Get log level from env or parameter
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Default format with Vietnamese-friendly emojis
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[]
    )
    
    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_string))
    logging.getLogger().addHandler(console_handler)
    
    # File handler (if specified)
    if log_file is None:
        log_file = os.getenv('LOG_FILE')
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(format_string))
        logging.getLogger().addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance with proper configuration
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# Auto-setup on import
setup_logging()
