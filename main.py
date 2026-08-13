import os
import random
import string
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH API MỚI ---
TELEGRAM_BOT_TOKEN = "8824407353:AAF-mYCW6kSq-9ixD4ce42W5SpXV2D4t9n8"
LINK4M_API_TOKEN = "68a76c1354de3f0da567ca17"
ADMIN_VIP_ID = 8880267204  # ID VIP của bạn

USER_DB = {}
VALID_LINKS = {}

# --- CẤU HÌNH HẠT GIỐNG NÔNG TRẠI ---
SEEDS_CONFIG = {
    1: {"name": "🌱 Mầm Đậu Xanh", "cost": 30, "grow_minutes": 1, "steal_minutes": 10, "reward": 35},
    2: {"name": "🌽 Bắp Ngô Ngọt", "cost": 60, "grow_minutes": 3, "steal_minutes": 12, "reward": 70},
    3: {"name": "🥔 Khoai Tây Vàng", "cost": 120, "grow_minutes": 7, "steal_minutes": 15, "reward": 140},
    4: {"name": "🍓 Dâu Tây Đỏ", "cost": 250, "grow_minutes": 15, "steal_minutes": 18, "reward": 290},
    5: {"name": "🍎 Táo Vàng Thần Tài", "cost": 500, "grow_minutes": 30, "steal_minutes": 20, "reward": 580}
}

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Vượt Link Nhận Mã</title></head>
<body style="background:#0f172a; color:#fff; text-align:center; padding:50px; font-family:sans-serif;">
    <div style="background:#1e293b; padding:30px; border-radius:12px; display:inline-block;">
        <h2>Mã nhận thưởng</h2>
        <div style="background:#0f172a; border:2px dashed #38bdf8; padding:15px; font-size:24px; color:#4ade80;">{{ key }}</div>
    </div>
</body>
</html>
"""

@app.route('/earn')
def earn_page():
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    VALID_LINKS[key] = True
    return render_template_string(HTML_TEMPLATE, key=key)

def get_user(user_id):
    now = datetime.now().date()
    if user_id not in USER_DB:
        USER_DB[user_id] = {"balance": 1000.0, "links_today": 0, "last_link_date": now, "bank_info": None, "farm": {"seed_id": None, "plant_time": None, "ripe_time": None, "steal_time": None}}
    if USER_DB[user_id]["last_link_date"] != now:
        USER_DB[user_id]["links_today"] = 0
        USER_DB[user_id]["last_link_date"] = now
    return USER_DB[user_id]

def get_main_menu(balance):
    keyboard = [
        [InlineKeyboardButton("💣 Dò Mìn 3x3", callback_data="play_mine"), InlineKeyboardButton("🌾 Nông trại TK", callback_data="play_farm")],
        [InlineKeyboardButton("🔗 Vượt link (500đ/link)", callback_data="get_earn_link")],
        [InlineKeyboardButton("💸 Rút tiền", callback_data="withdraw_menu")],
        [InlineKeyboardButton(f"💵 Số dư: {balance:,.0f} VNĐ", callback_data="none")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text("🤖 **Hệ thống TK Kim Kiếm đã sẵn sàng!**", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    if data == "menu":
        await query.edit_message_text("🤖 **Quay về trang chủ**", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

    elif data == "play_mine":
        await query.edit_message_text(
            "💣 **Dò Mìn · Chọn mức cược:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("200đ", callback_data="mine_bet_200"), InlineKeyboardButton("500đ", callback_data="mine_bet_500")],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
            ])
        )

    elif data.startswith("mine_bet_"):
        bet = int(data.split("_")[2])
        user["balance"] -= bet
        user["mine_game"] = {"bet": bet, "opened": 0, "multiplier": 1.0, "grid": ["?"]*9}
        kb = [[InlineKeyboardButton("❓", callback_data=f"mine_pick_{i}") for i in range(3)], 
              [InlineKeyboardButton("❓", callback_data=f"mine_pick_{i+3}") for i in range(3)],
              [InlineKeyboardButton("❓", callback_data=f"mine_pick_{i+6}") for i in range(3)],
              [InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
        await query.edit_message_text(f"💣 **Đang chơi cược {bet}đ...**", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("mine_pick_"):
        idx = int(data.split("_")[2])
        game = user["mine_game"]
        # Logic VIP (Không trúng mìn)
        if user_id == ADMIN_VIP_ID or random.random() > 0.2:
            game["opened"] += 1
            game["multiplier"] *= 1.5
            game["grid"][idx] = "💎"
            kb = [[InlineKeyboardButton(game["grid"][i], callback_data="none") for i in range(3)],
                  [InlineKeyboardButton(game["grid"][i+3], callback_data="none") for i in range(3)],
                  [InlineKeyboardButton(game["grid"][i+6], callback_data="none") for i in range(3)],
                  [InlineKeyboardButton(f"Rút {int(game['bet']*game['multiplier'])}đ", callback_data="mine_cashout")]]
            await query.edit_message_text(f"Đã mở {game['opened']}/8 ô an toàn!", reply_markup=InlineKeyboardMarkup(kb))
        else:
            del user["mine_game"]
            await query.edit_message_text("💥 **BÙM! Bạn đã thua.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Chơi lại", callback_data="play_mine")]]))

    elif data == "mine_cashout":
        won = int(user["mine_game"]["bet"] * user["mine_game"]["multiplier"])
        user["balance"] += won
        del user["mine_game"]
        await query.edit_message_text(f"🎉 Rút thành công {won}đ!", reply_markup=get_main_menu(user["balance"]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    text = update.message.text.strip()
    if text.lower() == "dungvip12":
        user["balance"] += 300
        await update.message.reply_text("✅ Kích hoạt VIP thành công! +300đ.", reply_markup=get_main_menu(user["balance"]))

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.run_polling()
    
