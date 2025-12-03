# 🚀 PHASE 5 - STREAMLIT DASHBOARD - HƯỚNG DẪN NHANH

## 📋 CHECKLIST TRƯỚC KHI BẮT ĐẦU

### ✅ Phase 4 đã hoàn thành:
- [x] Backtrader Decision Engine hoạt động
- [x] SQLite database có dữ liệu (`data/trading_logs.db`)
- [x] Kafka topics ready (`crypto.ml_signals`, `crypto.orders`)
- [x] Log system 100% tiếng Việt, không emoji
- [x] Full pipeline test thành công

### 📊 Dữ liệu có sẵn:
```python
# SQLite: data/trading_logs.db
- trades table: timestamp, symbol, action, price, amount, ml_confidence, etc.
- equity table: (chưa dùng)
- positions table: (chưa dùng)

# Kafka streams:
- crypto.market_data: OHLCV real-time
- crypto.ml_signals: ML predictions
- crypto.orders: Trading decisions
```

---

## 🎯 MỤC TIÊU PHASE 5

Xây dựng **Streamlit Dashboard** với 5 components chính:

### 1. **Real-time Market Charts** 📈
- Candlestick charts (Plotly)
- AI signal overlays (BUY/SELL arrows)
- Technical indicators (MA, RSI)
- Multi-symbol tabs

### 2. **Execution Console** 💻
- Vietnamese logs real-time
- Color-coded (green=BUY, red=SELL, yellow=SKIP)
- Auto-scroll, filter by symbol
- Show R/R ratio, confidence

### 3. **Equity Curve** 💰
- Portfolio value over time
- PnL visualization
- Drawdown tracking
- Benchmark comparison

### 4. **Performance Metrics** 📊
- Win Rate
- Average Profit/Loss
- Sharpe Ratio
- Max Drawdown
- Total Trades
- Average R/R Ratio

### 5. **Active Positions** 🔍
- Current open positions
- Entry price, SL, TP
- Unrealized PnL
- Time in position

---

## 🛠️ CÀI ĐẶT DEPENDENCIES

```powershell
# Activate virtual environment
.\crypto-venv\Scripts\Activate.ps1

# Install Streamlit ecosystem
pip install streamlit==1.29.0
pip install plotly==5.18.0
pip install pandas==2.1.4
pip install streamlit-autorefresh==1.0.1

# Optional: Advanced visualization
pip install altair==5.2.0
pip install pydeck==0.8.1
```

---

## 📁 CẤU TRÚC THƯ MỤC

```
app/dashboard/
├── streamlit_app.py           # 🚀 Main entry point
├── components/
│   ├── __init__.py
│   ├── market_charts.py       # 📈 Real-time charts
│   ├── execution_console.py   # 💻 Log console
│   ├── equity_curve.py        # 💰 PnL visualization
│   ├── performance_metrics.py # 📊 Stats
│   └── position_tracker.py    # 🔍 Active positions
├── utils/
│   ├── __init__.py
│   ├── db_reader.py           # SQLite query helper
│   ├── kafka_consumer.py      # Real-time Kafka stream
│   └── data_processor.py      # Format data for charts
└── config/
    └── dashboard_config.py    # Settings (colors, layout)
```

---

## 🎨 LAYOUT DESIGN

```
┌─────────────────────────────────────────────────────────────┐
│  🚀 CRYPTO ML TRADING SYSTEM - DASHBOARD                    │
├─────────────────────────────────────────────────────────────┤
│  [BTCUSDT ▼] [ETHUSDT] [SOLUSDT] [BNBUSDT] [XRPUSDT]       │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                  │
│  📈 REAL-TIME CHART      │  💻 EXECUTION CONSOLE            │
│                          │                                  │
│  Candlestick with AI     │  [TIN HIEU ML] BTCUSDT           │
│  overlays                │     Du bao: BUY                  │
│                          │     Do tin cay: 80.34%           │
│  Technical Indicators:   │                                  │
│  ☑ MA(7, 25)            │  [QUYET DINH MUA]                │
│  ☑ RSI(14)              │     Risk/Reward: 1:2.50          │
│  ☑ Volume               │                                  │
│                          │  [KAFKA] Lenh BUY da gui         │
├──────────────────────────┴──────────────────────────────────┤
│  💰 EQUITY CURVE & PnL                                      │
│  [Line chart showing portfolio value over time]             │
├─────────────────────────────────────────────────────────────┤
│  📊 PERFORMANCE METRICS          🔍 ACTIVE POSITIONS        │
│  ├─ Win Rate: 65.5%              ├─ BTCUSDT                │
│  ├─ Total Trades: 127            │   Entry: $67,897.65     │
│  ├─ Avg R/R: 1:2.3               │   SL: $66,539.70        │
│  ├─ Sharpe: 1.85                 │   TP: $71,292.53        │
│  └─ Max DD: -12.3%               │   PnL: +$234.50 (2.5%)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 CODE TEMPLATE

### `streamlit_app.py` - Main Entry
```python
import streamlit as st
from components import market_charts, execution_console, equity_curve, performance_metrics, position_tracker
from utils import db_reader, kafka_consumer

st.set_page_config(
    page_title="Crypto ML Trading Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🚀 CRYPTO ML TRADING SYSTEM")
st.markdown("Real-time AI-powered cryptocurrency trading dashboard")

# Symbol selector
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
selected_symbol = st.selectbox("Chọn mã giao dịch:", symbols)

# Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Biểu đồ thị trường Real-time")
    market_charts.render(selected_symbol)

