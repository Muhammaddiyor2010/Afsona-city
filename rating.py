import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types

DB_NAME = "users.db"

# 🔐 ADMIN KOD
ADMIN_CODE = "123455"

ADMIN_SESSIONS = set()

# ================= DB =================
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def get_active_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, score
        FROM users
        WHERE score > 0
        ORDER BY score DESC
    """)
    data = cur.fetchall()
    conn.close()
    return data


# ================= PDF =================
def generate_active_users_pdf(data):
    file_name = "faol_foydalanuvchilar.pdf"
    pdf = canvas.Canvas(file_name)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(160, 820, "Faol foydalanuvchilar reytingi")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = 770
    total_score = 0
    pdf.setFont("Helvetica", 11)

    for i, (uid, score) in enumerate(data, 1):
        pdf.drawString(50, y, f"{i}. ID: {uid} | Ball: {score}")
        y -= 18
        total_score += score

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y - 30, f"UMUMIY BALL: {total_score}")

    pdf.save()
    return file_name


# ================= ADMIN CORE =================
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS


def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Faol foydalanuvchilar PDF")
    kb.add("🔍 ID orqali qidirish")
    kb.add("📢 Reklama yuborish")
    kb.add("⬅️ Chiqish")

    bot.send_message(
        msg.chat.id,
        "🛠 <b>Admin panel</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ================= ADMIN LOGIN =================
def admin_start(bot):

    @bot.message_handler(commands=["admin"])
    def admin_login(msg):
        bot.send_message(msg.chat.id, "🔐 Admin kodni kiriting:")
        bot.register_next_step_handler(msg, lambda m: check_admin_code(bot, m))


def check_admin_code(bot, msg):
    if msg.text == ADMIN_CODE:
        ADMIN_SESSIONS.add(msg.from_user.id)
        show_admin_panel(bot, msg)
    else:
        bot.send_message(msg.chat.id, "❌ Kod noto‘g‘ri")


# ================= ADMIN HANDLERS =================
def admin_handlers(bot):

    @bot.message_handler(func=lambda m: m.text == "📄 Faol foydalanuvchilar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id):
            return

        data = get_active_users()
        if not data:
            bot.send_message(msg.chat.id, "❌ Faol foydalanuvchi yo‘q")
            return

        file = generate_active_users_pdf(data)
        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)


    @bot.message_handler(func=lambda m: m.text == "🔍 ID orqali qidirish")
    def ask_id(msg):
        if not is_admin(msg.from_user.id):
            return
        bot.send_message(msg.chat.id, "🆔 User ID kiriting:")
        bot.register_next_step_handler(msg, lambda m: find_user_info(bot, m))


    @bot.message_handler(func=lambda m: m.text == "📢 Reklama yuborish")
    def broadcast(msg):
        if not is_admin(msg.from_user.id):
            return
        bot.send_message(msg.chat.id, "📢 Reklama xabarini yuboring:")
        bot.register_next_step_handler(msg, lambda m: broadcast_message(bot, m))


    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def exit_admin(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi")


# ================= EXTRA =================
def find_user_info(bot, msg):
    try:
        user_id = int(msg.text)
    except:
        bot.send_message(msg.chat.id, "❌ ID noto‘g‘ri")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, phone FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        bot.send_message(msg.chat.id, "❌ Foydalanuvchi topilmadi")
        return

    username, phone = row
    bot.send_message(
        msg.chat.id,
        f"🆔 ID: {user_id}\n👤 Username: {username}\n📞 Telefon: {phone}"
    )


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
        except:
            fail += 1

    bot.send_message(
        msg.chat.id,
        f"📊 Yakun:\n✅ Yuborildi: {ok}\n❌ Xato: {fail}"
    )
