import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types

DB_NAME = "users.db"
ADMIN_PHONES = ["+998200050252", "+998908551141","+998931981793"]  # 2 ta admin raqam # O'zingizning admin raqamingiz
ADMIN_SESSIONS = set()


# 🔹 DB bilan ishlash
def get_connection():
    return sqlite3.connect(DB_NAME)


def get_top_100():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, score
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
        SELECT user_id, username, score
        FROM users
        WHERE score > 0
        ORDER BY score DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return data


# 🔹 PDF yaratish (oxirida jami ball)
def generate_rating_pdf(data, title="Reyting"):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = 760
    pdf.setFont("Helvetica", 11)
    total_score = 0

    for i, (user_id, username, score) in enumerate(data, start=1):
        pdf.drawString(50, y, f"{i}. ID: {user_id} | Username: {username} | Ball: {score}")
        y -= 18
        total_score += score
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800

    pdf.drawString(50, y-20, f"🟢 JAMI BALL: {total_score}")
    pdf.save()
    return file_name


# 🔹 Admin tekshirish
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS


# 🔹 Admin panel menyusi
def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol ishtirokchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("🔍 ID orqali username", "⬅️ Chiqish")
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
    # Top 100
    @bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
    def top100(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_top_100()
        if not data:
            bot.send_message(msg.chat.id, "Reyting hali yo‘q")
            return
        text = "🏆 <b>TOP 100</b>\n\n"
        for i, (uid, username, score) in enumerate(data, 1):
            text += f"{i}. ID: <code>{uid}</code> — {score} ball | Username: {username}\n"
        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # Faol foydalanuvchilar
    @bot.message_handler(func=lambda m: m.text == "👥 Faol ishtirokchilar")
    def active_users(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_active_users()
        bot.send_message(msg.chat.id, f"👥 Faol foydalanuvchilar soni: {len(data)}")

    # Top 100 PDF
    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def top_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_top_100()
        file = generate_rating_pdf(data, "Top 100 Reyting")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    # Faollar PDF
    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_active_users()
        file = generate_rating_pdf(data, "Faol ishtirokchilar")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    # ID orqali username
    @bot.message_handler(func=lambda m: m.text == "🔍 ID orqali username")
    def search_id(msg):
        if not is_admin(msg.from_user.id):
            return
        bot.send_message(msg.chat.id, "🔍 ID kiriting:")
        bot.register_next_step_handler(msg, find_username)

    def find_username(msg):
        try:
            user_id = int(msg.text)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                bot.send_message(msg.chat.id, f"ID {user_id} — Username: {row[0]}")
            else:
                bot.send_message(msg.chat.id, "❌ Bunday user topilmadi")
        except ValueError:
            bot.send_message(msg.chat.id, "❌ Noto‘g‘ri ID")

    # Chiqish
    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def admin_exit(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi")
