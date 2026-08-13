import os
import random
import string
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH TOKEN & ID VIP CỦA BẠN ---
TELEGRAM_BOT_TOKEN = "8880267204:AAG4JJRziEY5e66yzI2pas305ZX3rQCHEh8"
LINK4M_API_TOKEN = "68a76c1354de3f0da567ca17"
ADMIN_VIP_ID = 8880267204  # ID Telegram của bạn đã được gắn cố định

USER_DB = {}
VALID_LINKS = {}

# --- CẤU HÌNH 5 LOẠI HẠT GIỐNG NÔNG TRẠI ---
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
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vượt Link Nhận Tiền</title>
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
        <h2>Vượt Link Thành Công!</h2>
        <p>Mã nhận thưởng của bạn (Sao chép mã này dán vào bot):</p>
        <div class="key-box">{{ key }}</div>
        <p><i>Mỗi ngày bạn được tối đa 2 link, mỗi link trị giá 500đ.</i></p>
    </div>
</body>
</html>
"""

@app.route('/earn')
def earn_page():
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    VALID_LINKS[key] = True
    return render_template_string(HTML_TEMPLATE, key=key)

def create_link4m_link(target_url):
    try:
        api_url = f"https://link4m.co/api-shorten/v2?api={LINK4M_API_TOKEN}&url={target_url}"
        response = requests.get(api_url, timeout=10)
        result = response.json()
        if result.get("status") == 'success':
            return result.get("shortenedUrl")
    except:
        pass
    return target_url

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
    else:
        if USER_DB[user_id]["last_link_date"] != now:
            USER_DB[user_id]["links_today"] = 0
            USER_DB[user_id]["last_link_date"] = now
    return USER_DB[user_id]

def get_main_menu(balance):
    keyboard = [
        [InlineKeyboardButton("💰 Mời & Kiếm tiền", callback_data="invite"), InlineKeyboardButton("💸 Rút tiền", callback_data="withdraw_menu")],
        [InlineKeyboardButton("📢 Kênh TK", url="https://t.me/"), InlineKeyboardButton("👥 CLB TK", url="https://t.me/")],
        [InlineKeyboardButton("🏆 Hũ Thưởng · Xem kết quả", callback_data="jackpot")],
        [InlineKeyboardButton("🔗 Vượt link kiếm tiền (500đ/link)", callback_data="get_earn_link")],
        [InlineKeyboardButton("🏦 Liên kết ngân hàng", callback_data="link_bank")],
        [InlineKeyboardButton("💣 Dò Mìn Vượt Ô", callback_data="play_mine"), InlineKeyboardButton("🌾 Nông trại TK", callback_data="play_farm")],
        [InlineKeyboardButton(f"💵 Số dư: {balance:,.0f} VNĐ", callback_data="balance_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    welcome_text = "🤖 **Chào mừng bạn đến với hệ thống TK Kim Kiếm!**\n\nChọn các chức năng bên dưới:"
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_menu(user["balance"]), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    if data == "menu":
        await start(update, context)

    # --- TÍNH NĂNG RÚT TIỀN VÀ CẢNH BÁO ---
    elif data == "withdraw_menu":
        if not user["bank_info"]:
            await query.answer("❌ Bạn chưa liên kết tài khoản ngân hàng!", show_alert=True)
            return
            
        context.user_data["waiting_for_withdraw"] = True
        await query.edit_message_text(
            text=f"💸 **HỆ THỐNG RÚT TIỀN**\n\n"
                 f"🏦 Ngân hàng nhận: `{user['bank_info']}`\n"
                 f"💵 Số dư hiện tại: **{user['balance']:,.0f} VNĐ**\n\n"
                 f"⚠️ **CẢNH BÁO:** Rút tiền về tài khoản ngân hàng đã liên kết. **Nếu thông tin không đúng sẽ không được hoàn trả!**\n\n"
                 f"Vui lòng nhập **số tiền cần rút** vào khung chat:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    elif data == "get_earn_link":
        if user["links_today"] >= 2:
            await query.message.reply_text("❌ Bạn đã đạt giới hạn vượt link tối đa (2/2 lần) trong ngày hôm nay rồi!")
            return
        
        domain = "https://bot-link-vuot.onrender.com/earn"
        short_url = create_link4m_link(domain)
        
        keyboard = [
            [InlineKeyboardButton("🌐 Mở Link Kiếm 500đ", url=short_url)],
            [InlineKeyboardButton("🔑 Nhập Mã Nhận Tiền", callback_data="input_earn_code")],
            [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
        ]
        await query.edit_message_text(
            text=f"🔗 **Vượt Link Kiếm Tiền** (Hôm nay đã làm: {user['links_today']}/2)\n\nBấm nút bên dưới để vượt link, lấy mã dán lại vào bot:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "input_earn_code":
        context.user_data["waiting_for_code"] = True
        await query.edit_message_text(
            text="✍️ Hãy gửi mã code bạn nhận được từ trang web (hoặc mã code đặc quyền) vào khung chat này:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]])
        )

    elif data == "link_bank":
        context.user_data["waiting_for_bank"] = True
        bank_status = f"Đã liên kết: `{user['bank_info']}`" if user["bank_info"] else "Chưa liên kết"
        await query.edit_message_text(
            text=f"🏦 **Liên kết ngân hàng**\nTrạng thái: {bank_status}\n\n"
                 f"⚠️ **Lưu ý quan trọng:** Hãy kiểm tra kỹ thông tin. Nếu sai sót, tiền rút đi sẽ không được hoàn trả!\n\n"
                 f"Vui lòng nhập thông tin theo cú pháp: `TênNgânHàng - SốTàiKhoản - ChủTàiKhoản`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]]),
            parse_mode="Markdown"
        )

    # --- DÒ MÌN VƯỢT Ô ---
    elif data == "play_mine":
        await query.edit_message_text(
            text=f"💣 **Trò chơi Dò Mìn Vượt Ô (9 Ô May Mắn)**\n"
                 f"Số dư hiện tại: **{user['balance']:,.0f} VNĐ**\n\n"
                 f"Hãy chọn mức cược khởi điểm của bạn:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cược 200đ", callback_data="mine_bet_200"), InlineKeyboardButton("Cược 500đ", callback_data="mine_bet_500")],
                [InlineKeyboardButton("Cược 1,000đ", callback_data="mine_bet_1000"), InlineKeyboardButton("Cược 2,000đ", callback_data="mine_bet_2000")],
                [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
            ]),
            parse_mode="Markdown"
        )

    elif data.startswith("mine_bet_"):
        bet_amount = int(data.split("_")[2])
        if user["balance"] < bet_amount:
            await query.answer(f"❌ Số dư không đủ {bet_amount}đ để cược!", show_alert=True)
            return

        user["balance"] -= bet_amount
        user["mine_game"] = {
            "bet": bet_amount,
            "step": 1,
            "current_prize": bet_amount * 2
        }

        keyboard = [
            [InlineKeyboardButton("🟦 Ô 1", callback_data="mine_pick_1"), InlineKeyboardButton("🟦 Ô 2", callback_data="mine_pick_2"), InlineKeyboardButton("🟦 Ô 3", callback_data="mine_pick_3")],
            [InlineKeyboardButton("🟦 Ô 4", callback_data="mine_pick_4"), InlineKeyboardButton("🟦 Ô 5", callback_data="mine_pick_5"), InlineKeyboardButton("🟦 Ô 6", callback_data="mine_pick_6")],
            [InlineKeyboardButton("🟦 Ô 7", callback_data="mine_pick_7"), InlineKeyboardButton("🟦 Ô 8", callback_data="mine_pick_8"), InlineKeyboardButton("🟦 Ô 9", callback_data="mine_pick_9")],
            [InlineKeyboardButton("💰 Dừng lại & Rút tiền ngay", callback_data="mine_cashout")],
            [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]
        ]
        
        await query.edit_message_text(
            text=f"💣 **Đang chơi Dò Mìn (Cược: {bet_amount:,}đ)**\n"
                 f"🎯 Bước hiện tại: **Ô số 1**\n"
                 f"💵 Tiền thưởng nếu qua ô này: **{user['mine_game']['current_prize']:,}đ**\n\n"
                 f"Hãy chọn 1 ô bất kỳ bên dưới:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("mine_pick_"):
        if "mine_game" not in user:
            await query.answer("❌ Ván chơi đã kết thúc, vui lòng bắt đầu lại!", show_alert=True)
            return

        game = user["mine_game"]
        step = game["step"]

        # BUFF TỶ LỆ THẮNG CHO ID VIP CỦA BẠN (8880267204)
        if user_id == ADMIN_VIP_ID:
            is_exploded = False
        else:
            explosion_chances = {1: 0.35, 2: 0.50, 3: 0.65, 4: 0.75, 5: 0.80}
            current_chance = explosion_chances.get(step, 0.85)
            is_exploded = random.random() < current_chance

        if is_exploded:
            bet_lost = game["bet"]
            del user["mine_game"]
            await query.edit_message_text(
                text=f"💥 **BÙM! ĐÃ DẪM PHẢI MÌN Ở BƯỚC {step}!**\nSố dư: **{user['balance']:,.0f} VNĐ**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Chơi Lại", callback_data="play_mine")], [InlineKeyboardButton("« Quay lại Menu", callback_data="menu")]])
            )
        else:
            game["step"] += 1
            old_prize = game["current_prize"]
            game["current_prize"] = int(old_prize * 1.6) 
            
            if game["step"] > 9:
                user["balance"] += old_prize
                won_amount = old_prize
                del user["mine_game"]
                await query.edit_message_text(
                    text=f"🏆 **THẦN KỲ! VƯỢT XUẤT SẮC CẢ 9 Ô AN TOÀN!**\nNhận: **+{won_amount:,} VNĐ**",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Về Menu", callback_data="menu")]])
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("🟦 Ô", callback_data="mine_pick_A"), InlineKeyboardButton("🟦 Ô", callback_data="mine_pick_B"), InlineKeyboardButton("🟦 Ô", callback_data="mine_pick_C")],
                    [InlineKeyboardButton("💰 Dừng lại & Rút tiền ngay ({:,}đ)".format(old_prize), callback_data="mine_cashout")],
                    [InlineKeyboardButton("« Thoát", callback_data="menu")]
                ]
                await query.edit_message_text(
                    text=f"✨ **An toàn! Đã vượt qua ô số {step}**\n"
                         f"🎯 Ô tiếp theo: **{game['step']} / 9**\n"
                         f"💵 Thưởng hiện tại: **{old_prize:,}đ**",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )

    elif data == "mine_cashout":
        if "mine_game" not in user:
            await query.answer("❌ Không có ván chơi nào đang diễn ra!", show_alert=True)
            return

        game = user["mine_game"]
        reward = int(game["current_prize"] / 1.6) 
        user["balance"] += reward
        del user["mine_game"]

        await query.edit_message_text(
            text=f"🎉 **Rút tiền thành công!** +{reward:,} VNĐ\nSố dư: **{user['balance']:,.0f} VNĐ**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💣 Chơi Lại", callback_data="play_mine")], [InlineKeyboardButton("« Về Menu", callback_data="menu")]])
        )

    # --- NÔNG TRẠI TK ---
    elif data == "play_farm":
        farm = user["farm"]
        now = datetime.now()
        text = f"🌾 **Nông Trại TK**\nSố dư: **{user['balance']:,.0f} VNĐ**\n\n"
        keyboard_rows = []

        if farm["seed_id"] is None:
            text += "Trạng thái: 🟫 Đất trống. Chọn hạt giống:"
            for s_id, s_info in SEEDS_CONFIG.items():
                keyboard_rows.append([InlineKeyboardButton(f"{s_info['name']} (Giá: {s_info['cost']}đ | Lãi: {s_info['reward']}đ)", callback_data=f"plant_{s_id}")])
        else:
            s_info = SEEDS_CONFIG[farm["seed_id"]]
            if now >= farm["ripe_time"]:
                if user_id != ADMIN_VIP_ID and now >= farm["steal_time"]:
                    farm["seed_id"] = None
                    text += "😢 Cây bị kẻ gian ăn trộm sạch do để quá giờ!"
                    keyboard_rows.append([InlineKeyboardButton("🌱 Trồng cây mới", callback_data="play_farm")])
                else:
                    text += f"✨ Cây **{s_info['name']}** đã chín!"
                    keyboard_rows.append([InlineKeyboardButton("🌾 Thu Hoạch Ngay", callback_data="harvest_farm")])
            else:
                remaining = int((farm["ripe_time"] - now).total_seconds())
                text += f"⏳ Đang trồng: **{s_info['name']}**\n🕒 Còn lại: **{remaining} giây**"
                keyboard_rows.append([InlineKeyboardButton("🔄 Làm mới", callback_data="play_farm")])

        keyboard_rows.append([InlineKeyboardButton("« Quay lại Menu", callback_data="menu")])
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard_rows), parse_mode="Markdown")

    elif data.startswith("plant_"):
        s_id = int(data.split("_")[1])
        s_info = SEEDS_CONFIG[s_id]
        if user["balance"] < s_info["cost"]:
            await query.answer("❌ Không đủ tiền mua hạt giống!", show_alert=True)
            return
            
        user["balance"] -= s_info["cost"]
        now = datetime.now()
        user["farm"]["seed_id"] = s_id
        user["farm"]["plant_time"] = now
        user["farm"]["ripe_time"] = now + timedelta(minutes=s_info["grow_minutes"])
        user["farm"]["steal_time"] = user["farm"]["ripe_time"] + timedelta(minutes=s_info["steal_minutes"])
        await query.answer(f"🌱 Đã gieo trồng {s_info['name']}!", show_alert=True)
        await button_handler(update, context)

    elif data == "harvest_farm":
        farm = user["farm"]
        now = datetime.now()
        if farm["seed_id"] is None:
            await query.answer("❌ Không có cây nào!", show_alert=True)
            return
            
        s_info = SEEDS_CONFIG[farm["seed_id"]]
        if user_id != ADMIN_VIP_ID and now >= farm["steal_time"]:
            text = "😢 Bị ăn trộm sạch!"
        elif now >= farm["ripe_time"]:
            reward = s_info["reward"]
            user["balance"] += reward
            text = f"🎉 Thu hoạch thành công! +{reward} VNĐ"
        else:
            text = "⏳ Cây chưa chín!"
            
        farm["seed_id"] = None
        await query.answer(text, show_alert=True)
        await button_handler(update, context)

    elif data in ["invite", "jackpot", "balance_info"]:
        await query.answer("Tính năng đang hoạt động bình thường!", show_alert=False)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text.strip()

    # --- XỬ LÝ NHẬP SỐ TIỀN RÚT ---
    if context.user_data.get("waiting_for_withdraw"):
        context.user_data["waiting_for_withdraw"] = False
        try:
            amount = float(text.replace(",", "").replace(".", ""))
            if amount <= 0:
                raise ValueError()
            if user["balance"] < amount:
                await update.message.reply_text("❌ Số dư của bạn không đủ để rút số tiền này!", reply_markup=get_main_menu(user["balance"]))
                return
                
            # Trừ tiền trong tài khoản
            user["balance"] -= amount
            await update.message.reply_text(
                f"✅ **Yêu cầu rút tiền đã được ghi nhận!**\n\n"
                f"💵 Số tiền rút: **{amount:,.0f} VNĐ**\n"
                f"🏦 Chuyển về TK: `{user['bank_info']}`\n"
                f"📉 Số dư còn lại: **{user['balance']:,.0f} VNĐ**\n\n"
                f"⏳ Hệ thống đang xử lý giao dịch của bạn.",
                reply_markup=get_main_menu(user["balance"]),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ Vui lòng nhập một con số hợp lệ (Ví dụ: 50000)", reply_markup=get_main_menu(user["balance"]))
        return

    # --- XỬ LÝ MÃ CODE VƯỢT LINK VÀ CODE VIP Dungvip12 ---
    if context.user_data.get("waiting_for_code"):
        context.user_data["waiting_for_code"] = False
        
        if text.lower() == "dungvip12":
            user["balance"] += 300
            await update.message.reply_text(
                f"👑 **Mã VIP Đặc Quyền Kích Hoạt Thành Công!**\n"
                f"Cộng +300 VNĐ vào tài khoản.\n"
                f"Số dư mới: **{user['balance']:,.0f} VNĐ**",
                reply_markup=get_main_menu(user["balance"]),
                parse_mode="Markdown"
            )
            return

        if text in VALID_LINKS:
            del VALID_LINKS[text]
            user["links_today"] += 1
            user["balance"] += 500
            await update.message.reply_text(
                f"✅ Nhận thưởng thành công! +500 VNĐ.\nSố dư: **{user['balance']:,.0f} VNĐ**",
                reply_markup=get_main_menu(user["balance"]),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Mã code không hợp lệ hoặc đã được sử dụng!", reply_markup=get_main_menu(user["balance"]))
        return

    if context.user_data.get("waiting_for_bank"):
        context.user_data["waiting_for_bank"] = False
        user["bank_info"] = text
        await update.message.reply_text(
            f"✅ Liên kết ngân hàng thành công:\n`{text}`",
            reply_markup=get_main_menu(user["balance"]),
            parse_mode="Markdown"
        )
        return

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def main():
    import threading
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    application = Application.builder().token(TELEG