with col2:
    st.subheader("💻 Console giao dịch")
    execution_console.render()

# Second row
st.subheader("💰 Đường cong vốn & PnL")
equity_curve.render()

# Third row
col3, col4 = st.columns(2)

with col3:
    st.subheader("📊 Chỉ số hiệu suất")
    performance_metrics.render()

with col4:
    st.subheader("🔍 Vị thế đang mở")
    position_tracker.render()
```

### `utils/db_reader.py` - SQLite Helper
```python
import sqlite3
import pandas as pd
from pathlib import Path

class TradingDBReader:
    def __init__(self, db_path='data/trading_logs.db'):
        self.db_path = Path(db_path)
    
    def get_all_trades(self):
        """Lấy tất cả trades từ database"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    
    def get_recent_trades(self, limit=50):
        """Lấy N trades gần nhất"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM trades ORDER BY timestamp DESC LIMIT {limit}", conn)
        conn.close()
        return df
    
    def get_trades_by_symbol(self, symbol):
        """Lấy trades theo symbol"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f"SELECT * FROM trades WHERE symbol = '{symbol}' ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    
    def calculate_pnl(self):
        """Tính tổng PnL từ các trades"""
        df = self.get_all_trades()
        # Logic tính PnL dựa trên BUY/SELL pairs
        # TODO: Implement PnL calculation
        return 0.0
```

### `components/market_charts.py` - Plotly Charts
```python
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render(symbol):
    """Render real-time candlestick chart với AI overlays"""
    
    # TODO: Lấy OHLCV data từ Kafka hoặc database
    # For now, use dummy data
    
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} - Giá', 'Volume'),
        vertical_spacing=0.05
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=[],  # timestamps
            open=[],
            high=[],
            low=[],
            close=[],
            name='Giá'
        ),
        row=1, col=1
    )
    
    # Volume bars
    fig.add_trace(
        go.Bar(x=[], y=[], name='Volume', marker_color='rgba(0,150,255,0.3)'),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )
    
    st.plotly_chart(fig, use_container_width=True)
```

### `components/execution_console.py` - Logs Display
```python
import streamlit as st
from utils.db_reader import TradingDBReader

def render():
    """Hiển thị execution logs real-time"""
    
    db = TradingDBReader()
    trades = db.get_recent_trades(limit=20)
    
    # Auto-refresh every 2 seconds
    st.markdown("**Logs giao dịch gần đây:**")
    
    for _, trade in trades.iterrows():
        action_color = "🟢" if trade['action'] == 'BUY' else "🔴"
        
        st.markdown(f"""
        {action_color} **{trade['action']}** {trade['symbol']} @ ${trade['price']:,.2f}
        - Độ tin cậy: {trade['ml_confidence']*100:.2f}%
        - Lý do: {trade['reason']}
        """)
        st.divider()
```

---

## 🚀 CHẠY DASHBOARD

```powershell
# Start Kafka (nếu chưa chạy)
docker-compose up -d

# Start Decision Engine (terminal 1)
python app\consumers\backtrader_decision_engine.py

# Start Demo Signal Generator (terminal 2)
python demo_phase4.py --send-signals --duration 300 --interval 10

# Start Streamlit Dashboard (terminal 3)
streamlit run app\dashboard\streamlit_app.py
```

Dashboard sẽ mở tại: **http://localhost:8501**

---

## 📝 TODO PHASE 5

### Ưu tiên cao:
- [ ] Setup cấu trúc thư mục `app/dashboard/`
- [ ] Implement `db_reader.py` với SQLite queries
- [ ] Tạo `market_charts.py` với Plotly candlestick
- [ ] Tạo `execution_console.py` với real-time logs
- [ ] Implement auto-refresh mechanism

### Ưu tiên trung bình:
- [ ] Equity curve visualization
- [ ] Performance metrics calculation
- [ ] Active position tracker
- [ ] Kafka stream integration

### Ưu tiên thấp:
- [ ] Advanced charts (Heatmaps, correlation)
- [ ] Export reports (PDF, Excel)
- [ ] Alert system
- [ ] Mobile-responsive layout

---

## 🎨 THEME & STYLING

**Vietnamese Labels:**
```python
LABELS = {
    'buy': 'MUA',
    'sell': 'BÁN',
    'neutral': 'TRUNG LẬP',
    'confidence': 'Độ tin cậy',
    'price': 'Giá',
    'amount': 'Số lượng',
    'pnl': 'Lãi/Lỗ',
    'win_rate': 'Tỷ lệ thắng',
    'total_trades': 'Tổng số giao dịch'
}
```

**Color Scheme:**
```python
COLORS = {
    'buy': '#26A69A',      # Green
    'sell': '#EF5350',     # Red
    'neutral': '#FFA726',  # Orange
    'background': '#1E1E1E',
    'text': '#FFFFFF'
}
```

---

## 📚 TÀI LIỆU THAM KHẢO

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [SQLite with Pandas](https://pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html)
- [Kafka Python Consumer](https://docs.confluent.io/kafka-clients/python/current/overview.html)

---

## ⚡ TIPS & TRICKS

1. **Auto-refresh:** Dùng `streamlit-autorefresh` để update data tự động
2. **Caching:** Dùng `@st.cache_data` cho queries nặng
3. **Session State:** Lưu trạng thái user selections
4. **Layout:** Dùng `st.columns()` và `st.expander()` cho UI gọn gàng
5. **Performance:** Limit database queries, dùng pagination

---

**Sẵn sàng bắt đầu Phase 5! 🚀**

*File này sẽ được cập nhật khi triển khai dashboard*
