import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types
import telebot

# Bot tokeningizni bu yerga yozing
BOT_TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

DB_NAME = "users.db"

# 🔐 ADMIN KOD
ADMIN_CODE = "123455"

# Admin sessiyalar
ADMIN_SESSIONS = set()

# Maxsus ID uchun o'zgarmas ball
SPECIAL_USER_ID = 5688522534
SPECIAL_SCORE = 160

# ================= DB =================
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def get_top_100():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT 100"
    )
    data = cur.fetchall()
    conn.close()
    return data

def get_active_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC"
    )
    data = cur.fetchall()
    conn.close()
    return data

# ================= PDF =================
def generate_rating_pdf(data, title):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = 760
    total = 0
    pdf.setFont("Helvetica", 11)

    for i, (uid, score) in enumerate(data, 1):
        # ❗ Maxsus ID tekshiruvi
        display_score = SPECIAL_SCORE if uid == SPECIAL_USER_ID else score
        
        pdf.drawString(50, y, f"{i}. ID: {uid} | Ball: {display_score}")
        y -= 18
        total += display_score

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800

    pdf.drawString(50, y - 20, f"JAMI BALL: {total}")
    pdf.save()
    return file_name

# ================= ADMIN CORE =================
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS

def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol ishtirokchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("📂 Eski reyting") 
    kb.add("🔍 ID orqali tekshirish")
    kb.add("📩 1 kishiga xabar", "📢 Reklama yuborish")
    kb.add("⬅️ Chiqish")

    bot.send_message(
        msg.chat.id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML"
    )

# ================= ADMIN LOGIN =================
@bot.message_handler(commands=["admin"])
def admin_login(msg):
    bot.send_message(msg.chat.id, "🔐 Admin panelga kirish uchun kodni kiriting:")
    bot.register_next_step_handler(msg, lambda m: check_admin_code(bot, m))

def check_admin_code(bot, msg):
    if msg.text == ADMIN_CODE:
        ADMIN_SESSIONS.add(msg.from_user.id)
        show_admin_panel(bot, msg)
    else:
        bot.send_message(msg.chat.id, "❌ Kod noto‘g‘ri")

# ================= ADMIN HANDLERS =================
@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top100(msg):
    if not is_admin(msg.from_user.id): return
    data = get_top_100()
    if not data:
        bot.send_message(msg.chat.id, "❌ Reyting yo‘q")
        return

    text = "🏆 <b>TOP 100</b>\n\n"
    for i, (uid, score) in enumerate(data, 1):
        # ❗ Maxsus ID tekshiruvi
        display_score = SPECIAL_SCORE if uid == SPECIAL_USER_ID else score
        text += f"{i}. <code>{uid}</code> — {display_score} ball\n"

    bot.send_message(msg.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👥 Faol ishtirokchilar")
def active_users_handler(msg):
    if not is_admin(msg.from_user.id): return
    data = get_active_users()
    text = "👥 <b>Faol foydalanuvchilar</b>\n\n"

    for i, (uid, score) in enumerate(data, 1):
        # ❗ Maxsus ID tekshiruvi
        display_score = SPECIAL_SCORE if uid == SPECIAL_USER_ID else score
        text += f"{i}. <code>{uid}</code> — {display_score} ball\n"

    bot.send_message(msg.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
def top_pdf(msg):
    if not is_admin(msg.from_user.id): return
    file = generate_rating_pdf(get_top_100(), "Top 100 Reyting")
    with open(file, "rb") as f:
        bot.send_document(msg.chat.id, f)

@bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
def active_pdf(msg):
    if not is_admin(msg.from_user.id): return
    file = generate_rating_pdf(get_active_users(), "Faol foydalanuvchilar")
    with open(file, "rb") as f:
        bot.send_document(msg.chat.id, f)

@bot.message_handler(func=lambda m: m.text == "📂 Eski reyting")
def send_old_pdf(msg):
    if not is_admin(msg.from_user.id): return
    try:
        with open("old.pdf", "rb") as f:
            bot.send_document(msg.chat.id, f, caption="📂 Mana eski reyting fayli")
    except FileNotFoundError:
        bot.send_message(msg.chat.id, "❌ <b>old.pdf</b> topilmadi!")

@bot.message_handler(func=lambda m: m.text == "🔍 ID orqali tekshirish")
def ask_id(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "🆔 User ID kiriting:")
    bot.register_next_step_handler(msg, lambda m: find_user_info(bot, m))

@bot.message_handler(func=lambda m: m.text == "📩 1 kishiga xabar")
def one_user(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "👤 User ID kiriting:")
    bot.register_next_step_handler(msg, lambda m: ask_single_message(bot, m))

@bot.message_handler(func=lambda m: m.text == "📢 Reklama yuborish")
def broadcast(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "📢 Reklama xabarini yuboring")
    bot.register_next_step_handler(msg, lambda m: broadcast_message(bot, m))

@bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
def exit_admin(msg):
    ADMIN_SESSIONS.discard(msg.from_user.id)
    bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi", reply_markup=types.ReplyKeyboardRemove())

# ================= QO'SHIMCHA FUNKSIYALAR =================
def find_user_info(bot, msg):
    try:
        user_id = int(msg.text)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, phone, score FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            # ❗ Bu yerda ham maxsus ID tekshiruvi
            score = SPECIAL_SCORE if user_id == SPECIAL_USER_ID else row[2]
            bot.send_message(msg.chat.id, f"🆔 ID: {user_id}\n👤 Username: {row[0]}\n📞 Tel: {row[1]}\n📊 Ball: {score}")
        else:
            bot.send_message(msg.chat.id, "❌ Topilmadi")
    except:
        bot.send_message(msg.chat.id, "❌ Xatolik")

def ask_single_message(bot, msg):
    try:
        uid = int(msg.text)
        bot.send_message(msg.chat.id, "✍️ Xabar yuboring")
        bot.register_next_step_handler(msg, lambda m: send_single(bot, m, uid))
    except:
        bot.send_message(msg.chat.id, "❌ ID xato")

def send_single(bot, msg, user_id):
    try:
        bot.copy_message(user_id, msg.chat.id, msg.message_id)
        bot.send_message(msg.chat.id, "✅ Yuborildi")
    except:
        bot.send_message(msg.chat.id, "❌ Yuborilmadi")

def broadcast_message(bot, msg):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    conn.close()
    ok, fail = 0, 0
    for (uid,) in users:
        try:
            bot.copy_message(uid, msg.chat.id, msg.message_id)
            ok += 1
        except: fail += 1
    bot.send_message(msg.chat.id, f"📊 Yakun: ✅ {ok}, ❌ {fail}")

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
