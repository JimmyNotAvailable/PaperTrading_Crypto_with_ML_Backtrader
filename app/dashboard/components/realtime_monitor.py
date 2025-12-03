"""
Real-time Monitoring Component
Hiển thị live market data, signals, open positions từ Kafka và SQLite
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.dashboard.utils.db_utils import format_currency, format_percentage


def render_open_positions(positions_df: pd.DataFrame):
    """
    Render currently open positions
    
    Args:
        positions_df: DataFrame from positions table
    """
    st.markdown("### 📊 Vị thế đang mở (Open Positions)")
    
    if positions_df.empty:
        st.info("🔓 Hiện không có vị thế nào đang mở")
        return
    
    # Display each position as a card
    for idx, pos in positions_df.iterrows():
        symbol = pos['symbol']
        entry_price = pos['entry_price']
        current_price = pos['current_price']
        amount = pos['amount']
        unrealized_pnl = pos['unrealized_pnl']
        unrealized_pnl_pct = pos['unrealized_pnl_pct']
        
        # Color based on PnL
        if unrealized_pnl > 0:
            color = "🟢"
            bg_color = "#d4edda"  # Light green
        elif unrealized_pnl < 0:
            color = "🔴"
            bg_color = "#f8d7da"  # Light red
        else:
            color = "⚪"
            bg_color = "#e2e3e5"  # Light gray
        
        with st.container():
            st.markdown(f"""
            <div style="
                background-color: {bg_color}; 
                padding: 15px; 
                border-radius: 10px; 
                margin-bottom: 10px;
                border-left: 5px solid {'#28a745' if unrealized_pnl > 0 else '#dc3545' if unrealized_pnl < 0 else '#6c757d'};
            ">
                <h4 style="margin: 0;">{color} {symbol}</h4>
                <p style="margin: 5px 0;">
                    <strong>Giá vào:</strong> ${entry_price:,.2f} | 
                    <strong>Giá hiện tại:</strong> ${current_price:,.2f} | 
                    <strong>Số lượng:</strong> {amount:.6f}
                </p>
                <p style="margin: 5px 0;">
                    <strong>Lãi/Lỗ chưa chốt:</strong> {format_currency(unrealized_pnl)} ({format_percentage(unrealized_pnl_pct)})
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Summary
    total_unrealized = positions_df['unrealized_pnl'].sum()
    st.metric(
        "💰 Tổng lãi/lỗ chưa chốt",
        format_currency(total_unrealized, include_sign=False),
        delta=format_currency(total_unrealized)
    )


def render_recent_signals(trades_df: pd.DataFrame, limit: int = 10):
    """
    Render recent trading signals
    
    Args:
        trades_df: Recent trades DataFrame
        limit: Number of signals to show
    """
    st.markdown("### 🔔 Tín hiệu gần đây")
    
    if trades_df.empty:
        st.info("Chưa có tín hiệu nào")
        return
    
    # Take most recent
    recent = trades_df.head(limit)
    
    # Create styled dataframe
    display_df = recent[[
        'timestamp', 'symbol', 'action', 'price', 
        'ml_confidence', 'pnl', 'status'
    ]].copy()
    
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%d/%m %H:%M')
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.2f}")
    display_df['ml_confidence'] = display_df['ml_confidence'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
    display_df['pnl'] = display_df['pnl'].apply(lambda x: format_currency(x) if pd.notna(x) else "-")
    
    display_df.columns = [
        'Thời gian', 'Cặp tiền', 'Hành động', 'Giá', 
        'Tin cậy', 'PnL', 'Trạng thái'
    ]
    
    # Color coding for action
    def highlight_action(row):
        if row['Hành động'] == 'BUY':
            return ['background-color: #d4edda'] * len(row)
        elif row['Hành động'] == 'SELL':
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)
    
    styled_df = display_df.style.apply(highlight_action, axis=1)
    
    st.dataframe(styled_df, width='stretch', hide_index=True)


def render_equity_curve(equity_df: pd.DataFrame):
    """
    Render equity curve chart
    
    Args:
        equity_df: DataFrame from equity table
    """
    st.markdown("### 📈 Đường cong tài sản (Equity Curve)")
    
    if equity_df.empty:
        st.info("Chưa có dữ liệu equity curve")
        return
    
    fig = go.Figure()
    
    # Total value line
    fig.add_trace(go.Scatter(
        x=equity_df['timestamp'],
        y=equity_df['total_value'],
        mode='lines',
        name='Tổng tài sản',
        line=dict(color='rgb(59, 130, 246)', width=2),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))
    
    # Cash line
    fig.add_trace(go.Scatter(
        x=equity_df['timestamp'],
        y=equity_df['cash'],
        mode='lines',
        name='Tiền mặt',
        line=dict(color='rgb(34, 197, 94)', width=1, dash='dash')
    ))
    
    # Positions value line
    fig.add_trace(go.Scatter(
        x=equity_df['timestamp'],
        y=equity_df['positions_value'],
        mode='lines',
        name='Giá trị vị thế',
        line=dict(color='rgb(234, 179, 8)', width=1, dash='dot')
    ))
    
    fig.update_layout(
        height=400,
        hovermode='x unified',
        xaxis_title="Thời gian",
        yaxis_title="Giá trị ($)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Stats
    if len(equity_df) > 1:
        initial_value = equity_df.iloc[0]['total_value']
        current_value = equity_df.iloc[-1]['total_value']
        total_return = current_value - initial_value
        total_return_pct = (total_return / initial_value) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💼 Giá trị ban đầu", f"${initial_value:,.2f}")
        with col2:
            st.metric("💼 Giá trị hiện tại", f"${current_value:,.2f}")
        with col3:
            st.metric(
                "📊 Lợi nhuận tổng",
                format_currency(total_return, include_sign=False),
                delta=f"{format_percentage(total_return_pct)}"
            )


def render_realtime_monitor(positions_df: pd.DataFrame, trades_df: pd.DataFrame, equity_df: pd.DataFrame):
    """
    Main function to render real-time monitoring
    
    Args:
        positions_df: Open positions
        trades_df: Recent trades
        equity_df: Equity curve data
    """
    st.markdown("## 🔴 Giám Sát Thời Gian Thực")
    
    # Open positions
    render_open_positions(positions_df)
    
    st.divider()
    
    # Recent signals
    render_recent_signals(trades_df)
    
    st.divider()
    
    # Equity curve
    render_equity_curve(equity_df)
