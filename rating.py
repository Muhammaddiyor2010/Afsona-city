import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime
from telebot import types, TeleBot

# ===================== SOZLAMALAR =====================
TOKEN = "8011686611:AAHuyfCBOPdNkQQ-hPpy7E2Ju3wZX__ExMU" # 👈 Tokenni shu yerga yozing
bot = TeleBot(TOKEN)

DB_NAME = "users.db"

# 📞 Admin telefonlari (Admin bo'lishi uchun shu nomerlardan biri bilan kirish kerak)
ADMIN_PHONES = [
    "+998931981793",
    "+998200050252",
    "+998908551141",
    "+998991234567" # O'zingizning nomeringizni ham qo'shing
]

ADMIN_SESSIONS = set()

# ===================== DATABASE (BAZA) =====================

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def ensure_db_structure():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Jadval yaratish
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            score INTEGER DEFAULT 0
        )
    """)
    
    # Agar eski bazada 'phone' yoki 'username' ustuni bo'lmasa, ularni qo'shamiz
    cursor.execute("PRAGMA table_info(users)")
    cols = [c[1] for c in cursor.fetchall()]
    
    if "username" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "phone" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        
    conn.commit()
    conn.close()

ensure_db_structure()

# ===================== USER QISMI (START & NOMER OLISH) =====================

@bot.message_handler(commands=['start'])
def user_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Userni bazaga qo'shamiz (yangi bo'lsa)
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, score) VALUES (?, ?, 0)", (user_id, username))
    
    # Usernameni yangilaymiz (agar o'zgargan bo'lsa)
    cursor.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    
    # Telefon raqami bormi tekshiramiz
    cursor.execute("SELECT phone FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()

    # Agar bazada telefon raqami yo'q bo'lsa, so'raymiz
    if not row or not row[0]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True))
        bot.send_message(message.chat.id, "👋 Assalomu alaykum! Botdan foydalanish uchun telefon raqamingizni yuboring:", reply_markup=kb)
    else:
        bot.send_message(message.chat.id, "✅ Siz allaqachon ro'yxatdan o'tgansiz! Botdan foydalanishingiz mumkin.")

# Kontakt qabul qilish va bazaga saqlash
@bot.message_handler(content_types=['contact'])
def save_contact(message):
    if message.contact.user_id != message.from_user.id:
        bot.send_message(message.chat.id, "❌ Iltimos, o'z raqamingizni yuboring!")
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone=? WHERE user_id=?", (phone, message.from_user.id))
    conn.commit()
    conn.close()
    
    # Admin tekshiruvi (Login payti kerak bo'lishi mumkin)
    if phone in ADMIN_PHONES:
        bot.send_message(message.chat.id, "✅ Admin aniqlandi! /admin buyrug'ini bosing.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "✅ Raqamingiz saqlandi! Endi botdan foydalanishingiz mumkin.", reply_markup=types.ReplyKeyboardRemove())

# ===================== ADMIN PANEL =====================

def is_admin(user_id):
    return user_id in ADMIN_SESSIONS

@bot.message_handler(commands=["admin"])
def admin_login(msg):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE user_id=?", (msg.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    # Agar bazada nomeri bo'lsa va u ADMIN_PHONES da bo'lsa
    if row and row[0] in ADMIN_PHONES:
        ADMIN_SESSIONS.add(msg.from_user.id)
        show_admin_panel(msg)
    else:
        bot.send_message(msg.chat.id, "❌ Siz admin emassiz yoki raqamingiz tasdiqlanmagan (/start bosib raqam yuboring).")

def show_admin_panel(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🏆 Top 100", "👥 Faollar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("📩 1 kishiga xabar", "🔍 ID orqali Nomer") # 👈 MANA SHU TUGMA
    kb.add("📢 Reklama (hammaga)")
    kb.add("⬅️ Chiqish")
    bot.send_message(msg.chat.id, "🛠 <b>Admin panel</b>", reply_markup=kb, parse_mode="HTML")

# ===================== ADMIN HANDLERS =====================

@bot.message_handler(func=lambda m: m.text == "🔍 ID orqali Nomer")
def ask_id_for_info(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "🆔 Foydalanuvchi ID sini kiriting (faqat raqam):")
    bot.register_next_step_handler(msg, get_user_info_by_id)

def get_user_info_by_id(msg):
    target_id = msg.text.strip()
    
    if not target_id.isdigit():
        bot.send_message(msg.chat.id, "❌ ID faqat raqamlardan iborat bo'lishi kerak.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    # Bazadan qidiramiz
    cursor.execute("SELECT username, phone, score FROM users WHERE user_id=?", (target_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        username, phone, score = row
        # Agar telefon raqam bazada bo'lmasa
        phone_text = phone if phone else "❌ Kiritilmagan"
        
        text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"🆔 ID: <code>{target_id}</code>\n"
            f"🔗 Username: @{username if username else 'Yo‘q'}\n"
            f"📞 <b>Telefon:</b> {phone_text}\n"
            f"💎 Ball: {score}"
        )
        bot.send_message(msg.chat.id, text, parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Bunday ID bazada topilmadi. Foydalanuvchi /start bosmagan bo'lishi mumkin.")

# --- Boshqa Admin funksiyalari ---

@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top100(msg):
    if not is_admin(msg.from_user.id): return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, score FROM users WHERE score > 0 ORDER BY score DESC LIMIT 100")
    data = cursor.fetchall()
    conn.close()
    
    text = "🏆 <b>TOP 100</b>\n\n" + "\n".join([f"{i}. ID: <code>{uid}</code> — {s} ball" for i, (uid, s) in enumerate(data, 1)])
    bot.send_message(msg.chat.id, text[:4000] or "Reyting bo'sh", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📩 1 kishiga xabar")
def ask_user_target(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "👤 User ID kiriting:")
    bot.register_next_step_handler(msg, check_user_target)

def check_user_target(msg):
    target_id = msg.text.strip()
    if target_id.isdigit():
        bot.send_message(msg.chat.id, f"✅ ID: {target_id} qabul qilindi.\nXabar matnini yuboring:")
        bot.register_next_step_handler(msg, send_message_to_target, target_id)
    else:
        bot.send_message(msg.chat.id, "❌ ID raqam bo'lishi kerak.")

def send_message_to_target(msg, user_id):
    try:
        bot.copy_message(chat_id=user_id, from_chat_id=msg.chat.id, message_id=msg.message_id)
        bot.send_message(msg.chat.id, "✅ Xabar yuborildi!")
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(func=lambda m: m.text == "📢 Reklama (hammaga)")
def ask_ads(msg):
    if not is_admin(msg.from_user.id): return
    bot.send_message(msg.chat.id, "📢 Reklama postini yuboring:")
    bot.register_next_step_handler(msg, send_ads_to_all)

def send_ads_to_all(msg):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    bot.send_message(msg.chat.id, f"⏳ {len(users)} ta odamga yuborilmoqda...")
    ok = 0
    for (uid,) in users:
        try:
            bot.copy_message(chat_id=uid, from_chat_id=msg.chat.id, message_id=msg.message_id)
            ok += 1
        except: pass
    bot.send_message(msg.chat.id, f"✅ {ok} ta odamga bordi.")

@bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
def exit_admin(msg):
    ADMIN_SESSIONS.discard(msg.from_user.id)
    bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi", reply_markup=types.ReplyKeyboardRemove())

# Botni ishga tushirish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
