# 🚀 QUICK START GUIDE

Hướng dẫn nhanh để chạy Discord Bot dự đoán giá Crypto.

---

## ⚡ Setup Tự Động (Khuyến nghị)

### Windows:

```powershell
# Chạy script setup tự động
.\scripts\setup_environment.ps1
```

Script sẽ tự động:
- ✅ Tạo virtual environment
- ✅ Cài đặt dependencies
- ✅ Tạo file .env từ template
- ✅ Hỏi và lưu Discord Bot Token
- ✅ Tạo các thư mục cần thiết

---

## 🔧 Setup Thủ Công

### 1. Cài đặt môi trường

```powershell
# Clone repository (nếu chưa có)
git clone <your-repo-url>
cd crypto-ml-trading-project

# Tạo virtual environment
python -m venv crypto-venv

# Kích hoạt virtual environment
.\crypto-venv\Scripts\Activate.ps1  # Windows
# source crypto-venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Cấu hình Discord Bot Token

**A. Lấy Discord Bot Token:**

1. Vào https://discord.com/developers/applications
2. Click "New Application" → đặt tên bot
3. Vào tab "Bot" → Click "Add Bot"
4. Click "Reset Token" → Copy token (chỉ hiển thị 1 lần!)

**B. Lưu token vào .env:**

```powershell
# Copy template
copy .env.example .env

# Mở file .env và chỉnh sửa:
# DISCORD_BOT_TOKEN=paste-your-token-here
```

**⚠️ QUAN TRỌNG:** File .env đã được thêm vào .gitignore. KHÔNG commit token lên Git!

### 3. Mời Bot vào Discord Server

1. Vào https://discord.com/developers/applications
2. Chọn application của bạn → Tab "OAuth2" → "URL Generator"
3. Chọn:
   - **Scopes**: `bot`
   - **Bot Permissions**: 
     - Send Messages
     - Read Message History
     - Add Reactions
     - Embed Links
4. Copy URL và mở trong browser
5. Chọn server và authorize

---

## ▶️ Chạy Bot

```powershell
# Activate virtual environment (nếu chưa)
.\crypto-venv\Scripts\Activate.ps1

# Chạy bot
python app\bot.py
```

**Kết quả mong đợi:**

```
✅ Loaded environment variables from .env file
✅ Token loaded from DISCORD_BOT_TOKEN environment variable
🔍 Starting single bot instance...
🤖 Logged in as YourBot#1234 (ID: 1234567890)
```

---

## 🎮 Test Bot trên Discord

Trong Discord server, thử các lệnh:

```
!ping              # Kiểm tra bot online
!help              # Xem danh sách lệnh
!dudoan BTC        # Dự đoán giá Bitcoin
!price ETH         # Xem giá Ethereum hiện tại
!gia BNB           # Xem giá BNB (tiếng Việt)
!movers            # Top gainers/losers 24h
```

**Ví dụ output:**

```
!dudoan BTC
→ Bot trả về embed với:
   📊 Giá hiện tại: $68,000.00
   🎯 Giá dự đoán: $69,500.00
   📈 Thay đổi dự kiến: +2.21%
   🇻🇳 Giá VND: 1,632,000,000 đ
   🧠 Model: linear_regression R²=0.892
```

---

## 🐛 Xử Lý Lỗi Thường Gặp

### Lỗi: "BOT_TOKEN not provided"

**Nguyên nhân:** Chưa cấu hình token trong .env

**Giải pháp:**
```powershell
# 1. Kiểm tra file .env có tồn tại không
Test-Path .env

# 2. Mở .env và thêm token:
notepad .env

# 3. Đảm bảo có dòng:
DISCORD_BOT_TOKEN=your-actual-token-here
```

### Lỗi: "401 Unauthorized" khi start bot

**Nguyên nhân:** Token không hợp lệ hoặc đã expire

**Giải pháp:**
1. Vào Discord Developer Portal
2. Reset token
3. Copy token mới
4. Update trong file .env
5. Chạy lại bot

### Lỗi: Bot không phản hồi commands

**Kiểm tra:**
```
1. Bot đã online chưa? (màu xanh trên Discord)
2. Bot có quyền "Send Messages" không?
3. Command có đúng prefix ! không?
4. Có chạy nhiều instance bot không? (check process)
```

### Lỗi: "python-dotenv not installed"

**Giải pháp:**
```powershell
pip install python-dotenv
```

### Lỗi: "Production model package not found"

**Nguyên nhân:** Chưa train models hoặc file models bị thiếu

**Giải pháp:**
```powershell
# Option 1: Train models mới
python app\ml\train_all.py

