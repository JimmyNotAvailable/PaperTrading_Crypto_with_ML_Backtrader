"""
Backtrader Performance Monitor Dashboard - Phase 5
Real-time monitoring of Backtrader Engine with MongoDB backend
"""

import streamlit as st
import pandas as pd
import time
import json
import os
import sys
from pathlib import Path
from confluent_kafka import Producer
from dotenv import load_dotenv
import plotly.graph_objects as go
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.mongo_db import MongoDB

load_dotenv()

# ==========================
# CONFIGURATION
# ==========================

st.set_page_config(
    page_title="Backtrader Live Monitor",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Kafka Producer for panic button
producer = Producer({
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
})

# ==========================
# HELPER FUNCTIONS
# ==========================

def send_panic_command(price: float = 0):
    """Send panic stop command to Backtrader Engine"""
    msg = {
        'action': 'STOP_BOT',
        'current_price': price,
        'timestamp': time.time(),
        'source': 'dashboard'
    }
    producer.produce('crypto.commands', json.dumps(msg).encode('utf-8'))
    producer.flush()
    return True


def format_currency(value: float) -> str:
    """Format currency with color"""
    if value > 0:
        return f"<span style='color: green'>+${value:,.2f}</span>"
    elif value < 0:
        return f"<span style='color: red'>-${abs(value):,.2f}</span>"
    else:
        return f"${value:,.2f}"


def get_pnl_color(pnl: float) -> str:
    """Get color for PnL"""
    return "green" if pnl > 0 else "red" if pnl < 0 else "gray"


# ==========================
# LOGIN SYSTEM
# ==========================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1>🔐 Backtrader Dashboard Login</h1>
        <p style='color: gray;'>Phase 5: Real-time Trading Monitor</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="admin")
            password = st.text_input("🔑 Password", type="password", placeholder="admin123")
            submit = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit:
                db = MongoDB()
                if db.verify_password(username, password):
                    user = db.get_user(username)
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    db.close()
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
                    db.close()
        
        st.info("💡 Default: admin / admin123")
    
    st.stop()

# ==========================
# MAIN DASHBOARD
# ==========================

# Initialize MongoDB
db = MongoDB()

# Get fresh user data (with type guard)
if st.session_state.user is None:
    st.error("❌ Session expired! Please login again.")
    st.session_state.logged_in = False
    st.rerun()

user = db.get_user(st.session_state.user['username'])
if not user:
    st.error("❌ User not found! Please login again.")
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

# ==========================
# SIDEBAR
# ==========================

with st.sidebar:
    st.markdown(f"""
    <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 10px; margin-bottom: 1rem;'>
        <h2 style='color: white; margin: 0;'>👤 {user['username']}</h2>
        <p style='color: #e0e0e0; margin: 0; font-size: 0.9rem;'>Account Balance</p>
        <h1 style='color: white; margin: 0;'>${user['current_balance']:,.2f}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("⚙️ Controls")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto Refresh (3s)", value=True)
    
    st.divider()
    
    # Panic Button
    st.markdown("### 🚨 Emergency Controls")
    st.warning("⚠️ This will close ALL open positions immediately!")
    
    if st.button("🛑 PANIC BUTTON", type="primary", use_container_width=True):
        if send_panic_command():
            st.error("🚨 PANIC COMMAND SENT TO ENGINE!")
            time.sleep(2)
            st.rerun()
    
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

# ==========================
# HEADER
# ==========================

st.markdown("""
<div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); 
            border-radius: 10px; margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0;'>📈 Backtrader Performance Monitor</h1>
    <p style='color: #e0e0e0; margin: 0;'>Real-time Trading Engine Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ==========================
# METRICS
# ==========================

# Get trading stats
stats = db.get_trading_stats(user['username'])
trades_df = pd.DataFrame(db.get_trades_history(user['username'], limit=100))

# Calculate unrealized PnL
unrealized_pnl = 0
open_trade = db.get_open_trade(user['username'])
if open_trade:
    # Get latest price
    latest_price = db.get_latest_price(open_trade['symbol'])
    if latest_price:
        unrealized_pnl = (latest_price - open_trade['entry_price']) * open_trade['amount']
    else:
        # Fallback to a default if no price data
        unrealized_pnl = 0

# Display metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Realized PnL",
        value=f"${stats['total_pnl']:,.2f}",
        delta=f"{stats['total_pnl']:+,.2f}" if stats['total_pnl'] != 0 else None
    )

with col2:
    st.metric(
        label="📊 Unrealized PnL",
        value=f"${unrealized_pnl:,.2f}",
        delta=f"{unrealized_pnl:+,.2f}" if unrealized_pnl != 0 else None
    )

with col3:
    st.metric(
        label="🎯 Win Rate",
        value=f"{stats['win_rate']:.1f}%",
        delta=f"{stats['winning_trades']}W / {stats['losing_trades']}L"
    )

