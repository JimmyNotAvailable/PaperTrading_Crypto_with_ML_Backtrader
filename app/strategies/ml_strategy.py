r"""
Backtrader Strategy với ML Signals
Chiến lược giao dịch tích hợp tín hiệu từ Machine Learning
Theo thiết kế từ ToturialUpgrade.md - Phase 4

⚠️ NOTE: File này là REFERENCE IMPLEMENTATION - không được sử dụng trong Decision Engine hiện tại.
Decision Engine đang dùng Virtual Exchange (app/services/virtual_exchange.py) thay vì Backtrader.
File này có sẵn cho future backtesting needs.

Để chạy file này, cần:
1. Virtual environment activated: .\crypto-venv\Scripts\Activate.ps1
2. Backtrader installed: pip install backtrader (đã cài đặt version 1.9.78.123)

Type checking: File này có type errors trong IDE vì backtrader không có type stubs.
Điều này KHÔNG ảnh hưởng runtime - code chạy tốt khi có virtual env.
"""
try:
    import backtrader as bt  # type: ignore
except ImportError:
    # Backtrader optional - file này không được import trong production
    bt = None  # type: ignore
    
import logging
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)


# Guard: Chỉ định nghĩa classes nếu backtrader available
if bt is None:
    raise ImportError(
        "Backtrader not available. This is a reference implementation.\n"
        "Decision Engine uses Virtual Exchange instead (app/services/virtual_exchange.py).\n"
        "To use this file for backtesting, install: pip install backtrader"
    )


