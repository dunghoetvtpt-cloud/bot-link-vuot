import os
import random
import string
import requests
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH TOKEN ---
TELEGRAM_BOT_TOKEN = "8880267204:AAG4JJRziEY5e66yzI2pas305ZX3rQCHEh8"
LINK4M_API_TOKEN = "68a76c1354de3f0da567ca17"

VALID_KEYS = set()

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

# --- HÀM RÚT GỌN LINK BẰNG LINK4M V2 ---
def create_link4m_link(target_url):
    try:
        # Sử dụng đúng chuẩn API v2 của Link4m mà bạn cung cấp
        api_url = f"https://link4m.co/api-shorten/v2?api={LINK4M_API_TOKEN}&url={target_url}"
        response = requests.get(api_url, timeout=10)
        data = response.json()
        
        # Kiểm tra kết quả trả về theo đúng chuẩn v2
        if data.get("status") == "success":
            short_url = data.get("shortenedUrl")
            if short_url:
                return short_url
        else:
            print(f"Lỗi từ API Link4m: {data.get('message')}")
    except Exception as e:
        print(f"Lỗi kết nối Link4m: {e}")
    
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
        
        # Gọi API tạo link rút gọn Link4m v2
        short_url = create_link4m_link(render_domain)

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
    
