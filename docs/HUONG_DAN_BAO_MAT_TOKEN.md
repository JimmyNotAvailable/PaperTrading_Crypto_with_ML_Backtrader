# 🔐 HƯỚNG DẪN BẢO MẬT DISCORD BOT TOKEN

## ⚠️ CẢNH BÁO: TOKEN ĐÃ BỊ LEAK

Nếu bạn đã push file `token.txt` lên GitHub, token Discord Bot của bạn **ĐÃ BỊ LỘ CÔNG KHAI** và cần xử lý NGAY LẬP TỨC!

---

## 🚨 BƯỚC 1: THU HỒI TOKEN CŨ (QUAN TRỌNG NHẤT!)

### Thực hiện ngay:

1. **Truy cập Discord Developer Portal**
   - Vào: https://discord.com/developers/applications
   - Đăng nhập tài khoản Discord của bạn

2. **Chọn Application**
   - Click vào application (bot) của bạn trong danh sách

3. **Reset Token**
   - Vào tab **Bot** ở menu bên trái
   - Kéo xuống phần **TOKEN**
   - Click nút **Reset Token**
   - Xác nhận reset
   - **Copy token mới** (chỉ hiển thị 1 lần!)

4. **Lưu token mới an toàn**
   ```
   Dán vào notepad tạm thời
   KHÔNG lưu vào Git!
   ```

### ⚠️ Lưu ý:
- Token cũ sẽ **VÔ HIỆU HÓA NGAY LẬP TỨC**
- Bot sẽ **NGỪNG HOẠT ĐỘNG** cho đến khi bạn cập nhật token mới
- Ai có token cũ sẽ **KHÔNG THỂ** sử dụng nữa

---

## 🗑️ BƯỚC 2: XÓA TOKEN KHỎI GIT HISTORY

### Option A: Sử dụng git-filter-repo (Khuyến nghị)

```powershell
# 1. Cài đặt git-filter-repo
pip install git-filter-repo

# 2. Backup repository (quan trọng!)
cd ..
cp -r crypto-ml-trading-project crypto-ml-trading-project-backup

# 3. Quay lại repo
cd crypto-ml-trading-project

# 4. Xóa token.txt khỏi TOÀN BỘ lịch sử Git
git filter-repo --path token.txt --invert-paths

# 5. Xóa file token.txt còn lại (nếu có)
Remove-Item token.txt -ErrorAction SilentlyContinue

# 6. Commit thay đổi
git add .
git commit -m "security: remove token.txt from repository"

# 7. Force push (CẨN THẬN!)
git push origin --force --all
git push origin --force --tags
```

### Option B: Sử dụng BFG Repo-Cleaner (Alternative)

```powershell
# 1. Download BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. Chạy BFG
java -jar bfg.jar --delete-files token.txt

# 3. Cleanup
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. Force push
git push origin --force --all
```

### ⚠️ Cảnh báo khi Force Push:
- **Thông báo cho team members** trước khi force push
- Họ cần re-clone repository sau khi bạn force push
- Tất cả local branches sẽ bị conflict

---

## 🔧 BƯỚC 3: THIẾT LẬP BIẾN MÔI TRƯỜNG

### 3.1. Tạo file `.env` (Local Development)

```powershell
# Tạo file .env (đã có trong .gitignore)
New-Item -Path .env -ItemType File -Force
```

**Nội dung file `.env`:**
```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=YOUR_ACTUAL_DISCORD_BOT_TOKEN_HERE
BOT_TOKEN=YOUR_ACTUAL_DISCORD_BOT_TOKEN_HERE

# Database
MONGODB_URI=mongodb://localhost:27017/crypto

# Currency
FX_USD_VND=24000

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3.2. Cài đặt python-dotenv

```powershell
pip install python-dotenv
```

### 3.3. Cập nhật `requirements.txt`

```powershell
# Thêm vào requirements.txt
echo "python-dotenv>=1.0.0" >> requirements.txt
```

---

## 📝 BƯỚC 4: CẬP NHẬT CODE

### 4.1. Cập nhật `app/bot.py`

**Tìm function `read_bot_token()`:**

```python
# BEFORE (cũ)
def read_bot_token() -> Optional[str]:
	token = os.getenv("BOT_TOKEN")
	if token:
		return token.strip()
	# Fallback to token.txt
	root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	token_file = os.path.join(root, "token.txt")
	if os.path.exists(token_file):
		try:
			with open(token_file, "r", encoding="utf-8") as f:
				line = f.readline().strip()
				return line or None
		except Exception:
			return None
	return None
```

**Thay bằng (mới - ưu tiên .env):**

```python
from dotenv import load_dotenv

# Load .env file at module level
load_dotenv()

