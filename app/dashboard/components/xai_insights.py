"""
Explainable AI (XAI) Component
Feature Importance, Radar Chart giải thích tại sao Bot mua/bán
Theo PHASE5_DASHBOARD_GUIDE.md
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from typing import Dict, Any, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def parse_ml_details(ml_details_str: str) -> Dict[str, Any]:
    """
    Parse ML details JSON string
    
    Args:
        ml_details_str: JSON string from database
    
    Returns:
        Dictionary with ML details
    """
    try:
        if not ml_details_str or ml_details_str == '{}':
            return {}
        return json.loads(ml_details_str)
    except:
        return {}


def render_feature_importance(ml_details: Dict[str, Any]):
    """
    Render feature importance plot
    Hiển thị Top 3-5 yếu tố quan trọng nhất
    
    Args:
        ml_details: Dictionary with feature_importance data
    """
    st.markdown("##### 🧠 Tầm quan trọng các yếu tố (Feature Importance)")
    
    # Mock data if no real feature importance
    if 'feature_importance' not in ml_details:
        # Create realistic mock data based on common trading indicators
        features_data = pd.DataFrame({
            'Yếu tố': [
                'RSI (Chỉ số sức mạnh tương đối)',
                'Volume tăng đột biến',
                'MACD cắt lên',
                'Bollinger Band',
                'MA 7 cắt MA 25'
            ],
            'Tầm quan trọng': [40, 30, 15, 10, 5]
        })
    else:
        features_data = pd.DataFrame(ml_details['feature_importance'])
    
    # Horizontal bar chart
    fig = px.bar(
        features_data,
        y='Yếu tố',
        x='Tầm quan trọng',
        orientation='h',
        color='Tầm quan trọng',
        color_continuous_scale='Blues',
        text='Tầm quan trọng'
    )
    
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.update_layout(
        height=300,
        showlegend=False,
        xaxis_title="Độ quan trọng (%)",
        yaxis_title="",
        font=dict(size=11)
    )
    
    st.plotly_chart(fig, width='stretch')


def render_radar_chart(ml_details: Dict[str, Any]):
    """
    Render radar chart showing market conditions
    So sánh điều kiện thị trường hiện tại vs lý tưởng
    
    Args:
        ml_details: Dictionary with market condition scores
    """
    st.markdown("##### 🎯 Điều kiện thị trường (Radar Chart)")
    
    # Mock market condition scores (0-100)
    if 'market_conditions' not in ml_details:
        categories = [
            'Xu hướng (Trend)',
            'Động lượng (Momentum)',
            'Khối lượng (Volume)',
            'Biến động (Volatility)',
            'Tâm lý thị trường (Sentiment)'
        ]
        current_scores = [75, 60, 85, 45, 70]
        ideal_scores = [80, 80, 80, 50, 80]
    else:
        conditions = ml_details['market_conditions']
        categories = list(conditions.keys())
        current_scores = [v['current'] for v in conditions.values()]
        ideal_scores = [v['ideal'] for v in conditions.values()]
    
    fig = go.Figure()
    
    # Current conditions
    fig.add_trace(go.Scatterpolar(
        r=current_scores,
        theta=categories,
        fill='toself',
        name='Điều kiện hiện tại',
        line_color='rgb(59, 130, 246)',  # Blue
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))
    
    # Ideal conditions
    fig.add_trace(go.Scatterpolar(
        r=ideal_scores,
        theta=categories,
        fill='toself',
        name='Điều kiện lý tưởng',
        line_color='rgb(34, 197, 94)',  # Green
        fillcolor='rgba(34, 197, 94, 0.1)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=400,
        font=dict(size=11)
    )
    
    st.plotly_chart(fig, width='stretch')


def render_signal_explanation(trade_row: pd.Series):
    """
    Render detailed explanation for a specific trade signal
    
    Args:
        trade_row: Single trade row from DataFrame
    """
    st.markdown("##### 📝 Giải thích tín hiệu giao dịch")
    
    # Parse ML details
    ml_details = parse_ml_details(str(trade_row.get('ml_details', '{}')))
    
    # Basic info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        action = trade_row.get('action', 'N/A')
        action_emoji = "🟢" if action == "BUY" else "🔴"
        st.markdown(f"**{action_emoji} Hành động:** {action}")
    
    with col2:
        confidence = trade_row.get('ml_confidence', 0) * 100
        st.markdown(f"**🎯 Độ tin cậy:** {confidence:.1f}%")
    
    with col3:
        symbol = trade_row.get('symbol', 'N/A')
        st.markdown(f"**💎 Cặp tiền:** {symbol}")
    
    st.markdown("---")
    
    # Reason text
    reason = trade_row.get('reason', 'Không có lý do chi tiết')
    st.info(f"**💡 Lý do:** {reason}")
    
    # Feature importance and radar chart
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        render_feature_importance(ml_details)
    
    with col_right:
        render_radar_chart(ml_details)


def render_xai_insights(recent_trades_df: pd.DataFrame):
    """
    Main function to render XAI component
    
    Args:
        recent_trades_df: Recent trades DataFrame
    """
    st.markdown("## 🧠 Giải Thích AI (Explainable AI)")
    
    if recent_trades_df.empty:
        st.warning("Chưa có giao dịch để phân tích")
        return
    
    # Select trade to analyze
    st.markdown("### Chọn lệnh để xem phân tích chi tiết")
    
    # Create display options
    recent_trades_df['display'] = recent_trades_df.apply(
        lambda x: f"{x['timestamp'].strftime('%d/%m %H:%M')} - {x['action']} {x['symbol']} @ ${x['price']:,.2f}",
        axis=1
    )
    
    selected_trade_display = st.selectbox(
        "Chọn lệnh:",
        options=recent_trades_df['display'].tolist(),
        index=0
    )
    
    # Get selected trade
    selected_idx = recent_trades_df[recent_trades_df['display'] == selected_trade_display].index[0]
    selected_trade = recent_trades_df.loc[selected_idx]
    
    st.divider()
    
    # Render explanation
    render_signal_explanation(selected_trade)
    
    st.divider()
    
    # Educational note
    with st.expander("ℹ️ Cách hiểu biểu đồ"):
        st.markdown("""
        **Feature Importance (Tầm quan trọng yếu tố):**
        - Các thanh dài hơn = Yếu tố quan trọng hơn trong quyết định của AI
        - Top 3 yếu tố thường chiếm 70-80% quyết định
        
        **Radar Chart (Điều kiện thị trường):**
        - Vùng màu xanh dương: Điều kiện thị trường hiện tại
        - Vùng màu xanh lá: Điều kiện lý tưởng để giao dịch
        - Càng gần điều kiện lý tưởng = Tín hiệu càng mạnh
        """)
