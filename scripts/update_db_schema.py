"""
Database Schema Migration for Phase 5 Dashboard
Adds: status, unrealized_pnl, fee columns to trades table
"""
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path: str = "data/trading_logs.db"):
    """
    Add new columns for Phase 5 Dashboard features:
    - status: OPEN/CLOSED
    - unrealized_pnl: For open positions
    - fee: Alias for commission (for clarity)
    """
    db_file = Path(db_path)
    if not db_file.exists():
        logger.warning(f"Database {db_path} không tồn tại. Sẽ được tạo khi chạy Backtrader.")
        return
    
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(trades)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    logger.info(f"Existing columns: {existing_columns}")
    
    # Add status column if not exists
    if 'status' not in existing_columns:
        cursor.execute("""
            ALTER TABLE trades ADD COLUMN status TEXT DEFAULT 'CLOSED'
        """)
        logger.info("✅ Added column: status")
    
    # Add unrealized_pnl column if not exists
    if 'unrealized_pnl' not in existing_columns:
        cursor.execute("""
            ALTER TABLE trades ADD COLUMN unrealized_pnl REAL DEFAULT 0
        """)
        logger.info("✅ Added column: unrealized_pnl")
    
    # Add fee column if not exists (alias for commission for dashboard clarity)
    if 'fee' not in existing_columns:
        cursor.execute("""
            ALTER TABLE trades ADD COLUMN fee REAL DEFAULT 0
        """)
        # Copy commission to fee for existing records
        cursor.execute("""
            UPDATE trades SET fee = commission WHERE fee = 0
        """)
        logger.info("✅ Added column: fee (copied from commission)")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Migration hoàn tất: {db_path}")

if __name__ == "__main__":
    migrate_database()
