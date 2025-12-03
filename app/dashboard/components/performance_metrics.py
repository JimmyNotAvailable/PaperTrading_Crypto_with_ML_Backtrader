"""
Performance Metrics Component
Hiển thị Realized/Unrealized PnL, Trading Calendar Heatmap, Net PnL
Theo PHASE5_DASHBOARD_GUIDE.md
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.dashboard.utils.db_utils import format_currency, format_percentage, get_color_for_pnl


def render_pnl_breakdown(stats: Dict[str, Any]):
    """
    Render PnL Breakdown: Realized vs Unrealized vs Net
    
    Args:
        stats: Dictionary with realized_pnl, unrealized_pnl, total_fees, net_pnl
    """
    st.subheader("💰 Phân Tích Lãi/Lỗ (PnL Breakdown)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Realized PnL
    realized = stats.get('realized_pnl', 0)
    with col1:
        st.metric(
            "💎 Lãi đã chốt (Realized)",
            format_currency(realized, include_sign=False),
            delta=format_currency(realized),
            delta_color="normal"
        )
    
    # Unrealized PnL
    unrealized = stats.get('unrealized_pnl', 0)
    with col2:
        st.metric(
            "⏳ Lãi dự kiến (Unrealized)",
            format_currency(unrealized, include_sign=False),
            delta=format_currency(unrealized),
            delta_color="normal"
        )
    
    # Total Fees
    fees = stats.get('total_fees', 0)
    with col3:
        st.metric(
            "💸 Tổng phí sàn",
            format_currency(fees, include_sign=False),
            delta=f"-${fees:,.2f}",
            delta_color="inverse"
        )
    
    # Net PnL
    net = stats.get('net_pnl', 0)
    with col4:
        st.metric(
            "🎯 Lãi ròng (Net PnL)",
            format_currency(net, include_sign=False),
            delta=format_currency(net),
            delta_color="normal"
        )
    
    # Waterfall Chart
    st.markdown("##### 📊 Biểu đồ thác nước (Waterfall Chart)")
    
    initial_cash = stats.get('cash', 10000)
    
    fig = go.Figure(go.Waterfall(
        name="PnL Flow",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Vốn ban đầu", "Lãi đã chốt", "Lãi dự kiến", "Phí giao dịch", "Tổng hiện tại"],
        textposition="outside",
        text=[
            f"${initial_cash:,.0f}",
            format_currency(realized),
            format_currency(unrealized),
            f"-${fees:,.2f}",
            format_currency(initial_cash + net)
        ],
        y=[initial_cash, realized, unrealized, -fees, initial_cash + net],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        height=400,
        showlegend=False,
        yaxis_title="USD ($)",
        font=dict(size=12)
    )
    
    st.plotly_chart(fig, width='stretch')


def render_trading_calendar(trades_df: pd.DataFrame):
    """
    Render Trading Calendar Heatmap
    Hiển thị lịch sử Lãi/Lỗ theo ngày (giống GitHub Contributions)
    
    Args:
        trades_df: DataFrame with columns [timestamp, pnl]
    """
    st.markdown("##### 📅 Lịch sử Lãi/Lỗ theo ngày")
    
    if trades_df.empty:
        st.info("Chưa có dữ liệu giao dịch")
        return
    
    # Group by date
    trades_df['date'] = pd.to_datetime(trades_df['timestamp']).dt.date
    daily_pnl = trades_df.groupby('date')['pnl'].sum().reset_index()
    daily_pnl['date'] = pd.to_datetime(daily_pnl['date'])
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=daily_pnl['pnl'],
        x=daily_pnl['date'],
        y=['PnL'] * len(daily_pnl),
        colorscale=[
            [0, 'rgb(220, 38, 38)'],      # Đỏ đậm (lỗ lớn)
            [0.45, 'rgb(248, 113, 113)'],  # Đỏ nhạt
            [0.5, 'rgb(229, 231, 235)'],   # Xám (hòa vốn)
            [0.55, 'rgb(134, 239, 172)'],  # Xanh nhạt
            [1, 'rgb(22, 163, 74)']        # Xanh đậm (lãi lớn)
        ],
        zmid=0,  # Center at 0
        hovertemplate='<b>Ngày</b>: %{x}<br><b>PnL</b>: $%{z:,.2f}<extra></extra>',
        colorbar=dict(title="PnL ($)")
    ))
    
    fig.update_layout(
        height=150,
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis_visible=False,
        xaxis=dict(title="")
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        best_day = daily_pnl.loc[daily_pnl['pnl'].idxmax()] if not daily_pnl.empty else None
        if best_day is not None:
            st.success(f"🏆 Ngày lãi cao nhất: {best_day['date'].strftime('%d/%m/%Y')} ({format_currency(best_day['pnl'])})")
    
    with col2:
        worst_day = daily_pnl.loc[daily_pnl['pnl'].idxmin()] if not daily_pnl.empty else None
        if worst_day is not None:
            st.error(f"📉 Ngày lỗ cao nhất: {worst_day['date'].strftime('%d/%m/%Y')} ({format_currency(worst_day['pnl'])})")
    
    with col3:
        avg_daily = daily_pnl['pnl'].mean() if not daily_pnl.empty else 0
        st.info(f"📊 PnL trung bình/ngày: {format_currency(avg_daily)}")


def render_performance_metrics(stats: Dict[str, Any], trades_df: pd.DataFrame):
    """
    Main function to render all performance metrics
    
    Args:
        stats: Summary statistics from database
        trades_df: All trades DataFrame
    """
    st.markdown("## 📊 Phân Tích Hiệu Suất Chuyên Sâu")
    
    # PnL Breakdown
    render_pnl_breakdown(stats)
    
    st.divider()
    
    # Trading Calendar
    render_trading_calendar(trades_df)
    
    st.divider()
    
    # Additional stats
    st.markdown("##### 📈 Thống kê tổng quan")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔢 Tổng số lệnh", f"{stats.get('total_trades', 0):,}")
    
    with col2:
        win_rate = stats.get('win_rate', 0)
        st.metric("🎯 Tỷ lệ thắng", f"{win_rate:.1f}%")
    
    with col3:
        avg_pnl = stats.get('avg_pnl', 0)
        st.metric("💰 PnL trung bình/lệnh", format_currency(avg_pnl))
    
    with col4:
        total_value = stats.get('total_value', 0)
        st.metric("💼 Tổng giá trị tài sản", f"${total_value:,.2f}")
