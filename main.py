import os
import random
import string
import requests
from urllib.parse import quote
from flask import Flask, render_template_string, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'khoa_bi_mat_render_123'

# 2 Token Link4M của bạn
LINK4M_TOKENS = [
    "68a76c1354de3f0da567ca17",  # Token 1
    "6a7e4f3993203b217d199b6b"   # Token 2
]

# Database giả lập lưu trên RAM của Render (Số dư, mã hợp lệ)
USER_DATA = {
    "balance": 100.0,
    "links_today": 0
}
VALID_CODES = {} # Lưu các mã vượt link hợp lệ

# Giao diện Web chính (Có nút tạo link, hiển thị số dư và ô nhập mã)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Vượt Link Nhận Thưởng</title>
    <style>
        body { background:#0f172a; color:#fff; font-family:sans-serif; margin:0; padding:20px; display:flex; justify-content:center; }
        .container { width:100%; max-width:400px; background:#1e293b; padding:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.5); text-align:center; }
        h2 { color:#38bdf8; font-size:20px; }
        .balance { font-size:18px; color:#fbbf24; font-weight:bold; margin-bottom:15px; background:#0f172a; padding:10px; border-radius:8px; }
        button, input { width:100%; padding:12px; margin-top:10px; border-radius:8px; border:none; font-size:14px; box-sizing:border-box; }
        button { background:#0284c7; color:#fff; font-weight:bold; cursor:pointer; }
        button:hover { background:#0369a1; }
        input { background:#0f172a; color:#fff; border:1px solid #475569; text-align:center; }
        .result { margin-top:15px; background:#0f172a; padding:12px; border-radius:8px; border:1px dashed #38bdf8; word-break:break-all; font-size:13px; }
        .result a { color:#4ade80; font-weight:bold; text-decoration:none; }
        .msg { margin-top:10px; font-size:13px; font-weight:bold; }
    </style>
</head>
<body>
<div class="container">
    <h2>🚀 Tool Vượt Link Kiếm Tiền</h2>
    <div class="balance">💵 Số dư: {{ user.balance | format_money }} VNĐ</div>

    <!-- Thông báo kết quả (nếu có) -->
    {% if message %}
        <div class="msg" style="color: {{ '4ade80' if success else 'f87171' }};">{{ message }}</div>
    {% endif %}

    <!-- Nút tạo link rút gọn -->
    <form action="/tao-link" method="POST" style="margin-top:15px;">
        <button type="submit">🔗 Bấm Tạo Link Rút Gọn</button>
    </form>

    {% if short_url %}
        <div class="result">
            <span>Link rút gọn của bạn (Đã xoay vòng Token):</span><br><br>
            <a href="{{ short_url }}" target="_blank">{{ short_url }}</a>
        </div>
    {% endif %}

    <hr style="border:0; border-top:1px solid #334155; margin:20px 0;">

    <!-- Khung nhập mã nhận thưởng sau khi vượt link -->
    <h3 style="font-size:15px; color:#38bdf8;">🔑 Nhập Mã Nhận Thưởng</h3>
    <form action="/nhap-ma" method="POST">
        <input type="text" name="code" placeholder="Nhập mã bạn nhận được..." required>
        <button type="submit" style="background:#16a34a;">Xác Nhận Nhận Thưởng</button>
    </form>
</div>
</body>
</html>
"""

@app.template_filter('format_money')
def format_money(value):
    return f"{value:,.0f}"

@app.route('/')
def index():
    short_url = session.pop('last_short_url', None)
    message = session.pop('message', None)
    success = session.pop('success', True)
    return render_template_string(HTML_TEMPLATE, user=USER_DATA, short_url=short_url, message=message, success=success)

@app.route('/tao-link', methods=['POST'])
def tao_link():
    # 1. Tự động chọn ngẫu nhiên 1 trong 2 Token Link4M của bạn
    chosen_token = random.choice(LINK4M_TOKENS)
    
    # 2. Tạo một mã nhận thưởng ngẫu nhiên (Ví dụ: TK9X2A) cho lượt vượt link này
    earn_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Đưa mã này vào danh sách hợp lệ tạm thời
    VALID_CODES[earn_code] = False # Chưa được sử dụng
    
    # 3. Link đích khi người dùng vượt link xong sẽ nhảy về trang web của bạn kèm theo mã
    # (Render URL của chính app bạn + /nhan-thuong?code=...)
    base_url = request.host_url.rstrip('/')
    destination = f"{base_url}/trang-lay-ma?code={earn_code}"
    
    # Gọi API Link4M
    long_url = quote(destination, safe='')
    api_url = f"https://link4m.co/api-shorten/v2?api={chosen_token}&url={long_url}"
    
    try:
        res = requests.get(api_url, timeout=10).json()
        if res.get("status") == 'success':
            session['last_short_url'] = res.get("shortenedUrl")
            USER_DATA["links_today"] += 1
        else:
            session['message'] = "❌ Lỗi từ API Link4M: " + res.get("message", "Không rõ")
            session['success'] = False
    except Exception as e:
        session['message'] = "❌ Lỗi kết nối API!"
        session['success'] = False
        
    return redirect(url_for('index'))

# Trang mà người dùng nhìn thấy sau khi vượt link thành công
@app.route('/trang-lay-ma')
def trang_lay_ma():
    code = request.args.get('code', '')
    return f"""
    <body style="background:#0f172a; color:#fff; text-align:center; padding:50px; font-family:sans-serif;">
        <div style="background:#1e293b; padding:30px; border-radius:12px; display:inline-block; max-width:400px;">
            <h2 style="color:#4ade80;">🎉 Vượt Link Thành Công!</h2>
            <p style="color:#94a3b8; font-size:14px;">Mã nhận thưởng của bạn là:</p>
            <div style="background:#0f172a; border:2px dashed #38bdf8; padding:15px; font-size:22px; color:#fbbf24; margin: 15px 0; user-select:all;">{code}</div>
            <p style="color:#94a3b8; font-size:12px;">Hãy copy mã này, quay lại trang chính dán vào ô nhận thưởng để được cộng tiền nhé!</p>
            <a href="/" style="display:inline-block; margin-top:15px; padding:10px 20px; background:#0284c7; color:#fff; text-decoration:none; border-radius:6px; font-weight:bold;">Về Trang Chủ Nhập Mã</a>
        </div>
    </body>
    """

# Xử lý khi bấm nút nhận tiền bằng mã
@app.route('/nhap-ma', methods=['POST'])
def nhap_ma():
    input_code = request.form.get('code', '').strip().upper()
    
    if input_code in VALID_CODES:
        if not VALID_CODES[input_code]:
            VALID_CODES[input_code] = True # Đánh dấu mã đã dùng
            USER_DATA["balance"] += 500.0 # Cộng 500đ
            session['message'] = f"🎉 Nhận thưởng thành công! +500 VNĐ"
            session['success'] = True
        else:
            session['message'] = "⚠️ Mã này đã được sử dụng rồi!"
            session['success'] = False
    else:
        session['message'] = "❌ Mã không tồn tại hoặc không hợp lệ!"
        session['success'] = False
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
