# 🚀 QUICK START - Phase 5 Dashboard

## Khởi Động Nhanh (3 Bước)

### 1️⃣ Khởi động Kafka
```bash
docker-compose up -d
```
Kiểm tra: http://localhost:8080 (Kafka UI)

### 2️⃣ Chạy Backtrader Decision Engine
```bash
python test_phase4_integration.py
```
Đợi cho đến khi thấy: `✅ Đã mua BTCUSDT` và `✅ Đã mua ETHUSDT`

### 3️⃣ Khởi động Dashboard
```bash
start_dashboard.bat
```
Hoặc:
```bash
streamlit run app\dashboard\main.py
```

Truy cập: **http://localhost:8501**

---

## 📊 Các Trang Chính

### 🏠 Tổng Quan
- **Key Metrics:** Tổng tài sản, lãi ròng, tỷ lệ thắng, số lệnh, vị thế mở
- **Recent Activity:** 5 giao dịch gần nhất
- **Asset Allocation:** Pie chart phân bổ tiền mặt/vị thế
- **System Status:** Trạng thái Kafka, Database, ML Models

### 📊 Hiệu Suất
- **PnL Breakdown:** Realized (đã chốt) vs Unrealized (dự kiến) vs Net (ròng)
- **Waterfall Chart:** Dòng tiền từ vốn → lãi/lỗ → phí → tổng
- **Trading Calendar:** Heatmap lãi/lỗ theo ngày (giống GitHub)
- **Stats:** Win rate, avg PnL, best/worst day

### 🧠 Giải Thích AI
- **Chọn lệnh:** Dropdown chọn giao dịch để phân tích
- **Feature Importance:** Top 5 yếu tố quan trọng (RSI, Volume, MACD...)
- **Radar Chart:** So sánh điều kiện thực tế vs lý tưởng
- **Explanation:** Lý do chi tiết tại sao Bot mua/bán

### 🔴 Giám Sát Real-time
- **Open Positions:** Vị thế đang mở với unrealized PnL
- **Recent Signals:** 10 tín hiệu gần nhất
- **Equity Curve:** Đường cong tài sản (total/cash/positions)

### 🛡️ Kiểm Soát Rủi Ro
- **Risk Gauge:** Đồng hồ đo biến động (0-100)
  - Xanh: An toàn (< 30)
  - Vàng: Cẩn thận (30-60)
  - Đỏ: Nguy hiểm (> 60)
- **Trading Pause:** Toggle tạm dừng nhận lệnh mới
- **Panic Button:** Đóng tất cả vị thế (khẩn cấp)

### 🧮 Máy Tính Giả Lập
- **Input:** Vốn đầu tư + Khung thời gian
- **Output:** 
  - Lợi nhuận nếu bắt đầu X ngày trước
  - Win rate, max drawdown
  - Sharpe Ratio, Profit Factor
  - Cumulative return chart

---

## ⚙️ Cài Đặt

### Auto-Refresh
- Bật/tắt tự động làm mới
- Điều chỉnh tần suất: 5-60 giây

### Navigation
- Sidebar → Chọn trang
- Hotkey `R`: Refresh

---

## 🐛 Troubleshooting

### Dashboard không hiển thị dữ liệu?
```bash
# Kiểm tra database
python -c "import sqlite3; print(sqlite3.connect('data/trading_logs.db').execute('SELECT COUNT(*) FROM trades').fetchone())"
```

Nếu trả về 0 → Chạy lại `test_phase4_integration.py`

### Streamlit báo lỗi module?
```bash
pip install streamlit plotly streamlit-autorefresh pandas-ta
```

### Port 8501 đã được sử dụng?
```bash
streamlit run app\dashboard\main.py --server.port 8502
```

---

## 📚 Chi Tiết

Đọc thêm: `PHASE5_COMPLETION_REPORT.md`

---

**Dashboard Status:** ✅ Running at http://localhost:8501
