import os
import random
import string
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH API & ID ---
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
        USER_DB[user_id] = {
            "balance": 1000.0, 
            "links_today": 0, 
            "last_link_date": now, 
            "bank_info": None, 
            "farm": {"seed_id": None, "plant_time": None, "ripe_time": None, "steal_time": None}
        }
    if USER_DB[user_id]["last_link_date"] != now:
        USER_DB[user_id]["links_today"] = 0
        USER_DB[user_id]["last_link_date"] = now
    return USER_DB[user_id]

def get_main_menu(balance):
    keyboard = [
        [InlineKeyboardButton("💣 Dò Mìn 3x3", callback_data="play_mine"), InlineKeyboardButton("🌾 Nông trại TK", callback_data="play_farm")],
        [InlineKeyboardButton("🔗 Vượt link kiếm tiền (500đ/link)", callback_data="get_earn_link")],
        [InlineKeyboardButton("💸 Rút tiền", callback_data="withdraw_menu")],
        [InlineKeyboardButton("🏦 Liên kết ngân hàng", callback_data="link_bank")],
        [InlineKeyboardButton(f"💵 Số dư: {balance:,.0f} VNĐ", callback_data="balance_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    text = "🤖 **Hệ thống TK Kim Kiếm đã sẵn sàng!**\nChọn tính năng bên dưới:"
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    if data == "menu":
        await start(update, context)

    elif data == "withdraw_menu":
        if not user["bank_info"]:
            await query.answer("❌ Bạn chưa liên kết tài khoản ngân hàng!", show_alert=True)
            return
        context.user_data["waiting_for_withdraw"] = True
        await query.edit_message_text(
            text=f"💸 **RÚT TIỀN**\n🏦 TK: `{user['bank_info']}`\n⚠️ *Cảnh báo: Sai thông tin sẽ không được hoàn trả!*\n\nNhập số tiền cần rút:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    elif data == "link_bank":
        context.user_data["waiting_for_bank"] = True
        await query.edit_message_text(
            text="🏦 **Liên kết ngân hàng**\nNhập theo cú pháp: `TênNH - SốTK - ChủTK`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    elif data == "get_earn_link":
        domain = "https://bot-link-vuot.onrender.com/earn"
        keyboard = [
            [InlineKeyboardButton("🌐 Mở Link Nhận Mã", url=domain)],
            [InlineKeyboardButton("🔑 Nhập Mã", callback_data="input_earn_code")],
            [InlineKeyboardButton("« Quay lại", callback_data="menu")]
        ]
        await query.edit_message_text("🔗 Bấm vào link để vượt và lấy mã dán vào bot:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "input_earn_code":
        context.user_data["waiting_for_code"] = True
        await query.edit_message_text("✍️ Gửi mã code vào khung chat:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại", callback_data="menu")]]))

    # --- DÒ MÌN 3x3 ---
    elif data == "play_mine":
        await query.edit_message_text(
            "💣 **Dò Mìn · Chọn mức cược:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cược 200đ", callback_data="mine_bet_200"), InlineKeyboardButton("Cược 500đ", callback_data="mine_bet_500")],
                [InlineKeyboardButton("Cược 1,000đ", callback_data="mine_bet_1000"), InlineKeyboardButton("Cược 2,000đ", callback_data="mine_bet_2000")],
                [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
            ])
        )

    elif data.startswith("mine_bet_"):
        bet = int(data.split("_")[2])
        if user["balance"] < bet:
            await query.answer("❌ Số dư không đủ!", show_alert=True)
            return
        user["balance"] -= bet
        user["mine_game"] = {"bet": bet, "opened": 0, "multiplier": 1.0, "grid": ["?"] * 9}
        
        kb = [
            [InlineKeyboardButton("❓", callback_data="mine_pick_0"), InlineKeyboardButton("❓", callback_data="mine_pick_1"), InlineKeyboardButton("❓", callback_data="mine_pick_2")],
            [InlineKeyboardButton("❓", callback_data="mine_pick_3"), InlineKeyboardButton("❓", callback_data="mine_pick_4"), InlineKeyboardButton("❓", callback_data="mine_pick_5")],
            [InlineKeyboardButton("❓", callback_data="mine_pick_6"), InlineKeyboardButton("❓", callback_data="mine_pick_7"), InlineKeyboardButton("❓", callback_data="mine_pick_8")],
            [InlineKeyboardButton("« Thoát", callback_data="play_mine")]
        ]
        await query.edit_message_text(
            f"💣 **Dò Mìn · Đang chơi**\n🪙 Cược: **{bet}đ**\nĐã mở: **0 / 8 💎**\nHệ số: **1.0x**",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )

    elif data.startswith("mine_pick_"):
        if "mine_game" not in user:
            await query.answer("Ván chơi đã kết thúc!", show_alert=True)
            return
        idx = int(data.split("_")[2])
        game = user["mine_game"]
        if game["grid"][idx] != "?":
            await query.answer("Ô này đã mở rồi!", show_alert=True)
            return

        # Logic VIP (ID 8880267204 tuyệt đối không nổ mìn)
        is_exploded = False if user_id == ADMIN_VIP_ID else (random.random() < 0.25)

        if is_exploded:
            game["grid"][idx] = "💥"
            del user["mine_game"]
            kb = [
                [InlineKeyboardButton(game["grid"][0], callback_data="none"), InlineKeyboardButton(game["grid"][1], callback_data="none"), InlineKeyboardButton(game["grid"][2], callback_data="none")],
                [InlineKeyboardButton(game["grid"][3], callback_data="none"), InlineKeyboardButton(game["grid"][4], callback_data="none"), InlineKeyboardButton(game["grid"][5], callback_data="none")],
                [InlineKeyboardButton(game["grid"][6], callback_data="none"), InlineKeyboardButton(game["grid"][7], callback_data="none"), InlineKeyboardButton(game["grid"][8], callback_data="none")],
                [InlineKeyboardButton("🔄 Chơi lại", callback_data="play_mine"), InlineKeyboardButton("🏠 Menu", callback_data="menu")]
            ]
            await query.edit_message_text(f"💥 **Trúng mìn! Bạn đã thua.**\nSố dư: {user['balance']:,.0f}đ", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            game["opened"] += 1
            game["multiplier"] = round(game["multiplier"] * 1.5, 2)
            game["grid"][idx] = "💎"
            prize = int(game["bet"] * game["multiplier"])

            if game["opened"] >= 8:
                user["balance"] += prize
                del user["mine_game"]
                await query.edit_message_text(f"🏆 **Thắng lớn! Vượt 8 ô kim cương nhận +{prize}đ**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]))
            else:
                kb = [
                    [InlineKeyboardButton(game["grid"][0], callback_data="mine_pick_0"), InlineKeyboardButton(game["grid"][1], callback_data="mine_pick_1"), InlineKeyboardButton(game["grid"][2], callback_data="mine_pick_2")],
                    [InlineKeyboardButton(game["grid"][3], callback_data="mine_pick_3"), InlineKeyboardButton(game["grid"][4], callback_data="mine_pick_4"), InlineKeyboardButton(game["grid"][5], callback_data="mine_pick_5")],
                    [InlineKeyboardButton(game["grid"][6], callback_data="mine_pick_6"), InlineKeyboardButton(game["grid"][7], callback_data="mine_pick_7"), InlineKeyboardButton(game["grid"][8], callback_data="mine_pick_8")],
                    [InlineKeyboardButton(f"💰 Rút ngay ({prize}đ)", callback_data="mine_cashout")],
                    [InlineKeyboardButton("« Thoát", callback_data="play_mine")]
                ]
                await query.edit_message_text(
                    f"💣 **Dò Mìn · Đang chơi**\nĐã mở: **{game['opened']}/8 💎**\nHệ số: **{game['multiplier']}x**\nRút được: **{prize}đ**",
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
                )

    elif data == "mine_cashout":
        if "mine_game" not in user:
            return
        prize = int(user["mine_game"]["bet"] * user["mine_game"]["multiplier"])
        user["balance"] += prize
        del user["mine_game"]
        await query.edit_message_text(f"🎉 **Rút tiền thành công!** +{prize}đ\nSố dư: {user['balance']:,.0f}đ", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

    elif data in ["none", "balance_info", "invite", "jackpot"]:
        await query.answer("Tính năng đang hoạt động!", show_alert=False)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_withdraw"):
        context.user_data["waiting_for_withdraw"] = False
        try:
            amt = float(text.replace(",", "").replace(".", ""))
            if amt <= 0 or user["balance"] < amt:
                raise ValueError()
            user["balance"] -= amt
            await update.message.reply_text(f"✅ Đã tạo lệnh rút {amt:,.0f}đ về TK `{user['bank_info']}`", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ Số tiền không hợp lệ hoặc vượt quá số dư!", reply_markup=get_main_menu(user["balance"]))
        return

    if context.user_data.get("waiting_for_code"):
        context.user_data["waiting_for_code"] = False
        if text.lower() == "dungvip12":
            user["balance"] += 300
            await update.message.reply_text("👑 Nhập mã VIP thành công! +300đ", reply_markup=get_main_menu(user["balance"]))
        elif text in VALID_LINKS:
            del VALID_LINKS[text]
            user["balance"] += 500
            user["links_today"] += 1
            await update.message.reply_text("✅ Nhận thưởng 500đ thành công!", reply_markup=get_main_menu(user["balance"]))
        else:
            await update.message.reply_text("❌ Mã không hợp lệ!", reply_markup=get_main_menu(user["balance"]))
        return

    if context.user_data.get("waiting_for_bank"):
        context.user_data["waiting_for_bank"] = False
        user["bank_info"] = text
        await update.message.reply_text(f"✅ Đã lưu ngân hàng: `{text}`", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
        return

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
    
