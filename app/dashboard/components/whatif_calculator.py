"""
What-If Calculator Component
Backtest simulation với input parameters
Theo PHASE5_DASHBOARD_GUIDE.md
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.dashboard.utils.db_utils import format_currency, format_percentage


def simulate_backtest(
    initial_capital: float,
    days_ago: int,
    trades_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Simulate backtest for given parameters
    
    Args:
        initial_capital: Starting capital
        days_ago: Number of days to look back
        trades_df: All trades DataFrame
    
    Returns:
        Dictionary with simulation results
    """
    # Filter trades within timeframe
    cutoff_date = datetime.now() - timedelta(days=days_ago)
    filtered_trades = trades_df[trades_df['timestamp'] >= cutoff_date].copy()
    
    if filtered_trades.empty:
        return {
            'success': False,
            'message': f'Không có dữ liệu giao dịch trong {days_ago} ngày qua'
        }
    
    # Calculate returns
    filtered_trades = filtered_trades.sort_values('timestamp')
    
    # Calculate cumulative PnL
    cumulative_pnl = filtered_trades['pnl'].fillna(0).cumsum()
    final_value = initial_capital + cumulative_pnl.iloc[-1]
    
    # Calculate metrics
    total_trades = len(filtered_trades)
    winning_trades = len(filtered_trades[filtered_trades['pnl'] > 0])
    losing_trades = len(filtered_trades[filtered_trades['pnl'] < 0])
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_return = final_value - initial_capital
    total_return_pct = (total_return / initial_capital) * 100
    
    # Max drawdown
    cumulative_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - cumulative_max
    max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
    max_drawdown_pct = (max_drawdown / initial_capital * 100) if initial_capital > 0 else 0
    
    # Sharpe ratio (simplified)
    if len(filtered_trades) > 1:
        returns = filtered_trades['pnl_pct'].fillna(0)
        sharpe = (returns.mean() / returns.std()) if returns.std() > 0 else 0
    else:
        sharpe = 0
    
    return {
        'success': True,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'sharpe_ratio': sharpe,
        'trades': filtered_trades,
        'cumulative_pnl': cumulative_pnl
    }


