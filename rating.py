import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types

DB_NAME = "users.db"
ADMIN_PHONE = "+998931981793"  # o'zingizning admin raqamingiz
ADMIN_SESSIONS = set()  # vaqtinchalik adminlar

# 🔹 DB bilan ishlash
def get_connection():
    return sqlite3.connect(DB_NAME)

def get_top_100():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, score
        FROM users
        WHERE score > 0
        ORDER BY score DESC
        LIMIT 100
    """)
    data = cursor.fetchall()
    conn.close()
    return data

def get_active_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, score
        FROM users
        WHERE score > 0
        ORDER BY score DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return data

def generate_rating_pdf(data, title="Reyting"):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y = 760
    pdf.setFont("Helvetica", 11)
    for i, (user_id, score) in enumerate(data, start=1):
        pdf.drawString(50, y, f"{i}. User ID: {user_id} | Ball: {score}")
        y -= 18
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800
    pdf.save()
    return file_name

# 🔹 Admin tekshirish
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS

# 🔹 Admin panel ko‘rsatish
def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol ishtirokchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("⬅️ Chiqish")
    bot.send_message(msg.chat.id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML")

# 🔹 Admin start (telefon orqali)
def admin_start(bot):
    @bot.message_handler(commands=["admin"])
    def admin_login(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = types.KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)
        kb.add(btn)
        bot.send_message(msg.chat.id, "🔐 Admin panelga kirish uchun telefon raqamingizni yuboring:", reply_markup=kb)

    @bot.message_handler(content_types=["contact"])
    def check_admin_contact(msg):
        phone = msg.contact.phone_number
        if phone.startswith("998"):
            phone = "+" + phone
        if phone == ADMIN_PHONE:
            ADMIN_SESSIONS.add(msg.from_user.id)
            show_admin_panel(bot, msg)
        else:
            bot.send_message(msg.chat.id, "❌ Siz admin emassiz")

# 🔹 Admin tugmalar handlerlari
def admin_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
    def top100(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_top_100()
        if not data:
            bot.send_message(msg.chat.id, "Reyting hali yo‘q")
            return
        text = "🏆 <b>TOP 100</b>\n\n"
        for i, (uid, score) in enumerate(data, 1):
            text += f"{i}. ID: <code>{uid}</code> — {score} ball\n"
        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "👥 Faol ishtirokchilar")
    def active_users(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_active_users()
        bot.send_message(msg.chat.id, f"👥 Faol foydalanuvchilar soni: {len(data)}")

    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def top_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_top_100()
        file = generate_rating_pdf(data, "Top 100 Reyting")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_active_users()
        file = generate_rating_pdf(data, "Faol ishtirokchilar")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def admin_exit(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi")
