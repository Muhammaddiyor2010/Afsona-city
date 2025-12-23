import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types

DB_NAME = "users.db"

# 📞 Admin telefonlari (2 ta yoki ko‘p bo‘lishi mumkin)
ADMIN_PHONES = [
    "+998931981793",
    "+998200050252",
    "+998908551141"
]

ADMIN_SESSIONS = set()


# ===================== DB =====================

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def ensure_username_column():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cursor.fetchall()]
    if "username" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    conn.commit()
    conn.close()


ensure_username_column()


# ===================== RATING =====================

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


# ===================== PDF =====================

def generate_rating_pdf(data, title):
    filename = "rating.pdf"
    pdf = canvas.Canvas(filename)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(180, 820, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = 770
    total = 0

    pdf.setFont("Helvetica", 11)
    for i, (user_id, score) in enumerate(data, 1):
        pdf.drawString(50, y, f"{i}. ID: {user_id} | Ball: {score}")
        total += score
        y -= 18
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800

    pdf.drawString(50, y - 20, f"JAMI BALL: {total}")
    pdf.save()
    return filename


# ===================== ADMIN =====================

def is_admin(user_id):
    return user_id in ADMIN_SESSIONS


def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol foydalanuvchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("📩 1 kishiga xabar")
    kb.add("📢 Reklama (hammaga)")
    kb.add("⬅️ Chiqish")
    bot.send_message(
        msg.chat.id,
        "🛠 <b>Admin panel</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ===================== ADMIN LOGIN =====================

def admin_start(bot):

    @bot.message_handler(commands=["admin"])
    def admin_login(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
        bot.send_message(
            msg.chat.id,
            "🔐 Admin panelga kirish uchun telefon raqamingizni yuboring",
            reply_markup=kb
        )

    @bot.message_handler(content_types=["contact"])
    def check_admin(msg):
        phone = msg.contact.phone_number
        if phone.startswith("998"):
            phone = "+" + phone

        if phone in ADMIN_PHONES:
            ADMIN_SESSIONS.add(msg.from_user.id)
            show_admin_panel(bot, msg)
        else:
            bot.send_message(msg.chat.id, "❌ Siz admin emassiz")


# ===================== ADMIN HANDLERS =====================

def admin_handlers(bot):

    # 🏆 TOP 100
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

    # 👥 FAOL
    @bot.message_handler(func=lambda m: m.text == "👥 Faol foydalanuvchilar")
    def active(msg):
        if not is_admin(msg.from_user.id):
            return
        data = get_active_users()
        bot.send_message(msg.chat.id, f"👥 Faol foydalanuvchilar: {len(data)} ta")

    # 📄 PDF
    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def top_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        file = generate_rating_pdf(get_top_100(), "TOP 100 REYTING")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id):
            return
        file = generate_rating_pdf(get_active_users(), "FAOL FOYDALANUVCHILAR")
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)

    # ================== 1 USERGA XABAR ==================

    @bot.message_handler(func=lambda m: m.text == "📩 1 kishiga xabar")
    def one_user(msg):
        if not is_admin(msg.from_user.id):
            return
        bot.send_message(msg.chat.id, "👤 Username kiriting (@sizsiz):")
        bot.register_next_step_handler(msg, get_username)

    def get_username(msg):
        username = msg.text.replace("@", "").strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            bot.send_message(msg.chat.id, "❌ Bu user botga /start bosmagan")
            return

        user_id = row[0]
        bot.send_message(msg.chat.id, "✉️ Xabar matnini yuboring:")
        bot.register_next_step_handler(msg, send_one, user_id, username)

    def send_one(msg, user_id, username):
        try:
            bot.send_message(user_id, msg.text)
            bot.send_message(msg.chat.id, f"✅ @{username} ga yuborildi")
        except:
            bot.send_message(msg.chat.id, f"❌ @{username} ga bormadi")

    # ================== HAMMAGA REKLAMA ==================

    @bot.message_handler(func=lambda m: m.text == "📢 Reklama (hammaga)")
    def ads(msg):
        if not is_admin(msg.from_user.id):
            return
        bot.send_message(msg.chat.id, "📢 Reklama matnini yuboring:")
        bot.register_next_step_handler(msg, send_ads)

    def send_ads(msg):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        ok = 0
        fail = 0

        for (uid,) in users:
            try:
                bot.send_message(uid, msg.text)
                ok += 1
            except:
                fail += 1

        bot.send_message(
            msg.chat.id,
            f"📊 Reklama yakuni:\n\n"
            f"✅ BordI: {ok}\n"
            f"❌ Bormadi: {fail}"
        )

    # 🚪 CHIQISH
    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def exit_admin(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi")
