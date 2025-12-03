"""
Utility functions for Streamlit Dashboard
Database connection, data fetching, formatting
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """SQLite database connector for dashboard"""
    
    def __init__(self, db_path: str = "data/trading_logs.db"):
        self.db_path = Path(db_path)
    
    def get_connection(self):
        """Get database connection"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database {self.db_path} không tồn tại")
        return sqlite3.connect(str(self.db_path))
    
    def get_all_trades(self) -> pd.DataFrame:
        """Fetch all trades"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC", conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_recent_trades(self, limit: int = 50) -> pd.DataFrame:
        """Fetch recent trades"""
        conn = self.get_connection()
        query = f"SELECT * FROM trades ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_open_positions(self) -> pd.DataFrame:
        """Fetch currently open positions"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM positions ORDER BY timestamp DESC",
            conn
        )
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_equity_curve(self) -> pd.DataFrame:
        """Fetch equity curve data"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM equity ORDER BY timestamp ASC",
            conn
        )
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_trades = cursor.fetchone()[0]
        
        # Realized PnL (closed positions)
        cursor.execute("""
            SELECT SUM(pnl) FROM trades 
            WHERE status = 'CLOSED' AND pnl IS NOT NULL
        """)
        realized_pnl = cursor.fetchone()[0] or 0
        
        # Unrealized PnL (open positions)
        cursor.execute("""
            SELECT SUM(unrealized_pnl) FROM positions
        """)
        unrealized_pnl = cursor.fetchone()[0] or 0
        
        # Total fees
        cursor.execute("SELECT SUM(fee) FROM trades WHERE fee IS NOT NULL")
        total_fees = cursor.fetchone()[0] or 0
        
        # Win rate
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
            FROM trades 
            WHERE status = 'CLOSED' AND pnl IS NOT NULL
        """)
        win_rate = cursor.fetchone()[0] or 0
        
        # Average PnL per trade
        cursor.execute("""
            SELECT AVG(pnl) FROM trades 
            WHERE status = 'CLOSED' AND pnl IS NOT NULL
        """)
        avg_pnl = cursor.fetchone()[0] or 0
        
        # Latest equity
        cursor.execute("""
            SELECT total_value, cash, positions_value 
            FROM equity 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        equity_row = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_fees': total_fees,
            'net_pnl': realized_pnl + unrealized_pnl - total_fees,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'total_value': equity_row[0] if equity_row else 0,
            'cash': equity_row[1] if equity_row else 0,
            'positions_value': equity_row[2] if equity_row else 0
        }


def format_currency(value: float, include_sign: bool = True) -> str:
    """
    Format value as currency with color
    
    Args:
        value: Numeric value
        include_sign: Include +/- sign
    
    Returns:
        Formatted string
    """
    sign = "+" if value > 0 else ""
    if include_sign:
        return f"{sign}${value:,.2f}"
    return f"${abs(value):,.2f}"


def format_percentage(value: float, include_sign: bool = True) -> str:
    """
    Format value as percentage
    
    Args:
        value: Numeric value (0-100)
        include_sign: Include +/- sign
    
    Returns:
        Formatted string
    """
    sign = "+" if value > 0 else ""
    if include_sign:
        return f"{sign}{value:.2f}%"
    return f"{abs(value):.2f}%"


def get_color_for_pnl(pnl: float) -> str:
    """
    Get color based on PnL value
    
    Args:
        pnl: Profit/Loss value
    
    Returns:
        Color name (green, red, gray)
    """
    if pnl > 0:
        return "green"
    elif pnl < 0:
        return "red"
    return "gray"
