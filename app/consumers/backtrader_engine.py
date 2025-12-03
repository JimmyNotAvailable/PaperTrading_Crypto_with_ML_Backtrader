"""
Backtrader Engine with Kafka Integration - Phase 5
Real-time trading engine using Backtrader framework
"""

import backtrader as bt
import json
import os
import sys
import time
from datetime import datetime
from confluent_kafka import Consumer
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.mongo_db import MongoDB

load_dotenv()

# Kafka Configuration
KAFKA_CONF = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    'group.id': 'backtrader_group',
    'auto.offset.reset': 'latest'
}


class MLStrategy(bt.Strategy):
    """
    Backtrader Strategy integrating ML signals from Kafka
    
    This strategy:
    1. Listens to Kafka topics for ML signals and commands
    2. Executes trades based on AI predictions with confidence threshold
    3. Handles panic button commands to close all positions
    4. Logs all trades to MongoDB for dashboard display
    """
    
    params = (
        ('mongo_db', None),
        ('min_confidence', 0.75),
        ('risk_per_trade', 0.5),  # 50% of cash
    )

    def __init__(self):
        # Kafka Consumers
        self.signal_consumer = Consumer(KAFKA_CONF)
        self.signal_consumer.subscribe(['crypto.ml_signals', 'crypto.commands'])
        
        self.db = self.p.mongo_db
        self.username = "admin"  # Default user
        self.order = None
        self.current_symbol = "BTCUSDT"
        
        self.log("🚀 MLStrategy initialized")

    def log(self, txt, dt=None):
        """Log with timestamp"""
        dt = dt or datetime.now()
        print(f'[{dt.strftime("%H:%M:%S")}] {txt}')

    def notify_order(self, order):
        """Handle order status changes"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'🟢 MUA KHỚP LỆNH: ${order.executed.price:.2f} | Size: {order.executed.size:.4f}')
                
                # Save to MongoDB
                self.db.insert_trade({
                    "username": self.username,
                    "symbol": self.current_symbol,
                    "action": "BUY",
                    "entry_price": order.executed.price,
                    "amount": order.executed.size,
                    "fee": order.executed.comm,
                    "status": "OPEN",
                    "timestamp": time.time(),
                    "reason": "ML_Signal"
                })
                
            elif order.issell():
                self.log(f'🔴 BÁN KHỚP LỆNH: ${order.executed.price:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('⚠️  Lệnh bị hủy/từ chối')

        self.order = None

    def notify_trade(self, trade):
        """Handle completed trade cycle (BUY -> SELL)"""
        if not trade.isclosed:
            return

        self.log(f'💰 CHỐT LỜI/LỖ: Gross ${trade.pnl:.2f}, Net ${trade.pnlcomm:.2f}')
        
        # Update MongoDB: Close the oldest open trade
        last_open = self.db.get_open_trade(self.username, self.current_symbol)
        
        if last_open:
            self.db.close_trade(
                str(last_open['_id']),
                exit_price=trade.price,
                pnl=trade.pnlcomm
            )
            
            # Update user balance
            self.db.update_balance(self.username, trade.pnlcomm)

    def next(self):
        """
        Called for each new data point
        Polls Kafka for signals and executes trades
        """
        # Poll Kafka (non-blocking)
        msg = self.signal_consumer.poll(0.1)
        
        if msg is None:
            return
        if msg.error():
            return

        try:
            data = json.loads(msg.value().decode('utf-8'))
            topic = msg.topic()

            # Get current price
            current_price = data.get('price', self.data.close[0])

            # --- PANIC BUTTON ---
            if topic == 'crypto.commands' and data.get('action') == 'STOP_BOT':
                self.log("🚨 NHẬN LỆNH PANIC! BÁN TOÀN BỘ.")
                if self.position:
                    self.close()
                return

            # --- ML SIGNAL PROCESSING ---
            if topic == 'crypto.ml_signals':
                signal = data.get('signal')
                confidence = data.get('details', {}).get('confidence', 0)
                symbol = data.get('symbol', 'BTCUSDT')
                
                self.current_symbol = symbol

                # Entry Logic
                if not self.position:
                    if signal == 'BUY' and confidence >= self.p.min_confidence:
                        cash = self.broker.get_cash()
                        size = (cash * self.p.risk_per_trade) / current_price
                        
                        self.log(f"🤖 AI MUA: ${current_price:.2f} (Conf: {confidence:.2%})")
                        self.buy(size=size)
                
                # Exit Logic
                else:
                    if signal == 'SELL':
                        self.log(f"🤖 AI BÁN: ${current_price:.2f}")
                        self.close()

        except Exception as e:
            self.log(f"❌ Error processing signal: {e}")


class BacktraderWrapper:
    """
    Simplified Backtrader wrapper for real-time Kafka integration
    
    This wrapper:
    - Avoids complex LiveDataFeed setup
    - Uses manual position tracking with Backtrader's commission calculations
    - Integrates seamlessly with existing Kafka infrastructure
    """
    
    def __init__(self):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(5000.0)
        self.cerebro.broker.setcommission(commission=0.001)  # 0.1%
        
        self.db = MongoDB()
        
        # Kafka setup
        self.consumer = Consumer(KAFKA_CONF)
        self.consumer.subscribe(['crypto.ml_signals', 'crypto.commands'])
        
        # Internal state
        self.position_size = 0
        self.entry_price = 0
        self.username = "admin"
        self.current_symbol = "BTCUSDT"
        
        print("=" * 60)
        print("🚀 BACKTRADER WRAPPER STARTED (HYBRID MODE)")
        print("=" * 60)
        print(f"💵 Initial Balance: ${self.cerebro.broker.get_cash():,.2f}")
        print(f"📊 Commission: {0.1}%")
        print(f"🎯 Min Confidence: 75%")
        print(f"📈 Risk per Trade: 50% of cash")
        print("=" * 60)

    def run(self):
        """Main event loop"""
        print("\n⏳ Waiting for Kafka signals...")
        print("   Topics: crypto.ml_signals, crypto.commands\n")
        
        while True:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    continue

                data = json.loads(msg.value().decode('utf-8'))
                topic = msg.topic()
                
                current_price = data.get('price', 0)
                if current_price == 0:
                    continue

                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Get current portfolio value
                value = self.cerebro.broker.get_value()
                cash = self.cerebro.broker.get_cash()
                
                # --- PANIC COMMAND ---
                if topic == 'crypto.commands' and data.get('action') == 'STOP_BOT':
                    if self.position_size > 0:
                        print(f"\n[{timestamp}] 🚨 PANIC BUTTON PRESSED!")
                        self._sell(current_price, reason="PANIC")
                    else:
                        print(f"\n[{timestamp}] ⚠️  Panic received but no position to close")
                    continue

                # --- ML SIGNAL ---
                if topic == 'crypto.ml_signals':
                    signal = data.get('signal')
                    confidence = data.get('details', {}).get('confidence', 0)
                    symbol = data.get('symbol', 'BTCUSDT')
                    
                    self.current_symbol = symbol
                    
                    print(f"[{timestamp}] 📡 Signal: {signal} | {symbol} | Conf: {confidence:.2%} | Price: ${current_price:,.2f}")
                    
                    # BUY Signal
                    if signal == 'BUY' and self.position_size == 0 and confidence >= 0.75:
                        target_value = cash * 0.5  # 50% of cash
                        size = target_value / current_price
                        self._buy(current_price, size, confidence)
                    
                    # SELL Signal
                    elif signal == 'SELL' and self.position_size > 0:
                        self._sell(current_price, reason="ML_Signal")
                    
                    elif signal == 'HOLD':
                        print(f"         ⏸️  HOLD - No action")
            
            except KeyboardInterrupt:
                print("\n\n🛑 Shutting down Backtrader Engine...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        self.shutdown()

    def _buy(self, price: float, size: float, confidence: float):
        """Execute BUY order"""
        cost = price * size
        comm = cost * 0.001  # 0.1% commission
        total_cost = cost + comm
        
        # Update position
        self.position_size = size
        self.entry_price = price
        
        # Deduct from cash (simulated broker)
        # In real Backtrader, this is automatic
        
        # Save to MongoDB
        trade_id = self.db.insert_trade({
            "username": self.username,
            "symbol": self.current_symbol,
            "action": "BUY",
            "entry_price": price,
            "amount": size,
            "fee": comm,
            "status": "OPEN",
            "timestamp": time.time(),
            "ml_confidence": confidence,
            "reason": "ML_Signal"
        })
        
        # Deduct balance
        self.db.update_balance(self.username, -total_cost)
        
        print(f"         ✅ BUY EXECUTED: {size:.4f} {self.current_symbol} @ ${price:,.2f}")
        print(f"         💵 Cost: ${cost:,.2f} + Fee: ${comm:,.2f} = ${total_cost:,.2f}")
        print(f"         💰 Remaining Cash: ${self.db.get_balance(self.username):,.2f}")

    def _sell(self, price: float, reason: str = "ML_Signal"):
        """Execute SELL order"""
        if self.position_size == 0:
            return
        
        revenue = price * self.position_size
        comm = revenue * 0.001
        net_revenue = revenue - comm
        
        # Calculate PnL
        entry_cost = self.entry_price * self.position_size
        pnl = net_revenue - entry_cost
        
        # Get open trade
        open_trade = self.db.get_open_trade(self.username, self.current_symbol)
        
        if open_trade:
            # Close trade in DB
            self.db.close_trade(
                str(open_trade['_id']),
                exit_price=price,
                pnl=pnl
            )
            
            # Add revenue back to balance
            self.db.update_balance(self.username, net_revenue)
        
        print(f"         ✅ SELL EXECUTED: {self.position_size:.4f} {self.current_symbol} @ ${price:,.2f}")
        print(f"         💵 Revenue: ${revenue:,.2f} - Fee: ${comm:,.2f} = ${net_revenue:,.2f}")
        print(f"         {'💰 PROFIT' if pnl > 0 else '📉 LOSS'}: ${pnl:,.2f}")
        print(f"         💰 New Balance: ${self.db.get_balance(self.username):,.2f}")
        
        # Reset position
        self.position_size = 0
        self.entry_price = 0

    def shutdown(self):
        """Cleanup on shutdown"""
        # Close any open positions
        if self.position_size > 0:
            print("\n⚠️  Closing open position before shutdown...")
            # Get last known price from DB
            last_price = self.db.get_latest_price(self.current_symbol)
            if last_price:
                self._sell(last_price, reason="SHUTDOWN")
        
        self.db.close()
        self.consumer.close()
        print("✅ Backtrader Engine shutdown complete")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        BACKTRADER ENGINE - PHASE 5                       ║
║        Real-time ML Trading with Kafka                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Initialize MongoDB and create admin user if needed
    from app.services.mongo_db import init_default_user
    init_default_user()
    
    # Start engine
    engine = BacktraderWrapper()
    engine.run()