# Option 2: Bot sẽ dùng stub data (demo) nếu không có models
# Vẫn chạy được nhưng predictions sẽ là dummy data
```

---

## 📊 Train Machine Learning Models (Tùy chọn)

Nếu muốn train models mới với dữ liệu riêng:

### 1. Thu thập dữ liệu:

```powershell
python app\data_collector\realtime_collector.py
```

### 2. Train models:

```powershell
python app\ml\train_all.py
```

### 3. Models sẽ được lưu tại:

```
models/
  ├── linreg_price.joblib
  ├── linreg_price_change.joblib
  ├── knn_crypto_classifier.joblib
  └── ...
```

---

## 🔐 Bảo Mật Token

### ✅ ĐÚNG:
```powershell
# Lưu token trong .env (không commit lên Git)
DISCORD_BOT_TOKEN=MTIzNDU2...

# Sử dụng environment variables
$env:DISCORD_BOT_TOKEN="MTIzNDU2..."
python app\bot.py
```

### ❌ SAI:
```powershell
# KHÔNG lưu token trực tiếp trong code
token = "MTIzNDU2..."  # ❌ NGUY HIỂM!

# KHÔNG commit file token.txt lên Git
git add token.txt  # ❌ TUYỆT ĐỐI KHÔNG!
```

### 🆘 Nếu token bị leak:

**Xem hướng dẫn chi tiết:** `docs\HUONG_DAN_BAO_MAT_TOKEN.md`

**Tóm tắt:**
1. Reset token ngay trên Discord Portal
2. Xóa token khỏi Git history
3. Update token mới vào .env
4. Force push repository

---

## 📁 Cấu Trúc Thư Mục

```
crypto-ml-trading-project/
├── app/
│   ├── bot.py                    # ← Discord Bot chính
│   ├── ml/                       # ML models & training
│   ├── data_collector/           # Thu thập dữ liệu
│   └── services/                 # Business logic
├── data/
│   ├── models_production/        # Production models
│   └── realtime/                 # Real-time data
├── docs/
│   ├── TONG_QUAN_DU_AN.md       # Tổng quan dự án
│   ├── HUONG_DAN_BAO_MAT_TOKEN.md  # Bảo mật token
│   └── QUICK_START.md           # ← Bạn đang đọc file này
├── scripts/
│   └── setup_environment.ps1    # Setup tự động
├── .env                          # ← Cấu hình (KHÔNG commit!)
├── .env.example                  # Template
├── requirements.txt              # Python dependencies
└── README.md                     # Hướng dẫn chính
```

---

## 🎯 Các Lệnh Hữu Ích

```powershell
# Activate virtual environment
.\crypto-venv\Scripts\Activate.ps1

# Chạy bot
python app\bot.py

# Train models
python app\ml\train_all.py

# Thu thập dữ liệu
python app\data_collector\realtime_collector.py

# Kiểm tra dependencies
pip list

# Update dependencies
pip install -r requirements.txt --upgrade

# Deactivate virtual environment
deactivate
```

---

## 📚 Tài Liệu Đầy Đủ

- **Tổng quan dự án**: `docs\TONG_QUAN_DU_AN.md`
- **Bảo mật token**: `docs\HUONG_DAN_BAO_MAT_TOKEN.md`
- **Bot commands**: `docs\BOT_COMMANDS.md`
- **Architecture**: `docs\ARCHITECTURE.md`
- **README chính**: `README.md`

---

## 🆘 Hỗ Trợ

Nếu gặp vấn đề:

1. **Đọc docs:** `docs\` folder
2. **Check logs:** Terminal output
3. **Verify setup:**
   ```powershell
   # Test .env file
   Test-Path .env
   
   # Test token (an toàn)
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Token exists:', bool(os.getenv('DISCORD_BOT_TOKEN')))"
   ```

---

## ⚠️ Lưu Ý Quan Trọng

1. **KHÔNG** commit file `.env` hoặc `token.txt` lên Git
2. **LUÔN** sử dụng environment variables cho secrets
3. **ĐỊNH KỲ** rotate Discord Bot Token (3-6 tháng)
4. Bot chỉ mang tính **HỌC TẬP/DEMO**, không dùng để trading thật
5. Cryptocurrency rất **RỦI RO**, không invest dựa vào predictions của bot

---

## 🎉 Kết Luận

Bạn đã sẵn sàng! Chạy bot và test trên Discord:

```powershell
python app\bot.py
```

Trong Discord:
```
!dudoan BTC
```

**Chúc bạn thành công! 🚀**

---

*Cập nhật: 2025-01-14*