def read_bot_token() -> Optional[str]:
	"""
	Read Discord bot token from environment variables.
	
	Priority:
	1. DISCORD_BOT_TOKEN environment variable
	2. BOT_TOKEN environment variable  
	3. token.txt file (local dev fallback - NOT RECOMMENDED)
	
	Returns:
		Token string or None
	"""
	# Priority 1: DISCORD_BOT_TOKEN
	token = os.getenv("DISCORD_BOT_TOKEN")
	if token:
		return token.strip()
	
	# Priority 2: BOT_TOKEN (legacy compatibility)
	token = os.getenv("BOT_TOKEN")
	if token:
		return token.strip()
	
	# Priority 3: token.txt (NOT RECOMMENDED - only for local dev)
	# This should be removed in production!
	root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	token_file = os.path.join(root, "token.txt")
	
	if os.path.exists(token_file):
		print("⚠️ WARNING: Using token.txt file. This is NOT secure!")
		print("⚠️ Please use environment variables instead.")
		try:
			with open(token_file, "r", encoding="utf-8") as f:
				line = f.readline().strip()
				return line or None
		except Exception as e:
			print(f"❌ Error reading token.txt: {e}")
			return None
	
	return None
```

### 4.2. Thêm import ở đầu file `app/bot.py`

```python
# Thêm vào đầu file
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
```

---

## 🎯 BƯỚC 5: KIỂM TRA VÀ TEST

### 5.1. Kiểm tra `.gitignore`

```powershell
# Xem nội dung .gitignore
Get-Content .gitignore | Select-String -Pattern "token|.env"
```

**Đảm bảo có các dòng:**
```
# Environment variables
.env
token.txt
*.env
.env.*
!.env.example
```

### 5.2. Test local

```powershell
# Activate virtual environment
.\crypto-venv\Scripts\activate

# Test bot
python app/bot.py
```

**Expected output:**
```
🔍 Starting single bot instance...
🤖 Logged in as YourBot#1234 (ID: 1234567890)
```

### 5.3. Kiểm tra Git status

```powershell
git status

