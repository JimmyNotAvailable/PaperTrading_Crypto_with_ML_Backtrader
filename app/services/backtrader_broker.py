"""
Backtrader Broker Integration with Kafka
Execution Engine cho Decision Phase 4
Theo UpgradeBacktraderML.md - Tối ưu cho Demo với Streamlit Dashboard

Architecture:
    Kafka ML Signals → Backtrader Strategy → Execution → SQLite Logs → Streamlit Dashboard

Features:
    - Zero latency execution (local)
    - Commission calculation (0.1%)
    - SQLite logging for dashboard
    - ML signal integration
    - Risk management (SL/TP)
"""
import backtrader as bt  # type: ignore
import logging
import sqlite3
import json
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Ghi logs trades vào SQLite để Streamlit Dashboard đọc real-time
    """
    
    def __init__(self, db_path: str = "data/trading_logs.db"):
        """
        Initialize trade logger
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create tables if not exists"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                value REAL NOT NULL,
                commission REAL NOT NULL,
                pnl REAL,
                pnl_pct REAL,
                reason TEXT,
                ml_signal TEXT,
                ml_confidence REAL,
                ml_details TEXT
            )
        """)
        
        # Equity curve table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_value REAL NOT NULL,
                cash REAL NOT NULL,
                positions_value REAL NOT NULL
            )
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                amount REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                unrealized_pnl_pct REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"[KHOI TAO] Trade logger: {self.db_path}")
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log a trade to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                timestamp, symbol, action, price, amount, value, commission,
                pnl, pnl_pct, reason, ml_signal, ml_confidence, ml_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('timestamp', datetime.now().isoformat()),
            trade_data['symbol'],
            trade_data['action'],
            trade_data['price'],
            trade_data['amount'],
            trade_data['value'],
            trade_data.get('commission', 0),
            trade_data.get('pnl'),
            trade_data.get('pnl_pct'),
            trade_data.get('reason'),
            trade_data.get('ml_signal'),
            trade_data.get('ml_confidence'),
            json.dumps(trade_data.get('ml_details', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def log_equity(self, equity_data: Dict[str, float]):
        """Log equity snapshot"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO equity (timestamp, total_value, cash, positions_value)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            equity_data['total_value'],
            equity_data['cash'],
            equity_data['positions_value']
        ))
        
        conn.commit()
        conn.close()
    
    def log_position(self, position_data: Dict[str, Any]):
        """Log open position"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO positions (
                timestamp, symbol, entry_price, current_price, amount,
                unrealized_pnl, unrealized_pnl_pct, stop_loss, take_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            position_data['symbol'],
            position_data['entry_price'],
            position_data['current_price'],
            position_data['amount'],
            position_data['unrealized_pnl'],
            position_data['unrealized_pnl_pct'],
            position_data.get('stop_loss'),
            position_data.get('take_profit')
        ))
        
        conn.commit()
        conn.close()


class MLKafkaStrategy(bt.Strategy):  # type: ignore
    """
    Backtrader Strategy nhận ML signals từ external source (Kafka)
    Tương tự ml_strategy.py nhưng tối ưu cho production với logging
    """
    
    params = (
        ('stop_loss_pct', 0.02),      # 2% Stop Loss
        ('take_profit_pct', 0.05),    # 5% Take Profit
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('min_confidence', 0.60),
        ('position_size_pct', 0.95),
        ('log_db_path', 'data/trading_logs.db'),
    )
    
    def __init__(self):
        """Initialize strategy"""
        self.dataclose = self.datas[0].close  # type: ignore
        self.rsi = bt.indicators.RSI(self.datas[0], period=14)  # type: ignore
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # ML Signal storage (set từ bên ngoài)
        self.current_ml_signal = None
        self.current_ml_confidence = 0.0
        self.current_ml_details = {}
        self.symbol = 'UNKNOWN'
        
        # Trade logger
        self.trade_logger = TradeLogger(self.params.log_db_path)  # type: ignore
        
        logger.info("🧠 MLKafkaStrategy initialized")
        logger.info(f"   SL: {self.params.stop_loss_pct*100}%, TP: {self.params.take_profit_pct*100}%")  # type: ignore
    
    def set_signal(self, symbol: str, signal: str, confidence: float, details: Optional[Dict[str, Any]] = None):
        """Set ML signal from Kafka consumer"""
        self.symbol = symbol
        self.current_ml_signal = signal
        self.current_ml_confidence = confidence
        self.current_ml_details = details or {}
        
        logger.debug(f"[TIN HIEU] [{symbol}] {signal} (Do tin cay: {confidence:.2%})")
    
    def notify_order(self, order):  # type: ignore
        """Callback when order status changes"""
        if order.status in [order.Submitted, order.Accepted]:  # type: ignore
            return
        
        if order.status in [order.Completed]:  # type: ignore
            if order.isbuy():  # type: ignore
                self.buyprice = order.executed.price  # type: ignore
                self.buycomm = order.executed.comm  # type: ignore
                
                # Log BUY trade
                self.trade_logger.log_trade({
                    'symbol': self.symbol,
                    'action': 'BUY',
                    'price': order.executed.price,  # type: ignore
                    'amount': order.executed.size,  # type: ignore
                    'value': order.executed.value,  # type: ignore
                    'commission': order.executed.comm,  # type: ignore
                    'reason': 'ML Signal',
                    'ml_signal': self.current_ml_signal,
                    'ml_confidence': self.current_ml_confidence,
                    'ml_details': self.current_ml_details
                })
                
                logger.info(f"[THUC HIEN] MUA {self.symbol} @ ${order.executed.price:,.2f}")  # type: ignore
            else:
                # Calculate PnL for SELL
                pnl = order.executed.value - (self.buyprice * order.executed.size)  # type: ignore
                pnl_pct = (pnl / (self.buyprice * order.executed.size)) * 100  # type: ignore
                
                # Log SELL trade
                self.trade_logger.log_trade({
                    'symbol': self.symbol,
                    'action': 'SELL',
                    'price': order.executed.price,  # type: ignore
                    'amount': order.executed.size,  # type: ignore
                    'value': order.executed.value,  # type: ignore
                    'commission': order.executed.comm,  # type: ignore
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'Exit Signal'
                })
                
                logger.info(f"[THUC HIEN] BAN {self.symbol} @ ${order.executed.price:,.2f} | PnL: {pnl_pct:+.2f}%")  # type: ignore
        
        self.order = None
    
    def next(self):  # type: ignore
        """Main strategy logic - called on each new bar"""
        current_price = self.dataclose[0]  # type: ignore
        current_rsi = self.rsi[0]  # type: ignore
        
        # Log equity periodically
        if len(self) % 10 == 0:  # Every 10 bars  # type: ignore
            self.trade_logger.log_equity({
                'total_value': self.broker.getvalue(),  # type: ignore
                'cash': self.broker.getcash(),  # type: ignore
                'positions_value': self.broker.getvalue() - self.broker.getcash()  # type: ignore
            })
        
        # Check BUY conditions
        if not self.position and self.current_ml_signal == 'BUY':  # type: ignore
            if self.current_ml_confidence >= self.params.min_confidence:  # type: ignore
                if current_rsi < self.params.rsi_overbought:  # type: ignore
                    cash = self.broker.getcash()  # type: ignore
                    size = (cash * self.params.position_size_pct) / current_price  # type: ignore
                    self.order = self.buy(size=size)  # type: ignore
        
        # Check SELL conditions
        elif self.position:  # type: ignore
            # ML signal SELL
            if self.current_ml_signal == 'SELL':
                self.order = self.sell()  # type: ignore
            
            # Stop Loss
            elif self.buyprice:
                loss_pct = (current_price - self.buyprice) / self.buyprice
                if loss_pct <= -self.params.stop_loss_pct:  # type: ignore
                    logger.warning(f"[CAT LO] Stop Loss kich hoat: {loss_pct:.2%}")
                    self.order = self.sell()  # type: ignore
                
                # Take Profit
                elif loss_pct >= self.params.take_profit_pct:  # type: ignore
                    logger.info(f"[CHOT LOI] Take Profit kich hoat: {loss_pct:.2%}")
                    self.order = self.sell()  # type: ignore


class BacktraderBroker:
    """
    Wrapper quản lý Backtrader Cerebro engine
    Kết nối với Kafka signals và produce orders
    """
    
    def __init__(
        self,
        initial_cash: float = 10000.0,
        commission: float = 0.001,
        db_path: str = "data/trading_logs.db"
    ):
        """
        Initialize Backtrader broker
        
        Args:
            initial_cash: Starting capital
            commission: Trading commission (0.1% = 0.001)
            db_path: SQLite database path for logging
        """
        self.cerebro = bt.Cerebro()  # type: ignore
        self.cerebro.broker.setcash(initial_cash)  # type: ignore
        self.cerebro.broker.setcommission(commission=commission)  # type: ignore
        
        # Add strategy
        self.cerebro.addstrategy(MLKafkaStrategy, log_db_path=db_path)  # type: ignore
        
        self.initial_cash = initial_cash
        self.trade_logger = TradeLogger(db_path)
        
        logger.info("[KHOI TAO] BacktraderBroker")
        logger.info(f"   Initial Cash: ${initial_cash:,.2f}")
        logger.info(f"   Commission: {commission*100}%")
    
    def add_data_feed(self, data_feed):  # type: ignore
        """Add data feed to cerebro"""
        self.cerebro.adddata(data_feed)  # type: ignore
    
    def run(self):
        """Run backtest/live trading"""
        logger.info("[BAT DAU] Chay Backtrader...")
        results = self.cerebro.run()  # type: ignore
        
        final_value = self.cerebro.broker.getvalue()  # type: ignore
        pnl = final_value - self.initial_cash
        pnl_pct = (pnl / self.initial_cash) * 100
        
        logger.info("="*60)
        logger.info(f"[KET QUA] Gia tri danh muc cuoi cung: ${final_value:,.2f}")
        logger.info(f"[KET QUA] Tong PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
        logger.info("="*60)
        
        return results
    
    def get_value(self) -> float:
        """Get current portfolio value"""
        return self.cerebro.broker.getvalue()  # type: ignore
    
    def get_cash(self) -> float:
        """Get current cash"""
        return self.cerebro.broker.getcash()  # type: ignore