def render_simulation_results(results: Dict[str, Any]):
    """
    Render simulation results
    
    Args:
        results: Simulation results dictionary
    """
    if not results['success']:
        st.warning(results['message'])
        return
    
    st.markdown("### 📊 Kết Quả Mô Phỏng")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💼 Vốn ban đầu",
            f"${results['initial_capital']:,.2f}"
        )
    
    with col2:
        st.metric(
            "💰 Giá trị cuối",
            f"${results['final_value']:,.2f}",
            delta=format_currency(results['total_return'])
        )
    
    with col3:
        st.metric(
            "📈 Lợi nhuận",
            format_percentage(results['total_return_pct'], include_sign=False),
            delta=format_percentage(results['total_return_pct'])
        )
    
    with col4:
        st.metric(
            "🎯 Tỷ lệ thắng",
            f"{results['win_rate']:.1f}%"
        )
    
    # Additional metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("🔢 Tổng số lệnh", f"{results['total_trades']:,}")
    
    with col6:
        st.metric("✅ Lệnh thắng", f"{results['winning_trades']:,}")
    
    with col7:
        st.metric("❌ Lệnh thua", f"{results['losing_trades']:,}")
    
    with col8:
        st.metric(
            "📉 Max Drawdown",
            format_percentage(results['max_drawdown_pct'], include_sign=False),
            delta=f"-{results['max_drawdown_pct']:.1f}%",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Cumulative return chart
    st.markdown("#### 📈 Đường cong tích lũy (Cumulative Returns)")
    
    trades = results['trades']
    cumulative_pnl = results['cumulative_pnl']
    
    fig = go.Figure()
    
    # Cumulative PnL
    fig.add_trace(go.Scatter(
        x=trades['timestamp'],
        y=cumulative_pnl + results['initial_capital'],
        mode='lines',
        name='Giá trị tài sản',
        line=dict(color='rgb(59, 130, 246)', width=2),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)'
    ))
    
    # Initial capital line
    fig.add_hline(
        y=results['initial_capital'],
        line_dash="dash",
        line_color="gray",
        annotation_text="Vốn ban đầu",
        annotation_position="right"
    )
    
    fig.update_layout(
        height=400,
        hovermode='x unified',
        xaxis_title="Thời gian",
        yaxis_title="Giá trị ($)",
        showlegend=True
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Risk-adjusted metrics
    with st.expander("📊 Chỉ số rủi ro nâng cao"):
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown(f"""
            **Sharpe Ratio:**  
            `{results['sharpe_ratio']:.2f}`
            
            *Tỷ lệ lợi nhuận/rủi ro*
            - > 1: Tốt
            - > 2: Rất tốt
            - > 3: Xuất sắc
            """)
        
        with col_b:
            avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if results['winning_trades'] > 0 else 0
            avg_loss = abs(trades[trades['pnl'] < 0]['pnl'].mean()) if results['losing_trades'] > 0 else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            st.markdown(f"""
            **Profit Factor:**  
            `{profit_factor:.2f}`
            
            *Tỷ lệ lãi TB / lỗ TB*
            - > 1: Profitable
            - > 1.5: Tốt
            - > 2: Rất tốt
            """)
        
        with col_c:
            recovery_factor = abs(results['total_return'] / results['max_drawdown']) if results['max_drawdown'] > 0 else 0
            
            st.markdown(f"""
            **Recovery Factor:**  
            `{recovery_factor:.2f}`
            
            *Lợi nhuận / Max Drawdown*
            - > 2: Tốt
            - > 3: Rất tốt
            - > 5: Xuất sắc
            """)


def render_whatif_calculator(trades_df: pd.DataFrame):
    """
    Main function to render What-If calculator
    
    Args:
        trades_df: All trades DataFrame
    """
    st.markdown("## 🧮 Máy Tính Giả Lập (What-If Calculator)")
    
    st.markdown("""
    Công cụ này giúp bạn trả lời câu hỏi: **"Nếu tôi đầu tư X$ vào chiến thuật này Y ngày trước, giờ tôi có bao nhiêu?"**
    """)
    
    st.divider()
    
    # Input parameters
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        initial_capital = st.number_input(
            "💰 Vốn đầu tư ban đầu ($)",
            min_value=100.0,
            max_value=1000000.0,
            value=10000.0,
            step=1000.0,
            help="Số tiền bạn sẽ bắt đầu giao dịch"
        )
    
    with col_input2:
        timeframe_options = {
            "7 ngày qua": 7,
            "14 ngày qua": 14,
            "1 tháng qua (30 ngày)": 30,
            "2 tháng qua (60 ngày)": 60,
            "3 tháng qua (90 ngày)": 90
        }
        
        timeframe_label = st.selectbox(
            "📅 Khung thời gian",
            options=list(timeframe_options.keys()),
            index=2,
            help="Khoảng thời gian để chạy backtest"
        )
        
        days_ago = timeframe_options[timeframe_label]
    
    # Run simulation button
    if st.button("🚀 Chạy Mô Phỏng", type="primary", use_container_width=True):
        with st.spinner("Đang tính toán..."):
            results = simulate_backtest(initial_capital, days_ago, trades_df)
            render_simulation_results(results)
    
    st.divider()
    
    # Educational note
    with st.expander("ℹ️ Cách sử dụng What-If Calculator"):
        st.markdown("""
        **Cách hoạt động:**
        1. Nhập số vốn bạn muốn đầu tư
        2. Chọn khung thời gian để backtest
        3. Hệ thống sẽ áp dụng tất cả các lệnh giao dịch trong quá khứ lên vốn của bạn
        4. Xem kết quả: Lãi/lỗ, tỷ lệ thắng, max drawdown...
        
        **Lưu ý quan trọng:**
        - ⚠️ Kết quả quá khứ KHÔNG đảm bảo lợi nhuận tương lai
        - ⚠️ Đây là mô phỏng trên dữ liệu lịch sử, không tính phí trượt giá (slippage)
        - ✅ Dùng để đánh giá độ ổn định của chiến lược
        - ✅ Hiểu rõ rủi ro trước khi giao dịch thực
        
        **Chỉ số cần chú ý:**
        - **Win Rate**: Tỷ lệ thắng (tốt nếu > 50%)
        - **Max Drawdown**: Mức lỗ tối đa (nên < 20%)
        - **Sharpe Ratio**: Tỷ lệ lợi nhuận/rủi ro (tốt nếu > 1)
        """)
