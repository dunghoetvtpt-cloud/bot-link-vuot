import os
import random
import string
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH API & MẬT KHẨU KÍCH HOẠT VIP QUA LINK ---
TELEGRAM_BOT_TOKEN = "8824407353:AAF-mYCW6kSq-9ixD4ce42W5SpXV2D4t9n8"
LINK4M_API_TOKEN = "68a76c1354de3f0da567ca17"
ADMIN_VIP_ID = 8726403940  # ID Admin chính của bạn để dùng lệnh bật/tắt bot
VIP_ACTIVATION_SECRET = "kichhoatvip999"  # Mã bật/tắt trạng thái VIP qua link

USER_DB = {}
VALID_LINKS = {}
BOT_STATUS = {"is_active": True}  # Trạng thái bật/tắt bot (True: Hoạt động, False: Đang tắt/bảo trì)

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
            "balance": 0.0, 
            "is_vip": False, 
            "links_today": 0, 
            "last_link_date": now, 
            "bank_info": None, 
            "bank_changes_left": 3, 
            "farm": {"seed_id": None, "plant_time": None, "ripe_time": None, "steal_time": None}
        }
    if USER_DB[user_id]["last_link_date"] != now:
        USER_DB[user_id]["links_today"] = 0
        USER_DB[user_id]["last_link_date"] = now
    return USER_DB[user_id]