with col4:
    st.metric(
        label="📈 Total Trades",
        value=stats['total_trades']
    )

st.divider()

# ==========================
# POSITION & HISTORY
# ==========================

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("🎯 Active Position")
    
    if open_trade:
        st.success(f"**Symbol:** {open_trade['symbol']}")
        st.info(f"**Amount:** {open_trade['amount']:.4f}")
        st.info(f"**Entry Price:** ${open_trade['entry_price']:,.2f}")
        st.info(f"**ML Confidence:** {open_trade.get('ml_confidence', 0):.2%}")
        
        # Calculate current value
        if latest_price:
            current_value = open_trade['amount'] * latest_price
            entry_value = open_trade['amount'] * open_trade['entry_price']
            
            st.metric(
                label="Current Value",
                value=f"${current_value:,.2f}",
                delta=f"${unrealized_pnl:+,.2f}"
            )
        
        # Time held
        time_held = time.time() - open_trade['timestamp']
        hours = int(time_held // 3600)
        minutes = int((time_held % 3600) // 60)
        st.caption(f"⏱️ Held for: {hours}h {minutes}m")
    else:
        st.info("💵 No open positions\n\nWaiting for ML signals...")

with col_right:
    st.subheader("📜 Recent Trades History")
    
    if not trades_df.empty:
        # Format dataframe for display
        display_df = trades_df.copy()
        
        # Convert timestamp to readable format
        display_df['time'] = pd.to_datetime(display_df['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Select and rename columns
        cols_to_show = {
            'time': 'Time',
            'symbol': 'Symbol',
            'action': 'Action',
            'entry_price': 'Entry $',
            'amount': 'Amount',
            'status': 'Status'
        }
        
        # Add PnL if exists
        if 'pnl' in display_df.columns:
            cols_to_show['pnl'] = 'PnL $'
        
        # Filter and rename
        display_df = display_df[[col for col in cols_to_show.keys() if col in display_df.columns]]
        display_df = display_df.rename(columns=cols_to_show)
        
        # Style based on status and PnL
        def highlight_row(row):
            if row.get('Status') == 'OPEN':
                return ['background-color: #ffeaa7'] * len(row)
            elif row.get('Status') == 'CLOSED':
                if 'PnL $' in row:
                    if row['PnL $'] > 0:
                        return ['background-color: #55efc4'] * len(row)
                    elif row['PnL $'] < 0:
                        return ['background-color: #ff7675'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            display_df.head(20),
            hide_index=True,
            width='stretch'
        )
    else:
        st.info("No trades yet. Waiting for signals...")

# ==========================
# EQUITY CURVE
# ==========================

if stats['total_trades'] > 0:
    st.divider()
    st.subheader("📈 Equity Curve")
    
    # Calculate cumulative PnL
    closed_trades = db.get_closed_trades(user['username'])
    
    if closed_trades:
        equity_data = []
        cumulative_pnl = user['initial_balance']
        
        for trade in reversed(closed_trades):  # Oldest first
            cumulative_pnl += trade.get('pnl', 0)
            equity_data.append({
                'timestamp': trade.get('closed_at', trade['timestamp']),
                'equity': cumulative_pnl
            })
        
        equity_df = pd.DataFrame(equity_data)
        equity_df['datetime'] = pd.to_datetime(equity_df['timestamp'], unit='s')
        
        # Create Plotly chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_df['datetime'],
            y=equity_df['equity'],
            mode='lines+markers',
            name='Equity',
            line=dict(color='#6c5ce7', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(108, 92, 231, 0.1)'
        ))
        
        # Add initial balance line
        fig.add_hline(
            y=user['initial_balance'],
            line_dash="dash",
            line_color="gray",
            annotation_text="Initial Balance",
            annotation_position="right"
        )
        
        fig.update_layout(
            height=400,
            hovermode='x unified',
            xaxis_title="Time",
            yaxis_title="Equity ($)",
            showlegend=False,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, width='stretch')

# ==========================
# STATISTICS
# ==========================

if stats['total_trades'] > 0:
    st.divider()
    st.subheader("📊 Trading Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Win", f"${stats['avg_win']:,.2f}")
        st.metric("Winning Trades", stats['winning_trades'])
    
    with col2:
        st.metric("Average Loss", f"${stats['avg_loss']:,.2f}")
        st.metric("Losing Trades", stats['losing_trades'])
    
    with col3:
        profit_factor = stats['profit_factor']
        st.metric("Profit Factor", f"{profit_factor:.2f}")
        
        if profit_factor > 2:
            st.success("✅ Excellent")
        elif profit_factor > 1.5:
            st.info("👍 Good")
        elif profit_factor > 1:
            st.warning("⚠️ Profitable")
        else:
            st.error("❌ Losing")

# ==========================
# AUTO REFRESH
# ==========================

if auto_refresh:
    time.sleep(3)
    st.rerun()

# ==========================
# CLEANUP
# ==========================

db.close()