class MLSignalStrategy(bt.Strategy):
    """
    Chiến lược giao dịch dựa trên ML Signals
    
    Quy trình Decision (từ ToturialUpgrade.md):
    1. Signal: Model Random Forest dự đoán "Tăng"
    2. Strategy:
       - Kiểm tra ví tiền (Balance)
       - Kiểm tra rủi ro (Risk Management): Stop Loss 2%, Take Profit 5%
       - Kiểm tra chỉ báo phụ (RSI < 70) để tránh mua đỉnh
    3. Action: Gửi lệnh mua
    """
    
    params = (
        ('stop_loss_pct', 0.02),      # 2% Stop Loss
        ('take_profit_pct', 0.05),    # 5% Take Profit
        ('rsi_overbought', 70),       # RSI > 70 = overbought (không mua)
        ('rsi_oversold', 30),         # RSI < 30 = oversold (không bán)
        ('min_confidence', 0.60),     # Confidence tối thiểu để trade
        ('position_size_pct', 0.95),  # Sử dụng 95% số dư cho mỗi lệnh
        ('printlog', True),
    )
    
    def __init__(self):
        """Khởi tạo strategy"""
        # Lưu reference đến data
        self.dataclose = self.datas[0].close  # type: ignore
        
        # Thêm RSI indicator
        self.rsi = bt.indicators.RSI(self.datas[0], period=14)  # type: ignore
        
        # Track orders và positions
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # ML Signal từ bên ngoài (sẽ được set qua set_signal())
        self.current_ml_signal = None
        self.current_ml_confidence = 0.0
        self.current_ml_details = {}
        
        logger.info("🧠 MLSignalStrategy initialized")
        logger.info(f"   Stop Loss: {self.params.stop_loss_pct*100}%")  # type: ignore
        logger.info(f"   Take Profit: {self.params.take_profit_pct*100}%")  # type: ignore
        logger.info(f"   Min Confidence: {self.params.min_confidence*100}%")  # type: ignore
        logger.info(f"   RSI Thresholds: {self.params.rsi_oversold} / {self.params.rsi_overbought}")  # type: ignore
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:  # type: ignore
            dt = dt or self.datas[0].datetime.date(0)  # type: ignore
            print(f'{dt.isoformat()} {txt}')
    
    def notify_order(self, order):
        """Nhận thông báo về trạng thái order"""
        if order.status in [order.Submitted, order.Accepted]:
            # Order đã được gửi/chấp nhận
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}'
                )
            
            self.bar_executed = len(self)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        # Reset order
        self.order = None
    
    def notify_trade(self, trade):
        """Nhận thông báo khi trade hoàn tất"""
        if not trade.isclosed:
            return
        
        self.log(f'OPERATION PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')
    
    def set_signal(self, signal: str, confidence: float, details: Optional[Dict[str, Any]] = None):
        """
        Set ML signal từ bên ngoài
        
        Args:
            signal: 'BUY', 'SELL', hoặc 'NEUTRAL'
            confidence: Độ tin cậy (0.0 - 1.0)
            details: Chi tiết từ ML models (optional)
        """
        self.current_ml_signal = signal
        self.current_ml_confidence = confidence
        self.current_ml_details = details or {}
        
        logger.debug(f"📡 ML Signal received: {signal} (confidence: {confidence:.2%})")
    
    def can_buy(self) -> Tuple[bool, str]:  # type: ignore
        """
        Kiểm tra các điều kiện để mua
        
        Returns:
            (can_buy, reason)
        """
        # 1. Kiểm tra đã có position chưa
        if self.position:
            return False, "Already have open position"
        
        # 2. Kiểm tra có order đang pending không
        if self.order:
            return False, "Order pending"
        
        # 3. Kiểm tra ML signal
        if self.current_ml_signal != 'BUY':
            return False, f"ML signal is {self.current_ml_signal}"
        
        # 4. Kiểm tra confidence
        if self.current_ml_confidence < self.params.min_confidence:  # type: ignore
            return False, f"Confidence {self.current_ml_confidence:.2%} < {self.params.min_confidence:.2%}"  # type: ignore
        
        # 5. Kiểm tra RSI (tránh mua đỉnh)
        current_rsi = self.rsi[0]  # type: ignore
        if current_rsi > self.params.rsi_overbought:  # type: ignore
            return False, f"RSI {current_rsi:.1f} > {self.params.rsi_overbought} (overbought)"  # type: ignore
        
        return True, "OK"
    
    def can_sell(self) -> Tuple[bool, str]:  # type: ignore
        """
        Kiểm tra các điều kiện để bán
        
        Returns:
            (can_sell, reason)
        """
        # 1. Kiểm tra có position không
        if not self.position:
            return False, "No open position"
        
        # 2. Kiểm tra có order đang pending không
        if self.order:
            return False, "Order pending"
        
        # 3. Kiểm tra ML signal SELL
        if self.current_ml_signal == 'SELL':
            return True, "ML signal SELL"
        
        # 4. Kiểm tra Stop Loss
        current_price = self.dataclose[0]  # type: ignore
        loss_pct = (current_price - self.buyprice) / self.buyprice  # type: ignore
        if loss_pct <= -self.params.stop_loss_pct:  # type: ignore
            return True, f"Stop Loss triggered: {loss_pct:.2%}"
        
        # 5. Kiểm tra Take Profit
        if loss_pct >= self.params.take_profit_pct:  # type: ignore
            return True, f"Take Profit triggered: {loss_pct:.2%}"
        
        # 6. Kiểm tra RSI (quá bán)
        current_rsi = self.rsi[0]  # type: ignore
        if current_rsi < self.params.rsi_oversold:  # type: ignore
            return True, f"RSI {current_rsi:.1f} < {self.params.rsi_oversold} (oversold)"  # type: ignore
        
        return False, "Hold position"
    
    def next(self):
        """
        Logic chính - được gọi mỗi khi có candle mới
        """
        # Log current state
        current_price = self.dataclose[0]  # type: ignore
        current_rsi = self.rsi[0]  # type: ignore
        
        self.log(f'Close: {current_price:.2f}, RSI: {current_rsi:.1f}')
        
        # Kiểm tra điều kiện BUY
        can_buy, buy_reason = self.can_buy()
        if can_buy:
            # Tính position size (95% của cash)
            cash = self.broker.getcash()  # type: ignore
            position_value = cash * self.params.position_size_pct  # type: ignore
            size = position_value / current_price
            
            # Đặt lệnh mua
            self.log(f'🟢 BUY SIGNAL: {buy_reason}')
            self.log(f'   ML Details: {self.current_ml_details}')
            self.log(f'   Size: {size:.6f}, Value: ${position_value:.2f}')
            
            self.order = self.buy(size=size)  # type: ignore
        
        # Kiểm tra điều kiện SELL
        can_sell, sell_reason = self.can_sell()
        if can_sell:
            # Đặt lệnh bán
            self.log(f'🔴 SELL SIGNAL: {sell_reason}')
            
            # Tính PnL trước khi bán
            if self.buyprice:
                pnl_pct = (current_price - self.buyprice) / self.buyprice
                self.log(f'   Entry: ${self.buyprice:.2f} → Current: ${current_price:.2f} ({pnl_pct:+.2%})')
            
            self.order = self.sell()  # type: ignore
    
    def stop(self):  # type: ignore
        """Được gọi khi strategy kết thúc"""
        final_value = self.broker.getvalue()  # type: ignore
        pnl = final_value - self.broker.startingcash  # type: ignore
        pnl_pct = (pnl / self.broker.startingcash) * 100
        
        self.log('='*60)
        self.log(f'📊 Strategy Ending Value: ${final_value:.2f}')
        self.log(f'📊 Total PnL: ${pnl:.2f} ({pnl_pct:+.2f}%)')
        self.log('='*60)


class MLDataFeed(bt.DataBase):  # type: ignore
    """
    Custom Data Feed cho Backtrader
    Nhận dữ liệu từ Kafka thay vì file CSV
    """
    
    params = (
        ('fromdate', None),
        ('todate', None),
        ('timeframe', bt.TimeFrame.Minutes),
        ('compression', 1),
    )
    
    def __init__(self):
        super(MLDataFeed, self).__init__()
        
        # Buffer để lưu dữ liệu
        self.data_buffer = []
        self.current_index = 0
    
    def add_data(self, timestamp, open_price, high, low, close, volume):
        """
        Thêm dữ liệu mới vào buffer
        
        Args:
            timestamp: Unix timestamp (ms)
            open_price, high, low, close: OHLC prices
            volume: Trading volume
        """
        self.data_buffer.append({
            'datetime': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'openinterest': 0
        })
    
    def _load(self):
        """Load next data point"""
        if self.current_index >= len(self.data_buffer):
            return False
        
        data = self.data_buffer[self.current_index]
        
        # Set datetime
        self.lines.datetime[0] = bt.date2num(data['datetime'])  # type: ignore
        
        # Set OHLCV
        self.lines.open[0] = data['open']
        self.lines.high[0] = data['high']
        self.lines.low[0] = data['low']
        self.lines.close[0] = data['close']
        self.lines.volume[0] = data['volume']
        self.lines.openinterest[0] = data['openinterest']
        
        self.current_index += 1
        return True