# KHÔNG ĐƯỢC thấy:
# - token.txt
# - .env
```

---

## 🚀 BƯỚC 6: SETUP CHO PRODUCTION

### 6.1. GitHub Actions (CI/CD)

**Thêm Secret vào GitHub:**

1. Vào repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `DISCORD_BOT_TOKEN`
4. Value: `your-actual-token-here`
5. Click **Add secret**

**Sử dụng trong workflow (`.github/workflows/deploy.yml`):**

```yaml
name: Deploy Bot

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    env:
      DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
      MONGODB_URI: ${{ secrets.MONGODB_URI }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run bot
        run: python app/bot.py
```

### 6.2. Docker

**Cập nhật `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  bot:
    build: .
    container_name: crypto-bot
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - MONGODB_URI=${MONGODB_URI}
      - FX_USD_VND=${FX_USD_VND:-24000}
    env_file:
      - .env  # Load from .env file
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    # DON'T mount token.txt!
```

**Chạy Docker:**

```powershell
# Set environment variable (Windows)
$env:DISCORD_BOT_TOKEN="your-token-here"

# Run Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

### 6.3. Cloud Deployment

#### Heroku

```powershell
# Set config vars
heroku config:set DISCORD_BOT_TOKEN="your-token-here"
heroku config:set MONGODB_URI="your-mongodb-uri"

# Deploy
git push heroku main
```

#### Railway.app

1. Connect GitHub repository
2. Vào **Variables** tab
3. Thêm: `DISCORD_BOT_TOKEN` = your token
4. Deploy

#### Azure Web App

```powershell
# Set application settings
az webapp config appsettings set \
  --resource-group myResourceGroup \
  --name myWebApp \
  --settings DISCORD_BOT_TOKEN="your-token-here"
```

---

## ✅ BƯỚC 7: BEST PRACTICES

### 7.1. Pre-commit Hooks (Ngăn commit secrets)

```powershell
# Cài đặt pre-commit
pip install pre-commit detect-secrets

# Tạo file .pre-commit-config.yaml
```

**Nội dung `.pre-commit-config.yaml`:**

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package.lock.json
```

**Setup:**

```powershell
# Initialize
pre-commit install

# Create baseline
detect-secrets scan > .secrets.baseline

# Test
git add .
git commit -m "test"
# Nếu có secret sẽ bị block!
```

### 7.2. Token Rotation (Định kỳ đổi token)

**Khuyến nghị:**
- Đổi token mỗi **3-6 tháng**
- Đổi ngay nếu nghi ngờ bị leak
- Lưu lịch sử token cũ (an toàn) để rollback nếu cần

**Quy trình:**
1. Reset token trên Discord Portal
2. Update `.env` local
3. Update GitHub Secrets
4. Update production environment
5. Restart bot

### 7.3. Least Privilege (Quyền tối thiểu)

**Discord Bot Permissions:**
- Chỉ cấp quyền cần thiết
- KHÔNG cần Administrator
- Permissions cần:
  - Send Messages
  - Read Message History
  - Add Reactions
  - Embed Links

**OAuth2 URL Generator:**
```
https://discord.com/developers/applications/YOUR_APP_ID/oauth2/url-generator

Scopes: bot
Permissions: Chọn quyền cần thiết
```

### 7.4. Monitoring

**Log suspicious activities:**

```python
import logging

logger = logging.getLogger(__name__)

def read_bot_token() -> Optional[str]:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        logger.info("✅ Token loaded from environment variable")
        return token.strip()
    
    # If falling back to file
    if os.path.exists(token_file):
        logger.warning(f"⚠️ Token loaded from file: {token_file}")
        logger.warning("⚠️ This is insecure! Use environment variables.")
        # ... existing code ...
```

---

## 📋 CHECKLIST BẢO MẬT

### Immediate Actions (Ngay lập tức)
- [ ] Reset Discord bot token
- [ ] Update token mới vào `.env`
- [ ] Test bot hoạt động với token mới
- [ ] Xóa `token.txt` khỏi working directory

### Git Cleanup (Trong 24h)
- [ ] Xóa `token.txt` khỏi Git history
- [ ] Force push repository
- [ ] Thông báo team re-clone
- [ ] Verify token.txt không còn trong Git

### Code Updates (Trong 1 tuần)
- [ ] Cài đặt python-dotenv
- [ ] Update `app/bot.py` để load từ `.env`
- [ ] Update `.gitignore`
- [ ] Thêm `.env.example` template
- [ ] Update documentation

### Production Setup (Khi deploy)
- [ ] Setup GitHub Secrets
- [ ] Update Docker configs
- [ ] Test deployment
- [ ] Setup monitoring/alerts
- [ ] Document emergency procedures

### Long-term (Ongoing)
- [ ] Pre-commit hooks
- [ ] Token rotation schedule (3-6 tháng)
- [ ] Security audit quarterly
- [ ] Team training về security

---

## 🆘 KHI GẶP SỰ CỐ

### Token bị compromise (nghi ngờ bị hack)

1. **Ngay lập tức:**
   - Reset token trên Discord Portal
   - Revoke tất cả OAuth2 authorizations
   - Check bot activity logs

2. **Điều tra:**
   - Xem Git history: `git log --all --full-history -- token.txt`
   - Check GitHub Security Alerts
   - Review Discord audit logs

3. **Phục hồi:**
   - Tạo token mới
   - Update tất cả environments
   - Monitor bot activity 24-48h

### Bot không start sau khi update

```powershell
# Debug steps
# 1. Check .env file exists
Test-Path .env

# 2. Check .env content (safe way)
Get-Content .env | Select-String -Pattern "DISCORD_BOT_TOKEN"
# Should show: DISCORD_BOT_TOKEN=MTIzNDU...

# 3. Test loading env vars
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Token loaded:', bool(os.getenv('DISCORD_BOT_TOKEN')))"

# 4. Run bot with debug
python app/bot.py
```

---

## 📚 TÀI LIỆU THAM KHẢO

- **Discord Developer Portal**: https://discord.com/developers/docs
- **python-dotenv**: https://pypi.org/project/python-dotenv/
- **git-filter-repo**: https://github.com/newren/git-filter-repo
- **GitHub Secrets**: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **OWASP Secrets Management**: https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password

---

## ❓ FAQ

**Q: Tôi có cần xóa repository và tạo lại không?**  
A: KHÔNG CẦN! Sử dung `git filter-repo` để xóa khỏi history an toàn hơn.

**Q: Token cũ có thể dùng được không?**  
A: KHÔNG! Sau khi reset, token cũ VÔ HIỆU HÓA ngay lập tức.

**Q: File `.env` có nên commit không?**  
A: TUYỆT ĐỐI KHÔNG! Chỉ commit `.env.example` (không chứa giá trị thật).

**Q: Làm sao biết token đã bị leak chưa?**  
A: Check GitHub Security Alerts, search Google: `"your-token-here"` (đừng làm điều này với token thật!)

**Q: Local dev có cần `.env` không?**  
A: CÓ! Mỗi developer cần có `.env` riêng, không share.

---

**🔐 An toàn là ưu tiên hàng đầu! Đừng bao giờ commit secrets vào Git!**

---

*Tài liệu cập nhật: 2025-01-14*  
*Phiên bản: 1.0*

