# ⚠️ CẢNH BÁO BẢO MẬT / SECURITY ALERT

## 🚨 Discord Bot Token Đã Bị Lộ / Token Exposed

**Phát hiện ngày**: 28/11/2025  
**Mức độ**: 🔴 NGHIÊM TRỌNG / CRITICAL

### Vấn đề / Issue

Discord bot token đã bị commit vào file `.env.example` trong các commit trước đó:

```
Token bị lộ: YOUR_OLD_TOKEN_HERE (token đã bị hủy)
```

### ✅ Đã Sửa / Fixed

- [x] Xóa token khỏi `.env.example`
- [x] Thay thế bằng placeholder `YOUR_DISCORD_BOT_TOKEN_HERE`
- [x] Xác nhận `.env` đã nằm trong `.gitignore`

### 🔒 Hành Động Cần Làm NGAY / Immediate Actions Required

**BẠN PHẢI THỰC HIỆN CÁC BƯỚC SAU ĐỂ BẢO VỆ BOT:**

1. **Reset Discord Bot Token** (BẮT BUỘC):
   - Truy cập: https://discord.com/developers/applications
   - Chọn application của bạn
   - Vào **Bot** tab
   - Click **Reset Token** 
   - Copy token mới (CHỈ HIỂN THỊ MỘT LẦN!)

2. **Cập nhật Token Mới**:
   ```bash
   # Tạo file .env từ template
   cp .env.example .env
   
   # Mở .env và điền token MỚI
   notepad .env
   ```
   
   Trong file `.env`:
   ```env
   DISCORD_BOT_TOKEN=TOKEN_MỚI_CỦA_BẠN_Ở_ĐÂY
   ```

3. **Xác nhận .env KHÔNG được commit**:
   ```bash
   git status
   # .env KHÔNG được xuất hiện trong danh sách changed files
   ```

4. **Xóa token cũ khỏi Git history** (nếu đã push lên GitHub):
   ```bash
   # Cảnh báo: Thao tác này sẽ rewrite history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env.example" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push (CHỈ nếu bạn chắc chắn)
   git push origin --force --all
   ```

### 🛡️ Phòng Ngừa Trong Tương Lai / Prevention

1. **KHÔNG BAO GIỜ** commit token vào bất kỳ file nào
2. **LUÔN LUÔN** sử dụng `.env` cho sensitive data
3. **KIỂM TRA KỸ** trước khi commit: `git diff`
4. **SỬ DỤNG** pre-commit hooks để detect secrets

### 📚 Tài Liệu Tham Khảo

- [docs/HUONG_DAN_BAO_MAT_TOKEN.md](docs/HUONG_DAN_BAO_MAT_TOKEN.md) - Hướng dẫn chi tiết về bảo mật token
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Quy tắc bảo mật cho AI coding agents

### ✅ Checklist

- [ ] Đã reset Discord bot token
- [ ] Đã cập nhật token mới vào `.env`
- [ ] Đã verify `.env` không bị track bởi Git
- [ ] Bot hoạt động bình thường với token mới
- [ ] Đã xóa file `SECURITY_ALERT.md` này sau khi hoàn tất

---

**Lưu ý**: Sau khi hoàn tất tất cả các bước, bạn có thể xóa file này.
