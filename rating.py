import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types

DB_NAME = "users.db"

# 📞 Admin telefonlari
ADMIN_PHONES = [
    "+998931981793",
    "+998200050252",
    "+998908551141"
]

ADMIN_SESSIONS = set()

# ===================== DB =====================

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def ensure_db_structure():
    conn = get_connection()
    cursor = conn.cursor()
    # Jadval borligini tekshiramiz
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            score INTEGER DEFAULT 0
        )
    """)
    
    # Ustunlar bor-yo'qligini tekshirib, yo'q bo'lsa qo'shamiz
    cursor.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cursor.fetchall()]
    
    if "username" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "phone" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        
    conn.commit()
    conn.close()

ensure_db_structure()

# ===================== RATING =====================

def get_top_100():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT 100")
    data = cursor.fetchall()
    conn.close()
    return data

def get_active_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC")
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

# ===================== ADMIN SYSTEM =====================

def is_admin(user_id):
    return user_id in ADMIN_SESSIONS

def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🏆 Top 100", "👥 Faollar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("📩 1 kishiga xabar", "🔍 ID orqali Info") # Yangi tugma
    kb.add("📢 Reklama (hammaga)")
    kb.add("⬅️ Chiqish")
    bot.send_message(msg.chat.id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML")

def admin_start(bot):
    @bot.message_handler(commands=["admin"])
    def admin_login(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
        bot.send_message(msg.chat.id, "🔐 Admin panelga kirish uchun telefon raqamingizni yuboring", reply_markup=kb)

    @bot.message_handler(content_types=["contact"])
    def check_admin(msg):
        phone = msg.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
        
        if phone in ADMIN_PHONES:
            ADMIN_SESSIONS.add(msg.from_user.id)
            show_admin_panel(bot, msg)
        else:
            bot.send_message(msg.chat.id, "❌ Siz admin emassiz")

# ===================== ADMIN HANDLERS =====================

def admin_handlers(bot):

    # --- TOP & STATS ---
    @bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
    def top100(msg):
        if not is_admin(msg.from_user.id): return
        data = get_top_100()
        text = "🏆 <b>TOP 100</b>\n\n" + "\n".join([f"{i}. ID: <code>{uid}</code> — {s} ball" for i, (uid, s) in enumerate(data, 1)])
        bot.send_message(msg.chat.id, text or "Reyting bo'sh", parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "👥 Faollar")
    def active(msg):
        if not is_admin(msg.from_user.id): return
        data = get_active_users()
        bot.send_message(msg.chat.id, f"👥 Faol foydalanuvchilar: {len(data)} ta")

    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def top_pdf(msg):
        if not is_admin(msg.from_user.id): return
        with open(generate_rating_pdf(get_top_100(), "TOP 100"), "rb") as f:
            bot.send_document(msg.chat.id, f)

    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id): return
        with open(generate_rating_pdf(get_active_users(), "FAOL FOYDALANUVCHILAR"), "rb") as f:
            bot.send_document(msg.chat.id, f)

    # --- 🔍 ID ORQALI INFO OLISH (YANGI) ---
    @bot.message_handler(func=lambda m: m.text == "🔍 ID orqali Info")
    def ask_id_for_info(msg):
        if not is_admin(msg.from_user.id): return
        bot.send_message(msg.chat.id, "🆔 Foydalanuvchi ID sini kiriting:")
        bot.register_next_step_handler(msg, get_user_info_by_id)

    def get_user_info_by_id(msg):
        target_id = msg.text.strip()
        if not target_id.isdigit():
            bot.send_message(msg.chat.id, "❌ ID faqat raqamlardan iborat bo'lishi kerak.")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, phone, score FROM users WHERE user_id=?", (target_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            username, phone, score = row
            text = (
                f"👤 <b>Foydalanuvchi topildi:</b>\n\n"
                f"🆔 ID: <code>{target_id}</code>\n"
                f"🔗 Username: @{username if username else 'Yo‘q'}\n"
                f"📞 <b>Tel:</b> {phone if phone else 'Bazada yo‘q'}\n"
                f"💎 Ball: {score}"
            )
            bot.send_message(msg.chat.id, text, parse_mode="HTML")
        else:
            bot.send_message(msg.chat.id, "❌ Bunday ID bazada topilmadi.")

    # --- 📩 1 KISHIGA XABAR (YAXSHILANDI) ---
    @bot.message_handler(func=lambda m: m.text == "📩 1 kishiga xabar")
    def ask_user_target(msg):
        if not is_admin(msg.from_user.id): return
        bot.send_message(msg.chat.id, "👤 User ID yoki Username (@bilan) kiriting:")
        bot.register_next_step_handler(msg, check_user_target)

    def check_user_target(msg):
        target = msg.text.strip()
        user_id = None
        username = None

        conn = get_connection()
        cursor = conn.cursor()

        # Agar raqam kiritilsa (ID deb qabul qilamiz)
        if target.isdigit():
            cursor.execute("SELECT user_id, username FROM users WHERE user_id=?", (target,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                username = row[1]
        
        # Agar @ bilan kiritilsa (Username)
        elif target.startswith("@"):
            clean_username = target.replace("@", "")
            cursor.execute("SELECT user_id, username FROM users WHERE username=?", (clean_username,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                username = row[1]
        
        conn.close()

        if user_id:
            bot.send_message(msg.chat.id, f"✅ Topildi: {user_id} (@{username})\n\n✍️ Xabar matnini yuboring:")
            bot.register_next_step_handler(msg, send_message_to_target, user_id)
        else:
            bot.send_message(msg.chat.id, "❌ Foydalanuvchi bazadan topilmadi.\nU botga /start bosganmi?")

    def send_message_to_target(msg, user_id):
        try:
            bot.copy_message(chat_id=user_id, from_chat_id=msg.chat.id, message_id=msg.message_id)
            bot.send_message(msg.chat.id, "✅ Xabar muvaffaqiyatli yuborildi!")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Xatolik: {e}")

    # --- REKLAMA ---
    @bot.message_handler(func=lambda m: m.text == "📢 Reklama (hammaga)")
    def ask_ads(msg):
        if not is_admin(msg.from_user.id): return
        bot.send_message(msg.chat.id, "📢 Reklama postini yuboring (rasm, video, matn):")
        bot.register_next_step_handler(msg, send_ads_to_all)

    def send_ads_to_all(msg):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        ok, fail = 0, 0
        status_msg = bot.send_message(msg.chat.id, "⏳ Yuborilmoqda...").message_id

        for (uid,) in users:
            try:
                bot.copy_message(chat_id=uid, from_chat_id=msg.chat.id, message_id=msg.message_id)
                ok += 1
            except:
                fail += 1
        
        bot.delete_message(msg.chat.id, status_msg)
        bot.send_message(msg.chat.id, f"📊 Yakunlandi:\n✅ Bordi: {ok}\n❌ Bormadi: {fail}")

    # --- CHIQISH ---
    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def exit_admin_panel(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi", reply_markup=types.ReplyKeyboardRemove())
