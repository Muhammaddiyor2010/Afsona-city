import sqlite3
import telebot
import PyPDF2
import re
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types
from config import * # config.py dan hamma narsani olamiz

bot = telebot.TeleBot(TOKEN)
DB_NAME = "users.db"
ADMIN_SESSIONS = set()
user_referrals = {}

# ================= DB QISMI =================
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def user_exists(uid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    conn.close()
    return res is not None

def add_user(uid, ph, ref=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, phone, score, referrer_id) VALUES (?, ?, 0, ?)", (uid, ph, ref))
    conn.commit()
    conn.close()

def add_score(uid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET score = score + 1 WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()

def get_score(uid):
    # Maxsus ID tekshiruvi
    if uid == SPECIAL_USER_ID: return SPECIAL_SCORE
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE user_id = ?", (uid,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else 0

def get_top_100_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT 100")
    data = cur.fetchall()
    conn.close()
    return data

# ================= YORDAMCHI FUNKSIYALAR =================
def get_score_from_pdf(user_id):
    try:
        with open("old.pdf", "rb") as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text()
            pattern = rf"ID:\s*{user_id}\s*\|\s*Ball:\s*(\d+)"
            match = re.search(pattern, full_text)
            return int(match.group(1)) if match else 0
    except: return 0

def check_sub(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except: return False

def generate_rating_pdf(data, title):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)
    y = 760
    total = 0
    for i, (uid, score) in enumerate(data, 1):
        display_score = SPECIAL_SCORE if uid == SPECIAL_USER_ID else score
        pdf.drawString(50, y, f"{i}. ID: {uid} | Ball: {display_score}")
        y -= 18
        total += display_score
        if y < 50: pdf.showPage(); y = 800
    pdf.save()
    return file_name

# ================= ADMIN QISMI =================
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS or user_id == ADMIN_ID

def show_admin_panel(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100 Admin", "📄 Top 100 PDF", "📂 Eski reyting")
    kb.add("📢 Reklama yuborish", "⬅️ Chiqish")
    bot.send_message(msg.chat.id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(commands=["admin"])
def admin_login(msg):
    bot.send_message(msg.chat.id, "🔐 Admin kodni kiriting:")
    bot.register_next_step_handler(msg, check_admin_code)

def check_admin_code(msg):
    if msg.text == ADMIN_CODE:
        ADMIN_SESSIONS.add(msg.from_user.id)
        show_admin_panel(msg)
    else:
        bot.send_message(msg.chat.id, "❌ Kod noto‘g‘ri")

# ================= FOYDALANUVCHI HANDLERLARI =================
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if len(msg.text.split()) > 1:
        user_referrals[uid] = int(msg.text.split()[1])

    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        bot.send_message(uid, "Kanalga obuna bo'ling:", reply_markup=kb)
        return

    if user_exists(uid):
        menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu.add("🔗 Mening havolam", "💰 Mening hisobim")
        menu.add("🏆 Top 100")
        bot.send_message(uid, "Xush kelibsiz!", reply_markup=menu)
    else:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
        bot.send_message(uid, "Ro'yxatdan o'tish uchun kontaktingizni yuboring:", reply_markup=kb)

@bot.message_handler(content_types=["contact"])
def contact_handler(msg):
    uid = msg.from_user.id
    ph = msg.contact.phone_number
    ref = user_referrals.get(uid)
    
    if not user_exists(uid):
        add_user(uid, ph, ref)
        if ref and ref != uid: add_score(ref)
        
        # Ballarni tiklash
        old_score = get_score_from_pdf(uid)
        if old_score > 0:
            for _ in range(old_score): add_score(uid)
            msg_text = f"✅ Ro'yxatdan o'tdingiz. {old_score} ball tiklandi!"
        else:
            msg_text = "✅ Ro'yxatdan o'tdingiz!"
            
        menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu.add("🔗 Mening havolam", "💰 Mening hisobim", "🏆 Top 100")
        bot.send_message(uid, msg_text, reply_markup=menu)

@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    score = get_score(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💰 Sizning jami balingiz: {score}")

@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top_view(msg):
    data = get_top_100_db()
    text = "🏆 <b>TOP 100 REYTING</b>\n\n"
    for i, u in enumerate(data, 1):
        d_score = SPECIAL_SCORE if u[0] == SPECIAL_USER_ID else u[1]
        text += f"{i}. ID: <code>{u[0]}</code> — {d_score} ball\n"
    bot.send_message(msg.chat.id, text, parse_mode="HTML")

# Admin tugmalari uchun handlerlar
@bot.message_handler(func=lambda m: is_admin(m.from_user.id))
def admin_buttons(msg):
    if msg.text == "🏆 Top 100 Admin":
        top_view(msg)
    elif msg.text == "📄 Top 100 PDF":
        file = generate_rating_pdf(get_top_100_db(), "Reyting")
        with open(file, "rb") as f: bot.send_document(msg.chat.id, f)
    elif msg.text == "⬅️ Chiqish":
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "Chiqildi.", reply_markup=types.ReplyKeyboardRemove())

if __name__ == "__main__":
    bot.infinity_polling()
