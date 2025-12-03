"""
Phase 5: Streamlit Dashboard Main App
Crypto ML Trading Bot Dashboard - Vietnamese Interface

Features:
- Real-time monitoring (Kafka + SQLite)
- Performance metrics (Realized/Unrealized PnL)
- Explainable AI (XAI)
- Risk control (Panic button, Risk gauge)
- What-If calculator (Backtest simulation)

Theo PHASE5_DASHBOARD_GUIDE.md
"""
import streamlit as st
import sys
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.dashboard.utils.db_utils import DatabaseConnector
from app.dashboard.components.performance_metrics import render_performance_metrics
from app.dashboard.components.xai_insights import render_xai_insights
from app.dashboard.components.realtime_monitor import render_realtime_monitor
from app.dashboard.components.risk_control import render_risk_control
from app.dashboard.components.whatif_calculator import render_whatif_calculator


# Page config
st.set_page_config(
    page_title="Crypto ML Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E40AF;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stMetric {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main dashboard application"""
    
    # Header
    st.markdown('<p class="main-header">📊 Crypto ML Trading Dashboard</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">🤖 Hệ thống giao dịch tự động với Machine Learning & Backtrader</p>',
        unsafe_allow_html=True
    )
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/bitcoin.png", width=80)
        st.markdown("## ⚙️ Cài Đặt")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("🔄 Tự động làm mới", value=True)
        
        if auto_refresh:
            refresh_interval = st.slider(
                "Tần suất làm mới (giây)",
                min_value=5,
                max_value=60,
                value=10,
                step=5
            )
            # Auto-refresh
            st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")
        
        st.divider()
        
        # Navigation
        st.markdown("## 📍 Điều Hướng")
        
        page = st.radio(
            "Chọn trang:",
            options=[
                "🏠 Tổng quan",
                "📊 Hiệu suất",
                "🧠 Giải thích AI",
                "🔴 Giám sát Real-time",
                "🛡️ Kiểm soát Rủi ro",
                "🧮 Máy tính Giả lập"
            ],
            index=0
        )
        
        st.divider()
        
        # System info
        st.markdown("## ℹ️ Thông Tin Hệ Thống")
        st.info("""
        **Phase 5**: Streamlit Dashboard  
        **Version**: 1.0.0  
        **Database**: SQLite  
        **ML Engine**: Ensemble (RF + KNN)  
        **Execution**: Backtrader  
        **Data Stream**: Kafka
        """)
        
        st.divider()
        
        # Help
        with st.expander("❓ Trợ giúp"):
            st.markdown("""
            **Các trang chính:**
            - 🏠 **Tổng quan**: Snapshot toàn bộ hệ thống
            - 📊 **Hiệu suất**: PnL breakdown, calendar
            - 🧠 **Giải thích AI**: Tại sao Bot mua/bán
            - 🔴 **Real-time**: Vị thế đang mở, signals
            - 🛡️ **Rủi ro**: Panic button, pause trading
            - 🧮 **Giả lập**: Backtest với vốn tùy chọn
            
            **Hotkeys:**
            - `R`: Refresh
            - `S`: Screenshot
            - `?`: Help
            """)
    
    # Initialize database connector
    try:
        db = DatabaseConnector()
        
        # Fetch data
        stats = db.get_summary_stats()
        all_trades = db.get_all_trades()
        recent_trades = db.get_recent_trades(limit=20)
        positions = db.get_open_positions()
        equity = db.get_equity_curve()
        
    except FileNotFoundError:
        st.error("""
        ❌ **Database không tồn tại!**
        
        Vui lòng chạy Backtrader Decision Engine trước:
        ```bash
        python test_phase4_integration.py
        ```
        """)
        return
    except Exception as e:
        st.error(f"❌ Lỗi kết nối database: {str(e)}")
        return
    
    # Render selected page
    if page == "🏠 Tổng quan":
        render_overview_page(stats, recent_trades, positions)
    
    elif page == "📊 Hiệu suất":
        render_performance_metrics(stats, all_trades)
    
    elif page == "🧠 Giải thích AI":
        render_xai_insights(recent_trades)
    
    elif page == "🔴 Giám sát Real-time":
        render_realtime_monitor(positions, recent_trades, equity)
    
    elif page == "🛡️ Kiểm soát Rủi ro":
        render_risk_control(recent_trades)
    
    elif page == "🧮 Máy tính Giả lập":
        render_whatif_calculator(all_trades)


def render_overview_page(stats: dict, recent_trades, positions):
    """
    Render overview page with key metrics
    
    Args:
        stats: Summary statistics
        recent_trades: Recent trades DataFrame
        positions: Open positions DataFrame
    """
    st.markdown("## 🏠 Tổng Quan Hệ Thống")
    
    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_value = stats.get('total_value', 0)
        st.metric(
            "💼 Tổng tài sản",
            f"${total_value:,.2f}"
        )
    
    with col2:
        net_pnl = stats.get('net_pnl', 0)
        st.metric(
            "💰 Lãi ròng",
            f"${abs(net_pnl):,.2f}",
            delta=f"${net_pnl:,.2f}"
        )
    
    with col3:
        win_rate = stats.get('win_rate', 0)
        st.metric(
            "🎯 Tỷ lệ thắng",
            f"{win_rate:.1f}%"
        )
    
    with col4:
        total_trades = stats.get('total_trades', 0)
        st.metric(
            "🔢 Tổng lệnh",
            f"{total_trades:,}"
        )
    
    with col5:
        open_positions = len(positions)
        st.metric(
            "📊 Vị thế mở",
            f"{open_positions}"
        )
    
    st.divider()
    
    # Quick stats
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### 🔔 Hoạt động gần đây")
        
        if not recent_trades.empty:
            # Display recent 5 trades
            display_trades = recent_trades.head(5)
            
            for idx, trade in display_trades.iterrows():
                action = trade['action']
                symbol = trade['symbol']
                price = trade['price']
                timestamp = trade['timestamp'].strftime('%d/%m %H:%M')
                pnl = trade.get('pnl', 0)
                
                action_color = "🟢" if action == "BUY" else "🔴"
                pnl_text = f"(PnL: ${pnl:,.2f})" if pnl and pnl != 0 else ""
                
                st.markdown(f"{action_color} **{timestamp}** - {action} {symbol} @ ${price:,.2f} {pnl_text}")
        else:
            st.info("Chưa có giao dịch nào")
    
    with col_right:
        st.markdown("### 📊 Phân bổ tài sản")
        
        cash = stats.get('cash', 0)
        positions_value = stats.get('positions_value', 0)
        
        import plotly.graph_objects as go
        
        fig = go.Figure(data=[go.Pie(
            labels=['Tiền mặt', 'Vị thế'],
            values=[cash, positions_value],
            hole=0.4,
            marker_colors=['#10B981', '#3B82F6']
        )])
        
        fig.update_layout(
            height=250,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, width='stretch')
    
    st.divider()
    
    # System status
    st.markdown("### ⚡ Trạng thái hệ thống")
    
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    
    with status_col1:
        st.success("✅ Database: Hoạt động")
    
    with status_col2:
        st.success("✅ Kafka: Kết nối")
    
    with status_col3:
        st.success("✅ ML Models: Loaded")
    
    with status_col4:
        if 'trading_paused' in st.session_state and st.session_state.trading_paused:
            st.warning("⏸️ Trading: Tạm dừng")
        else:
            st.success("✅ Trading: Hoạt động")


if __name__ == "__main__":
    main()
