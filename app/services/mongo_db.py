"""
MongoDB Service Layer for Phase 5
Manages users, trades, and balance operations
"""

import os
import time
import bcrypt
from typing import Dict, List, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv

load_dotenv()


class MongoDB:
    """MongoDB Service for Backtrader Engine"""
    
    def __init__(self):
        # Connection setup
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        database_name = os.getenv('MONGODB_DATABASE', 'crypto_trading_db')
        
        self.client = MongoClient(mongodb_uri)
        self.db: Database = self.client[database_name]
        
        # Collections
        self.users: Collection = self.db['users']
        self.trades: Collection = self.db['trades']
        self.ml_signals: Collection = self.db['ml_signals']
        self.market_data: Collection = self.db['market_data']
        
        # Create indexes
        self._create_indexes()
        
        print(f"✅ MongoDB Connected: {database_name}")
    
    def _create_indexes(self):
        """Create necessary indexes for performance"""
        # Users indexes
        self.users.create_index([('username', ASCENDING)], unique=True)
        
        # Trades indexes
        self.trades.create_index([('username', ASCENDING), ('timestamp', DESCENDING)])
        self.trades.create_index([('status', ASCENDING)])
        self.trades.create_index([('symbol', ASCENDING)])
        
        # ML signals indexes
        self.ml_signals.create_index([('symbol', ASCENDING), ('timestamp', DESCENDING)])
        
        # Market data indexes
        self.market_data.create_index([('symbol', ASCENDING), ('timestamp', DESCENDING)])
    
    # ========================
    # USER MANAGEMENT
    # ========================
    
    def create_user(self, username: str, password: str, initial_balance: float = 5000.0) -> Dict:
        """Create new user with hashed password"""
        # Check if user exists
        if self.users.find_one({'username': username}):
            raise ValueError(f"User {username} already exists")
        
        # Hash password
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user = {
            'username': username,
            'password': hashed_pw,
            'initial_balance': initial_balance,
            'current_balance': initial_balance,
            'created_at': time.time(),
            'updated_at': time.time()
        }
        
        self.users.insert_one(user)
        print(f"✅ User created: {username} with ${initial_balance:,.2f}")
        return user
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        return self.users.find_one({'username': username})
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify user password"""
        user = self.get_user(username)
        if not user:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), user['password'])
    
    def update_balance(self, username: str, amount: float):
        """Update user balance (can be positive or negative)"""
        result = self.users.update_one(
            {'username': username},
            {
                '$inc': {'current_balance': amount},
                '$set': {'updated_at': time.time()}
            }
        )
        
        if result.modified_count > 0:
            user = self.get_user(username)
            if user:
                print(f"💰 Balance updated: {username} -> ${user['current_balance']:,.2f}")
    
    def get_balance(self, username: str) -> float:
        """Get current balance"""
        user = self.get_user(username)
        return user['current_balance'] if user else 0.0
    
    # ========================
    # TRADE MANAGEMENT
    # ========================
    
    def insert_trade(self, trade_data: Dict) -> str:
        """Insert new trade record"""
        trade_data['timestamp'] = trade_data.get('timestamp', time.time())
        result = self.trades.insert_one(trade_data)
        return str(result.inserted_id)
    
    def get_open_trade(self, username: str, symbol: Optional[str] = None) -> Optional[Dict]:
        """Get first open trade for user"""
        query = {'username': username, 'status': 'OPEN'}
        if symbol:
            query['symbol'] = symbol
        
        return self.trades.find_one(query, sort=[('timestamp', ASCENDING)])
    
    def get_all_open_trades(self, username: str) -> List[Dict]:
        """Get all open trades for user"""
        return list(self.trades.find(
            {'username': username, 'status': 'OPEN'}
        ).sort('timestamp', ASCENDING))
    
    def close_trade(self, trade_id: str, exit_price: float, pnl: float):
        """Close a trade"""
        from bson.objectid import ObjectId
        
        result = self.trades.update_one(
            {'_id': ObjectId(trade_id)},
            {
                '$set': {
                    'status': 'CLOSED',
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'closed_at': time.time()
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Trade closed: ID={trade_id}, PnL=${pnl:,.2f}")
    
    def get_trades_history(self, username: str, limit: int = 50) -> List[Dict]:
        """Get trade history for user"""
        return list(self.trades.find(
            {'username': username}
        ).sort('timestamp', DESCENDING).limit(limit))
    
    def get_closed_trades(self, username: str) -> List[Dict]:
        """Get all closed trades"""
        return list(self.trades.find(
            {'username': username, 'status': 'CLOSED'}
        ).sort('timestamp', DESCENDING))
    
    # ========================
    # ML SIGNALS
    # ========================
    
    def save_ml_signal(self, signal_data: Dict):
        """Save ML signal for tracking"""
        signal_data['timestamp'] = signal_data.get('timestamp', time.time())
        self.ml_signals.insert_one(signal_data)
    
    def get_recent_signals(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get recent ML signals"""
        query = {}
        if symbol:
            query['symbol'] = symbol
        
        return list(self.ml_signals.find(query).sort('timestamp', DESCENDING).limit(limit))
    
    # ========================
    # MARKET DATA
    # ========================
    
    def save_market_data(self, market_data: Dict):
        """Save market data tick"""
        market_data['timestamp'] = market_data.get('timestamp', time.time())
        self.market_data.insert_one(market_data)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol"""
        data = self.market_data.find_one(
            {'symbol': symbol},
            sort=[('timestamp', DESCENDING)]
        )
        return data.get('price') if data else None
    
    # ========================
    # STATISTICS
    # ========================
    
    def get_trading_stats(self, username: str) -> Dict:
        """Calculate trading statistics"""
        closed_trades = self.get_closed_trades(username)
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        wins = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losses = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses)) if losses else 0
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': (avg_win / avg_loss) if avg_loss > 0 else 0
        }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        print("MongoDB connection closed")


# Initialize default admin user if needed
def init_default_user():
    """Initialize default admin user for testing"""
    db = MongoDB()
    
    try:
        db.create_user('admin', 'admin123', initial_balance=5000.0)
    except ValueError:
        print("ℹ️  Admin user already exists")
    
    db.close()


if __name__ == "__main__":
    # Test MongoDB connection and create admin user
    init_default_user()
