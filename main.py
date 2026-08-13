import os
import random
import string
import requests
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH TOKEN ---
TELEGRAM_BOT_TOKEN = "8880267204:AAG4JJRziEY5e66yzI2pas305ZX3rQCHEh8"
LAYMA_TOKEN = "90a4fd0df685bd1dbb09e1455feb7609"

# Lưu trữ Key tạm thời
VALID_KEYS = set()

# --- KHỞI TẠO FLASK ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lấy Key Xác Nhận</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }
        .container { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        h2 { color: #38bdf8; }
        .key-box { background: #0f172a; border: 2px dashed #38bdf8; padding: 15px; font-size: 22px; font-weight: bold; color: #4ade80; margin: 20px 0; border-radius: 8px; word-break: break-all; }
        p { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Xác Nhận Vượt Link Thành Công!</h2>
        <p>Sao chép mã (Key) bên dưới và dán lại vào Bot Telegram để nhận file config:</p>
        <div class="key-box">{{ key }}</div>
        <p><i>Bạn có thể tắt trang này và quay lại Telegram.</i></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    VALID_KEYS.add(key)
    return render_template_string(HTML_TEMPLATE, key=key)


# --- HÀM RÚT GỌN LINK BẰNG LAYMA ---
def create_layma_link(target_url):
    try:
        api_url = f"https://api.layma.net/api/admin/shortlink/quicklink?tokenValue={LAYMA_TOKEN}&mat=json&url={target_url}"
        response = requests.get(api_url, timeout=10)
        
        # In kết quả thô ra log Render để kiểm tra nếu có lỗi
        print(f"Phản hồi từ Layma: {response.text}")
        
        data = response.json()
        if isinstance(data, dict):
            # Lấy các trường dữ liệu phổ biến trả về link rút gọn
            short_url = data.get("shortUrl") or data.get("url") or data.get("html") or data.get("link")
            if short_url and str(short_url).startswith("http"):
                return short_url
    except Exception as e:
        print(f"Lỗi kết nối Layma: {e}")
    
    return target_url


# --- CÁC LỆNH CỦA BOT TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔗 Lấy File Config (Vượt Link)", callback_data="get_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Chào bạn! Hãy bấm nút bên dưới để vượt link lấy mã xác nhận nhận file config:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_link":
        render_domain = "https://bot-link-vuot.onrender.com"
        
        # Gọi API Layma
        short_url = create_layma_link(render_domain)

        keyboard = [
            [InlineKeyboardButton("🌐 Vượt Link Nhận Key", url=short_url)],
            [InlineKeyboardButton("🔑 Nhập Key Xác Nhận", callback_data="input_key")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Vui lòng bấm vào nút bên dưới để vượt link và lấy mã Key:",
            reply_markup=reply_markup
        )

    elif query.data == "input_key":
        await query.edit_message_text(
            text="Hãy gửi mã Key bạn vừa lấy được từ trang web vào khung chat này để bot kiểm tra nhé!"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    if user_text in VALID_KEYS:
        VALID_KEYS.remove(user_text)
        await update.message.reply_text(
            "✅ Xác nhận thành công! Dưới đây là file config của bạn:\n\n📂 `[Đường dẫn hoặc nội dung file config của bạn ở đây]`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Mã Key không hợp lệ hoặc đã được sử dụng. Vui lòng lấy link mới!")


# --- HÀM CHẠY ĐỒNG THỜI BOT VÀ WEB ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def main():
    import threading
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot đang chạy...")
    application.run_polling()

if __name__ == "__main__":
    main()
