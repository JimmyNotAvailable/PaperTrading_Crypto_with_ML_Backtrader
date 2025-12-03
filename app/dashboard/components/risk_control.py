"""
Risk Control Component
Panic Button, Risk Gauge, Pause Trading
Theo PHASE5_DASHBOARD_GUIDE.md
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def render_panic_button():
    """
    Render emergency stop button
    Cho phép đóng tất cả vị thế khi thị trường biến động mạnh
    """
    st.markdown("### 🚨 Kiểm Soát Khẩn Cấp")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button(
            "🛑 ĐÓNG TẤT CẢ VỊ THẾ",
            type="primary",
            use_container_width=True,
            help="Bán tháo toàn bộ positions - Chỉ dùng khi khẩn cấp!"
        ):
            st.warning("⚠️ Tính năng này sẽ được kích hoạt trong phiên bản production")
            st.info("Sẽ gửi lệnh SELL cho tất cả open positions qua Kafka")
    
    with col2:
        st.markdown("""
        **Khi nào dùng Panic Button?**
        - 🔴 Thị trường sụp đổ đột ngột (Black Swan)
        - 🔴 Bot ra quyết định sai liên tiếp
        - 🔴 Lỗ vượt quá ngưỡng chịu đựng
        
        ⚠️ **Lưu ý:** Việc bán tháo có thể gây lỗ lớn do slippage
        """)


def render_trading_pause():
    """
    Render trading pause toggle
    Tạm dừng Bot nhận tín hiệu mới (không đóng vị thế hiện tại)
    """
    st.markdown("### ⏸️ Tạm Dừng Giao Dịch")
    
    # Session state for pause status
    if 'trading_paused' not in st.session_state:
        st.session_state.trading_paused = False
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        pause_status = st.toggle(
            "Tạm dừng nhận lệnh mới",
            value=st.session_state.trading_paused,
            help="Bot sẽ không mở vị thế mới nhưng vẫn giữ positions hiện tại"
        )
        
        st.session_state.trading_paused = pause_status
        
        if pause_status:
            st.error("⏸️ Bot đã TẠM DỪNG")
        else:
            st.success("▶️ Bot đang HOẠT ĐỘNG")
    
    with col2:
        if pause_status:
            st.warning("""
            **Chế độ tạm dừng:**
            - ❌ Không nhận tín hiệu ML mới
            - ✅ Vẫn giữ các vị thế đang mở
            - ✅ Vẫn áp dụng SL/TP
            
            💡 Dùng khi: Thị trường biến động cao, cần quan sát
            """)
        else:
            st.info("""
            **Chế độ hoạt động bình thường:**
            - ✅ Nhận tín hiệu ML
            - ✅ Mở vị thế mới khi có cơ hội
            - ✅ Quản lý rủi ro tự động
            """)


def calculate_volatility_score(trades_df: pd.DataFrame) -> float:
    """
    Calculate volatility score (0-100)
    
    Args:
        trades_df: Recent trades DataFrame
    
    Returns:
        Volatility score
    """
    if trades_df.empty or len(trades_df) < 5:
        return 20  # Low volatility default
    
    # Calculate PnL variance
    recent_pnl = trades_df.head(20)['pnl'].dropna()
    
    if len(recent_pnl) < 2:
        return 20
    
    # Normalize variance to 0-100 scale
    pnl_std = recent_pnl.std()
    avg_price = trades_df.head(20)['price'].mean()
    
    # Volatility as percentage of average price
    volatility = (pnl_std / avg_price) * 100
    
    # Cap at 100
    return min(volatility * 10, 100)


def render_risk_gauge(trades_df: pd.DataFrame):
    """
    Render risk gauge meter
    Hiển thị độ biến động thị trường hiện tại
    
    Args:
        trades_df: Recent trades for volatility calculation
    """
    st.markdown("### 🎚️ Đồng Hồ Rủi Ro (Risk Gauge)")
    
    # Calculate volatility
    volatility_score = calculate_volatility_score(trades_df)
    
    # Determine risk level
    if volatility_score < 30:
        risk_level = "THẤP"
        risk_color = "green"
        risk_emoji = "🟢"
    elif volatility_score < 60:
        risk_level = "TRUNG BÌNH"
        risk_color = "orange"
        risk_emoji = "🟡"
    else:
        risk_level = "CAO"
        risk_color = "red"
        risk_emoji = "🔴"
    
    # Gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=volatility_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{risk_emoji} Mức độ rủi ro: {risk_level}", 'font': {'size': 20}},
        delta={'reference': 50, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': risk_color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#d4edda'},    # Light green
                {'range': [30, 60], 'color': '#fff3cd'},   # Light yellow
                {'range': [60, 100], 'color': '#f8d7da'}   # Light red
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': volatility_score
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        font={'color': "darkblue", 'family': "Arial"}
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Recommendations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**📊 Điểm biến động:** {volatility_score:.1f}/100")
    
    with col2:
        if volatility_score < 30:
            st.success("✅ Điều kiện ổn định, an toàn giao dịch")
        elif volatility_score < 60:
            st.warning("⚠️ Biến động vừa phải, cẩn thận với size lệnh")
        else:
            st.error("🚨 Biến động cao, cân nhắc tạm dừng hoặc giảm leverage")


def render_risk_control(trades_df: pd.DataFrame):
    """
    Main function to render risk control component
    
    Args:
        trades_df: Recent trades DataFrame
    """
    st.markdown("## 🛡️ Kiểm Soát Rủi Ro")
    
    # Risk gauge
    render_risk_gauge(trades_df)
    
    st.divider()
    
    # Trading pause
    render_trading_pause()
    
    st.divider()
    
    # Panic button
    render_panic_button()
    
    st.divider()
    
    # Risk management settings
    with st.expander("⚙️ Cài đặt quản lý rủi ro"):
        st.markdown("""
        **Thông số hiện tại (từ Backtrader):**
        - 🛑 Stop Loss: 2% mỗi lệnh
        - 🎯 Take Profit: 5% mỗi lệnh
        - 📊 Confidence tối thiểu: 60%
        - 💰 Max position size: 20% tài sản
        
        💡 **Lưu ý:** Điều chỉnh thông số trong file `config/production_config.py`
        """)
