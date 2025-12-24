import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types
import os

DB_NAME = "users.db"

# Adminlar ro'yxati (Format muhim emas, kod o'zi to'g'irlaydi)
ADMIN_PHONES = [
    "998931981793",
    "998200050252",
    "998908551141"
]

ADMIN_SESSIONS = set()

# ================= DB (BAZA) =================
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    # Jadval yaratish
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            username TEXT,
            score INTEGER DEFAULT 0,
            referrer_id INTEGER,
            joined_channel BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    return conn

# User borligini tekshirish
def user_exists(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

# User qo'shish
def add_user(user_id, phone=None, referrer_id=None, username=None):
    if user_exists(user_id):
        # Agar faqat telefonni yangilash kerak bo'lsa
        if phone:
            conn = get_connection()
            conn.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
            conn.commit()
            conn.close()
        return

    conn = get_connection()
    conn.execute(
        "INSERT INTO users (user_id, phone, referrer_id, username, score) VALUES (?, ?, ?, ?, 0)",
        (user_id, phone, referrer_id, username)
    )
    conn.commit()
    conn.close()

# Ball qo'shish
def add_score(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET score = score + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Ballni olish
def get_score(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    data = cur.fetchone()
    conn.close()
    return data[0] if data else 0

def mark_joined(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET joined_channel = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_top_100():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT 100")
    data = cur.fetchall()
    conn.close()
    return data

def get_active_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC")
    data = cur.fetchall()
    conn.close()
    return data

# ================= PDF =================
def generate_rating_pdf(data, title):
    file_name = "rating.pdf"
    p = canvas.Canvas(file_name)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, title)
    p.setFont("Helvetica", 10)
    p.drawString(50, 780, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    y = 750
    p.setFont("Helvetica", 12)
    for i, (uid, score) in enumerate(data, 1):
        p.drawString(50, y, f"{i}. ID: {uid} | Ball: {score}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
    
    p.save()
    return file_name

# ================= ADMIN LOGIKASI =================
def clean_phone(phone):
    """Raqamni tozalash faqat raqamlarni qoldirish"""
    return "".join(filter(str.isdigit, phone))

def is_admin(user_id):
    return user_id in ADMIN_SESSIONS

def show_admin_panel(bot, chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol ishtirokchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("🔍 ID orqali tekshirish")
    kb.add("📩 1 kishiga xabar", "📢 Reklama yuborish")
    kb.add("⬅️ Chiqish")
    
    bot.send_message(chat_id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML")

# BU YERDA XATOLIK TUZATILDI: Handler decorator o'rniga next_step ishlatamiz
def check_admin_login(msg, bot):
    if not msg.contact:
        bot.send_message(msg.chat.id, "❌ Kontakt yuborilmadi.")
        return

    phone = clean_phone(msg.contact.phone_number)
    admin_phones_clean = [clean_phone(p) for p in ADMIN_PHONES]

    if phone in admin_phones_clean:
        ADMIN_SESSIONS.add(msg.from_user.id)
        bot.send_message(msg.chat.id, "✅ Admin tasdiqlandi!")
        show_admin_panel(bot, msg.chat.id)
    else:
        bot.send_message(msg.chat.id, "❌ Siz admin emassiz.", reply_markup=types.ReplyKeyboardRemove())

def admin_start(bot):
    @bot.message_handler(commands=["admin"])
    def admin_entry(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
        bot.send_message(msg.chat.id, "🔐 Admin panelga kirish uchun telefon raqamingizni yuboring:", reply_markup=kb)
        
        # KEYINGI QADAMNI BELGILAYMIZ (Bu oddiy userlarga xalaqit bermaydi)
        bot.register_next_step_handler(msg, lambda m: check_admin_login(m, bot))

# ================= ADMIN HANDLERS =================
def admin_handlers(bot):
    @bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
    def top100_handler(msg):
        if is_admin(msg.from_user.id):
            data = get_top_100()
            text = "🏆 <b>TOP 100</b>\n\n"
            for i, (uid, score) in enumerate(data, 1):
                text += f"{i}. <code>{uid}</code> — {score} ball\n"
            bot.send_message(msg.chat.id, text if data else "❌ Reyting bo'sh", parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "👥 Faol ishtirokchilar")
    def active_handler(msg):
        if is_admin(msg.from_user.id):
            data = get_active_users()
            text = "👥 <b>Faol foydalanuvchilar</b>\n\n"
            for i, (uid, score) in enumerate(data, 1):
                text += f"{i}. <code>{uid}</code> — {score} ball\n"
            bot.send_message(msg.chat.id, text if data else "❌ Bo'sh", parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def pdf_top_handler(msg):
        if is_admin(msg.from_user.id):
            file = generate_rating_pdf(get_top_100(), "Top 100 Reyting")
            with open(file, "rb") as f:
                bot.send_document(msg.chat.id, f)

    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def pdf_active_handler(msg):
        if is_admin(msg.from_user.id):
            file = generate_rating_pdf(get_active_users(), "Faollar")
            with open(file, "rb") as f:
                bot.send_document(msg.chat.id, f)
    
    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def exit_admin(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi", reply_markup=types.ReplyKeyboardRemove())

    # Qo'shimcha admin funksiyalari (Broadcast va ID search) shu yerda bo'lishi mumkin...
