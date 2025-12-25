import telebot
from telebot import types
import re
import PyPDF2

from config import *   # TOKEN, ADMIN_ID, CHANNEL_USERNAME
from db import *       # get_connection, user_exists, add_user, add_score, mark_joined
from rating import *   # get_top_100, admin_start, admin_handlers, get_score_from_pdf

# ================= SOZLAMALAR =================

SPECIAL_USER_ID = 5688522534
SPECIAL_SCORE = 150

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
user_referrals = {}

# ================= YORDAMCHI FUNKSIYALAR =================

def get_score(user_id):
    if user_id == SPECIAL_USER_ID:
        return SPECIAL_SCORE

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()

    db_score = row[0] if row else 0

    if db_score == 0:
        return get_score_from_pdf(user_id)

    return db_score


def check_sub(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


def phone_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    return kb


def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔗 Mening havolam", "💰 Mening hisobim")
    kb.add("📘 Qo‘llanma", "🏆 Top 100")
    return kb

# ================= START =================

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id

    # referal
    if len(msg.text.split()) > 1:
        try:
            user_referrals[uid] = int(msg.text.split()[1])
        except:
            pass

    text = (
        "🎉 <b>KONKURS BOSHLANDI!</b>\n\n"
        "Sovg‘alar: 📱 Telefon, 📺 Televizor va boshqalar 🎁\n\n"
        "1️⃣ Kanalga obuna bo‘ling\n"
        "2️⃣ <b>Tekshirish</b> tugmasini bosing"
    )

    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        bot.send_message(msg.chat.id, text, reply_markup=kb)
        return

    if user_exists(uid):
        bot.send_message(msg.chat.id, "✅ Siz ro‘yxatdan o‘tgansiz", reply_markup=main_menu())
        return

    bot.send_message(
        msg.chat.id,
        "📞 Telefon raqamingizni yuboring (tugma orqali 👇)",
        reply_markup=phone_keyboard()
    )

# ================= OBUNA TEKSHIRISH =================

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    uid = call.from_user.id

    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval kanalga obuna bo‘ling", show_alert=True)
        return

    bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi")

    if not user_exists(uid):
        bot.send_message(
            call.message.chat.id,
            "📞 Endi telefon raqamingizni yuboring:",
            reply_markup=phone_keyboard()
        )

# ================= CONTACT ORQALI =================

@bot.message_handler(content_types=["contact"])
def phone_contact(msg):
    uid = msg.from_user.id

    if msg.contact.user_id != uid:
        bot.send_message(msg.chat.id, "❌ O‘zingizning raqamingizni yuboring")
        return

    register_user(uid, msg.contact.phone_number, msg.chat.id)

# ================= MATN ORQALI RAQAM =================

@bot.message_handler(func=lambda m: m.text and re.fullmatch(r"\+?\d{9,15}", m.text))
def phone_text(msg):
    uid = msg.from_user.id
    register_user(uid, msg.text, msg.chat.id)

# ================= RAQAMNI RO‘YXATDAN O‘TKAZISH =================

def register_user(uid, phone, chat_id):
    if user_exists(uid):
        bot.send_message(chat_id, "ℹ️ Siz allaqachon ro‘yxatdan o‘tgansiz", reply_markup=main_menu())
        return

    ref = user_referrals.get(uid)
    add_user(uid, phone, ref)

    if ref and ref != uid:
        add_score(ref)

    mark_joined(uid)

    old_score = get_score_from_pdf(uid)
    if old_score > 0:
        for _ in range(old_score):
            add_score(uid)
        extra = f"\n🎁 <b>Eski bazadan {old_score} ball qo‘shildi!</b>"
    else:
        extra = ""

    bot.send_message(
        chat_id,
        f"✅ <b>Ro‘yxatdan o‘tdingiz!</b>{extra}",
        reply_markup=main_menu()
    )

# ================= MENING HAVOLAM =================

@bot.message_handler(func=lambda m: m.text == "🔗 Mening havolam")
def my_link(msg):
    uid = msg.from_user.id
    username = bot.get_me().username
    link = f"https://t.me/{username}?start={uid}"

    bot.send_message(
        msg.chat.id,
        f"🔗 <b>Sizning havolangiz:</b>\n{link}\n\nDo‘stlaringizni taklif qiling 🎁"
    )

# ================= MENING HISOBIM =================

@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    score = get_score(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💰 <b>Sizning ballingiz:</b> {score}")

# ================= TOP 100 =================

@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top_100_view(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "❌ Faqat adminlar uchun")
        return

    data = get_top_100()
    if not data:
        bot.send_message(msg.chat.id, "Reyting yo‘q")
        return

    text = "🏆 <b>TOP 100</b>\n\n"
    for i, u in enumerate(data, 1):
        text += f"{i}. <code>{u[0]}</code> — {u[1]} ball\n"

    bot.send_message(msg.chat.id, text)

# ================= QO‘LLANMA =================

@bot.message_handler(func=lambda m: m.text == "📘 Qo‘llanma")
def guide(msg):
    bot.send_message(msg.chat.id, "📖 Do‘stlaringizni havola orqali taklif qiling va ball yig‘ing!")

# ================= ADMIN =================

try:
    admin_start(bot)
    admin_handlers(bot)
except:
    pass

# ================= RUN =================

if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
