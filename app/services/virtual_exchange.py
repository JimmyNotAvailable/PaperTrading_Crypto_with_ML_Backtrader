"""
Virtual Exchange Simulator
Mô phỏng sàn giao dịch ảo để demo và test chiến lược trading
Theo thiết kế từ ToturialUpgrade.md
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Đại diện cho một lệnh giao dịch"""
    order_id: str
    symbol: str
    side: str  # 'BUY' hoặc 'SELL'
    price: float
    amount: float
    timestamp: int
    status: str = 'OPEN'  # 'OPEN', 'FILLED', 'CANCELLED'
    filled_price: Optional[float] = None
    filled_timestamp: Optional[int] = None


@dataclass
class Position:
    """Đại diện cho một vị thế đang mở"""
    symbol: str
    side: str
    entry_price: float
    amount: float
    entry_timestamp: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Trade:
    """Đại diện cho một giao dịch hoàn tất (entry + exit)"""
    symbol: str
    entry_price: float
    exit_price: float
    amount: float
    entry_time: int
    exit_time: int
    pnl: float
    pnl_percentage: float
    side: str  # 'LONG' hoặc 'SHORT'


class VirtualExchange:
    """
    Sàn giao dịch ảo
    
    Chức năng:
    - Quản lý số dư tài khoản (USDT)
    - Thực hiện khớp lệnh mua/bán
    - Tính toán lãi/lỗ (PnL)
    - Theo dõi lịch sử giao dịch
    - Áp dụng phí giao dịch (commission)
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission_rate: float = 0.001,  # 0.1% phí giao dịch
        max_position_size: float = 0.95  # Tối đa 95% số dư cho 1 lệnh
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission_rate = commission_rate
        self.max_position_size = max_position_size
        
        # Lưu trữ dữ liệu
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.orders: List[Order] = []
        self.trade_history: List[Trade] = []
        
        # Thống kê
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission_paid = 0.0
        
        logger.info(f"💰 Virtual Exchange initialized: ${initial_balance:,.2f} USDT")
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Tính tổng giá trị danh mục (balance + giá trị positions)
        
        Args:
            current_prices: Dict {symbol: current_price}
        """
        total = self.balance
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position_value = position.amount * current_prices[symbol]
                total += position_value
        
        return total
    
    def get_available_balance(self) -> float:
        """Số dư có thể sử dụng để mở lệnh mới"""
        return self.balance
    
    def can_open_position(self, symbol: str, price: float, amount: float) -> tuple[bool, str]:
        """
        Kiểm tra có thể mở vị thế mới không
        
        Returns:
            (can_open, reason)
        """
        # Kiểm tra đã có position cho symbol này chưa
        if symbol in self.positions:
            return False, f"Already have open position for {symbol}"
        
        # Tính giá trị lệnh
        order_value = price * amount
        commission = order_value * self.commission_rate
        total_cost = order_value + commission
        
        # Kiểm tra số dư
        if total_cost > self.balance:
            return False, f"Insufficient balance: need ${total_cost:,.2f}, have ${self.balance:,.2f}"
        
        # Kiểm tra không vượt max position size
        max_allowed = self.balance * self.max_position_size
        if order_value > max_allowed:
            return False, f"Order size ${order_value:,.2f} exceeds max position size ${max_allowed:,.2f}"
        
        return True, "OK"
    
    def open_position(
        self,
        symbol: str,
        price: float,
        amount: float,
        timestamp: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_details: Optional[dict] = None
    ) -> Optional[Position]:
        """
        Mở vị thế mới (BUY)
        
        Args:
            symbol: Ký hiệu coin (VD: BTCUSDT)
            price: Giá entry
            amount: Số lượng coin
            timestamp: Unix timestamp (ms)
            stop_loss: Giá stop loss (optional)
            take_profit: Giá take profit (optional)
            signal_details: Chi tiết tín hiệu ML (optional)
        
        Returns:
            Position object nếu thành công, None nếu thất bại
        """
        can_open, reason = self.can_open_position(symbol, price, amount)
        
        if not can_open:
            logger.warning(f"❌ Cannot open position for {symbol}: {reason}")
            return None
        
        # Tính chi phí
        order_value = price * amount
        commission = order_value * self.commission_rate
        total_cost = order_value + commission
        
        # Trừ số dư
        self.balance -= total_cost
        self.total_commission_paid += commission
        
        # Tạo position
        position = Position(
            symbol=symbol,
            side='LONG',
            entry_price=price,
            amount=amount,
            entry_timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[symbol] = position
        
        # Log chi tiết
        logger.info(f"🟢 OPENED POSITION: {symbol}")
        logger.info(f"   Entry Price: ${price:,.2f}")
        logger.info(f"   Amount: {amount:.6f}")
        logger.info(f"   Total Cost: ${total_cost:,.2f} (Commission: ${commission:,.2f})")
        logger.info(f"   Remaining Balance: ${self.balance:,.2f}")
        if stop_loss:
            logger.info(f"   Stop Loss: ${stop_loss:,.2f} ({((stop_loss-price)/price*100):.2f}%)")
        if take_profit:
            logger.info(f"   Take Profit: ${take_profit:,.2f} ({((take_profit-price)/price*100):.2f}%)")
        if signal_details:
            logger.info(f"   ML Signal: {signal_details}")
        
        return position
    
    def close_position(
        self,
        symbol: str,
        price: float,
        timestamp: int,
        reason: str = "MANUAL"
    ) -> Optional[Trade]:
        """
        Đóng vị thế (SELL)
        
        Args:
            symbol: Ký hiệu coin
            price: Giá exit
            timestamp: Unix timestamp (ms)
            reason: Lý do đóng lệnh (MANUAL, STOP_LOSS, TAKE_PROFIT, SIGNAL)
        
        Returns:
            Trade object nếu thành công
        """
        if symbol not in self.positions:
            logger.warning(f"❌ No open position for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Tính giá trị bán
        sell_value = price * position.amount
        commission = sell_value * self.commission_rate
        net_proceeds = sell_value - commission
        
        # Cộng vào số dư
        self.balance += net_proceeds
        self.total_commission_paid += commission
        
        # Tính PnL
        buy_cost = position.entry_price * position.amount  # Không tính commission lần đầu vì đã trừ rồi
        pnl = net_proceeds - buy_cost
        pnl_percentage = (pnl / buy_cost) * 100
        
        # Tạo trade record
        trade = Trade(
            symbol=symbol,
            entry_price=position.entry_price,
            exit_price=price,
            amount=position.amount,
            entry_time=position.entry_timestamp,
            exit_time=timestamp,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            side=position.side
        )
        
        # Cập nhật thống kê
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.trade_history.append(trade)
        
        # Xóa position
        del self.positions[symbol]
        
        # Log chi tiết
        pnl_emoji = "🟢" if pnl > 0 else "🔴"
        logger.info(f"{pnl_emoji} CLOSED POSITION: {symbol} ({reason})")
        logger.info(f"   Entry: ${position.entry_price:,.2f} → Exit: ${price:,.2f}")
        logger.info(f"   Amount: {position.amount:.6f}")
        logger.info(f"   PnL: ${pnl:,.2f} ({pnl_percentage:+.2f}%)")
        logger.info(f"   Commission Paid: ${commission:,.2f}")
        logger.info(f"   New Balance: ${self.balance:,.2f}")
        
        return trade
    
    def check_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float,
        timestamp: int
    ) -> Optional[Trade]:
        """
        Kiểm tra và tự động đóng lệnh nếu chạm Stop Loss hoặc Take Profit
        
        Returns:
            Trade nếu đã đóng lệnh, None nếu không
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Kiểm tra Stop Loss
        if position.stop_loss and current_price <= position.stop_loss:
            logger.warning(f"⚠️ Stop Loss triggered for {symbol}: ${current_price:,.2f} <= ${position.stop_loss:,.2f}")
            return self.close_position(symbol, position.stop_loss, timestamp, "STOP_LOSS")
        
        # Kiểm tra Take Profit
        if position.take_profit and current_price >= position.take_profit:
            logger.info(f"🎯 Take Profit triggered for {symbol}: ${current_price:,.2f} >= ${position.take_profit:,.2f}")
            return self.close_position(symbol, position.take_profit, timestamp, "TAKE_PROFIT")
        
        return None
    
    def get_statistics(self) -> Dict:
        """Lấy thống kê tổng quan"""
        total_pnl = sum(trade.pnl for trade in self.trade_history)
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance,
            'total_pnl': total_pnl,
            'total_pnl_percentage': (total_pnl / self.initial_balance * 100),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_commission_paid': self.total_commission_paid,
            'open_positions': len(self.positions),
            'avg_win': sum(t.pnl for t in self.trade_history if t.pnl > 0) / self.winning_trades if self.winning_trades > 0 else 0,
            'avg_loss': sum(t.pnl for t in self.trade_history if t.pnl < 0) / self.losing_trades if self.losing_trades > 0 else 0
        }
    
    def print_statistics(self):
        """In thống kê ra console"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 VIRTUAL EXCHANGE STATISTICS")
        print("="*60)
        print(f"Initial Balance:       ${stats['initial_balance']:>12,.2f}")
        print(f"Current Balance:       ${stats['current_balance']:>12,.2f}")
        print(f"Total PnL:             ${stats['total_pnl']:>12,.2f} ({stats['total_pnl_percentage']:+.2f}%)")
        print(f"Commission Paid:       ${stats['total_commission_paid']:>12,.2f}")
        print("-" * 60)
        print(f"Total Trades:          {stats['total_trades']:>12}")
        print(f"Winning Trades:        {stats['winning_trades']:>12}")
        print(f"Losing Trades:         {stats['losing_trades']:>12}")
        print(f"Win Rate:              {stats['win_rate']:>12.2f}%")
        print(f"Average Win:           ${stats['avg_win']:>12,.2f}")
        print(f"Average Loss:          ${stats['avg_loss']:>12,.2f}")
        print(f"Open Positions:        {stats['open_positions']:>12}")
        print("="*60 + "\n")