def get_main_menu(balance):
    keyboard = [
        [InlineKeyboardButton("💣 Dò Mìn 3x3", callback_data="play_mine"), InlineKeyboardButton("🌾 Nông trại TK", callback_data="play_farm")],
        [InlineKeyboardButton("👛 Ví của tôi", callback_data="my_wallet")],
        [InlineKeyboardButton("🔗 Vượt link kiếm tiền (500đ/link)", callback_data="get_earn_link")],
        [InlineKeyboardButton(f"💵 Số dư: {balance:,.0f} VNĐ", callback_data="balance_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- CÁC LỆNH BẬT / TẮT BOT DÀNH CHO ADMIN ---
async def offbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_VIP_ID:
        return
    BOT_STATUS["is_active"] = False
    await update.message.reply_text("🔴 **Đã TẮT (Off) bot thành công!** Bot tạm thời không tiếp nhận yêu cầu từ người dùng.", parse_mode="Markdown")

async def onbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_VIP_ID:
        return
    BOT_STATUS["is_active"] = True
    await update.message.reply_text("🟢 **Đã BẬT (On) bot thành công!** Hệ thống hoạt động bình thường trở lại.", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Nếu bot đang tắt và người dùng không phải Admin thì chặn
    if not BOT_STATUS["is_active"] and user_id != ADMIN_VIP_ID:
        if update.message:
            await update.message.reply_text("🛠️ **Hệ thống đang bảo trì tạm thời!** Vui lòng quay lại sau.", parse_mode="Markdown")
        return

    user = get_user(user_id)
    text = "🤖 **Hệ thống TK Kim Kiếm đã sẵn sàng!**\nChọn tính năng bên dưới:"
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not BOT_STATUS["is_active"] and user_id != ADMIN_VIP_ID:
        await update.callback_query.answer("🛠️ Hệ thống đang bảo trì!", show_alert=True)
        return

    query = update.callback_query
    await query.answer()
    user = get_user(user_id)
    data = query.data

    if data == "menu":
        await start(update, context)

    # --- QUẢN LÝ VÍ & NGÂN HÀNG ---
    elif data == "my_wallet":
        bank_text = f"`{user['bank_info']}`" if user["bank_info"] else "Chưa liên kết"
        vip_status = "👑 Đang bật (Bất tử)" if user["is_vip"] else "🔒 Thường"
        text = (
            f"👛 **QUẢN LÝ VÍ CỦA TÔI**\n\n"
            f"💵 Số dư: **{user['balance']:,.0f} VNĐ**\n"
            f"👑 Trạng thái VIP: **{vip_status}**\n"
            f"🏦 Tài khoản ngân hàng: {bank_text}\n"
            f"🔄 Số lần đổi ngân hàng còn lại: **{user['bank_changes_left']}/3**\n\n"
            f"⚠️ *Lưu ý: Tối thiểu rút 100.000đ và chỉ đổi ngân hàng tối đa 3 lần.*"
        )
        kb = [
            [InlineKeyboardButton("🔗 Liên kết / Đổi ngân hàng", callback_data="link_bank_prompt")],
            [InlineKeyboardButton("💸 Rút tiền", callback_data="withdraw_menu")],
            [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "link_bank_prompt":
        if user["bank_changes_left"] <= 0:
            await query.answer("❌ Bạn đã hết lượt đổi ngân hàng (tối đa 3 lần)!", show_alert=True)
            return
        context.user_data["waiting_for_bank"] = True
        await query.edit_message_text(
            text=f"🏦 **LIÊN KẾT / ĐỔI NGÂN HÀNG**\n\n"
                 f"Số lần đổi còn lại: **{user['bank_changes_left']}**\n\n"
                 f"Vui lòng nhập thông tin theo cú pháp:\n`TênNgânHàng - SốTàiKhoản - TênNgườiNhận`\n\n"
                 f"*(Ví dụ: Vietcombank - 10672819 - NGUYEN BAO YEN)*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại Ví", callback_data="my_wallet")]]),
            parse_mode="Markdown"
        )

    elif data == "withdraw_menu":
        if not user["bank_info"]:
            await query.answer("❌ Bạn chưa liên kết tài khoản ngân hàng trong mục 'Ví của tôi'!", show_alert=True)
            return
        context.user_data["waiting_for_withdraw"] = True
        await query.edit_message_text(
            text=f"💸 **RÚT TIỀN**\n🏦 TK nhận: `{user['bank_info']}`\n⚠️ *Tối thiểu rút: **100.000 VNĐ***\n\nNhập số tiền cần rút:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại Ví", callback_data="my_wallet")]]),
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
                [InlineKeyboardButton("Cược 10,000đ", callback_data="mine_bet_10000"), InlineKeyboardButton("Cược 20,000đ", callback_data="mine_bet_20000")],
                [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
            ])
        )

    elif data.startswith("mine_bet_"):
        bet = int(data.split("_")[2])
        if user["balance"] < bet:
            await query.answer("❌ Số dư không đủ! Hãy đi kiếm tiền trước nhé.", show_alert=True)
            return
        user["balance"] -= bet
        
        safe_count = random.randint(3, 5)
        user["mine_game"] = {
            "bet": bet, 
            "opened": 0, 
            "multiplier": 1.0, 
            "grid": ["?"] * 9,
            "safe_clicks_left": safe_count
        }
        
        kb = [
            [InlineKeyboardButton("❓", callback_data="mine_pick_0"), InlineKeyboardButton("❓", callback_data="mine_pick_1"), InlineKeyboardButton("❓", callback_data="mine_pick_2")],
            [InlineKeyboardButton("❓", callback_data="mine_pick_3"), InlineKeyboardButton("❓", callback_data="mine_pick_4"), InlineKeyboardButton("❓", callback_data="mine_pick_5")],
            [InlineKeyboardButton("❓", callback_data="mine_pick_6"), InlineKeyboardButton("❓", callback_data="mine_pick_7"), InlineKeyboardButton("❓", callback_data="mine_pick_8")],
            [InlineKeyboardButton("« Thoát", callback_data="play_mine")]
        ]
        await query.edit_message_text(
            f"💣 **Dò Mìn · Đang chơi**\n🪙 Cược: **{bet:,.0f}đ**\nĐã mở: **0 / 8 💎**\nHệ số: **1.0x**",
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

        if user["is_vip"]:
            is_exploded = False 
        else:
            if game["safe_clicks_left"] > 0:
                game["safe_clicks_left"] -= 1
                is_exploded = False
            else:
                if game["opened"] == 7:  
                    is_exploded = (random.random() < 0.999)
                else:
                    is_exploded = (random.randint(1, 8) == 1)

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
                await query.edit_message_text(f"🏆 **Thắng lớn! Vượt 8 ô kim cương nhận +{prize:,.0f}đ**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]))
            else:
                kb = [
                    [InlineKeyboardButton(game["grid"][0], callback_data="mine_pick_0"), InlineKeyboardButton(game["grid"][1], callback_data="mine_pick_1"), InlineKeyboardButton(game["grid"][2], callback_data="mine_pick_2")],
                    [InlineKeyboardButton(game["grid"][3], callback_data="mine_pick_3"), InlineKeyboardButton(game["grid"][4], callback_data="mine_pick_4"), InlineKeyboardButton(game["grid"][5], callback_data="mine_pick_5")],
                    [InlineKeyboardButton(game["grid"][6], callback_data="mine_pick_6"), InlineKeyboardButton(game["grid"][7], callback_data="mine_pick_7"), InlineKeyboardButton(game["grid"][8], callback_data="mine_pick_8")],
                    [InlineKeyboardButton(f"💰 Rút ngay ({prize:,.0f}đ)", callback_data="mine_cashout")],
                    [InlineKeyboardButton("« Thoát", callback_data="play_mine")]
                ]
                await query.edit_message_text(
                    f"💣 **Dò Mìn · Đang chơi**\nĐã mở: **{game['opened']}/8 💎**\nHệ số: **{game['multiplier']}x**\nRút được: **{prize:,.0f}đ**",
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
                )

    elif data == "mine_cashout":
        if "mine_game" not in user:
            return
        prize = int(user["mine_game"]["bet"] * user["mine_game"]["multiplier"])
        user["balance"] += prize
        del user["mine_game"]
        await query.edit_message_text(f"🎉 **Rút tiền thành công!** +{prize:,.0f}đ\nSố dư: {user['balance']:,.0f}đ", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

    elif data in ["none", "balance_info"]:
        await query.answer("Tính năng đang hoạt động!", show_alert=False)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not BOT_STATUS["is_active"] and user_id != ADMIN_VIP_ID:
        return

    user = get_user(user_id)
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_withdraw"):
        context.user_data["waiting_for_withdraw"] = False
        try:
            amt = float(text.replace(",", "").replace(".", ""))
            if amt < 100000:
                await update.message.reply_text("❌ Số tiền rút tối thiểu phải từ **100.000 VNĐ** trở lên!", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
                return
            if amt > user["balance"]:
                await update.message.reply_text("❌ Số tiền vượt quá số dư hiện có trong ví!", reply_markup=get_main_menu(user["balance"]))
                return
            
            user["balance"] -= amt
            await update.message.reply_text(
                f"✅ **Đã tạo lệnh rút thành công {amt:,.0f}đ!**\n"
                f"🏦 TK nhận: `{user['bank_info']}`\n\n"
                f"⏳ *Bạn có thể phải chờ khoảng 1-2 tuần để bên mình kiểm tra xem đúng số TK ko để xử lý lệnh rút.*", 
                reply_markup=get_main_menu(user["balance"]), 
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text("❌ Định dạng số tiền không hợp lệ!", reply_markup=get_main_menu(user["balance"]))
        return

    if context.user_data.get("waiting_for_code"):
        context.user_data["waiting_for_code"] = False
        
        # --- Bật/Tắt trạng thái VIP qua link ---
        if text == VIP_ACTIVATION_SECRET:
            user["is_vip"] = not user["is_vip"] 
            status_str = "KÍCH HOẠT THÀNH CÔNG (Bất tử)" if user["is_vip"] else "ĐÃ TẮT VIP"
            await update.message.reply_text(f"👑 Trạng thái VIP của bạn đã thay đổi: **{status_str}**", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
            return

        # --- Nâng giá trị mã dungvip12 lên 10.000đ ---
        if text.lower() == "dungvip12":
            user["balance"] += 10000
            await update.message.reply_text("👑 Nhập mã VIP `dungvip12` thành công! **+10.000 VNĐ**", reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
            return

        if text in VALID_LINKS:
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
        user["bank_changes_left"] -= 1  
        await update.message.reply_text(
            f"✅ **Đã liên kết ngân hàng thành công!**\n\n"
            f"🏦 Thông tin: `{text}`\n"
            f"🔄 Số lần đổi còn lại: {user['bank_changes_left']}/3",
            reply_markup=get_main_menu(user["balance"]),
            parse_mode="Markdown"
        )
        return

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Đăng ký các lệnh
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("offbot", offbot_command))
    application.add_handler(CommandHandler("onbot", onbot_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
        
