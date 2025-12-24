import telebot
from telebot import types
import PyPDF2  # PDF o'qish uchun
import re      # ID va Ballni ajratib olish uchun
from config import *
from db import *
from rating import *

bot = telebot.TeleBot(TOKEN)
user_referrals = {}

# ================= YORDAMCHI FUNKSIYALAR =================

def get_score_from_pdf(user_id):
    """old.pdf ichidan user_id ga tegishli ballni qidirib topadi"""
    try:
        with open("old.pdf", "rb") as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text()
            
            # PDF formati: "ID: 1234567 | Ball: 50" shuni qidiradi
            pattern = rf"ID:\s*{user_id}\s*\|\s*Ball:\s*(\d+)"
            match = re.search(pattern, full_text)
            
            if match:
                return int(match.group(1))
    except FileNotFoundError:
        print("Xato: old.pdf fayli topilmadi.")
    except Exception as e:
        print(f"PDF o'qishda xatolik: {e}")
    return 0

def check_sub(user_id):
    """Kanalga obunani tekshirish"""
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= BOT HANDLERLARI =================

@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id

    # Referral tizimi
    if len(msg.text.split()) > 1:
        try:
            user_referrals[user_id] = int(msg.text.split()[1])
        except:
            pass

    text = (
        f"Konkursga qatnashish uchun pastda so’ralgan ma’lumotlarni yuboring va aytilgan amallarni bajaring. "
        "Onlayn taqdimot kanalga qo’shilib 📱Televizor, Muzlatgich va boshqa sovg'alardan birini yutib oling 🎁\n"
        "Qani kettik!!!\n\n"
        f"Birinchi navbatda kanalga qo'shiling va Bajarildi ✅ tugmasini bosing"
    )

    if not check_sub(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        try:
            with open("main.jpg", "rb") as photo:
                bot.send_photo(msg.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, text, reply_markup=kb)
        return

    if user_exists(user_id):
        menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu.add("🔗 Mening havolam", "💰 Mening hisobim")
        menu.add("📘 Qo‘llanma", "🏆 Top 100")
        bot.send_message(msg.chat.id, "✅ Siz allaqachon ro‘yxatdan o‘tgansiz", reply_markup=menu)
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    bot.send_message(msg.chat.id, "📞 Telefon raqamingizni yuboring", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval kanalga obuna bo‘ling", show_alert=True)
        return

    bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi")
    
    # Agar user obuna bo'lib qaytsa va hali ro'yxatda bo'lmasa, telefon so'rash
    if not user_exists(uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
        bot.send_message(call.message.chat.id, "📞 Endi telefon raqamingizni yuboring:", reply_markup=kb)

@bot.message_handler(content_types=["contact"])
def phone(msg):
    uid = msg.from_user.id
    ph = msg.contact.phone_number
    
    # 1. Bazaga qo'shish
    ref = user_referrals.get(uid)
    add_user(uid, ph, ref)
    
    # 2. Taklif qilgan odamga ball berish
    if ref and ref != uid:
        add_score(ref)
    
    mark_joined(uid)

    # 3. PDFdan eski ballarni tekshirish (ASOSIY QISM)
    old_score = get_score_from_pdf(uid)
    if old_score > 0:
        # Ballarni tiklash (necha ball bo'lsa shuncha marta add_score chaqiriladi)
        for _ in range(old_score):
            add_score(uid)
        tiklash_matni = f"\n\n🎁 <b>Eski bazadan {old_score} ballingiz aniqlandi va hisobingizga qo'shildi!</b>"
    else:
        tiklash_matni = ""

    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🔗 Mening havolam", "💰 Mening hisobim")
    menu.add("📘 Qo‘llanma", "🏆 Top 100")

    bot.send_message(
        msg.chat.id, 
        f"✅ Ro‘yxatdan muvaffaqiyatli o‘tdingiz!{tiklash_matni}", 
        reply_markup=menu,
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "🔗 Mening havolam")
def my_link(msg):
    uid = msg.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"
    text = (
        f"🔗 Sizning referal havolangiz:\n{link}\n\n"
        "Do'stlaringizni taklif qiling va sovg'alarga ega bo'ling!"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Ulashish", switch_inline_query=link))
    try:
        with open("main.jpg", "rb") as photo:
            bot.send_photo(msg.chat.id, photo, caption=text, reply_markup=kb)
    except:
        bot.send_message(msg.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    score = get_score(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💰 Sizning jami balingiz: {score}")

@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top_100_view(msg):
    data = get_top_100()
    if not data:
        bot.send_message(msg.chat.id, "Reyting hali shakllanmadi.")
        return
    text = "🏆 <b>TOP 100 REYTING</b>\n\n"
    for i, u in enumerate(data, 1):
        text += f"{i}. ID: <code>{u[0]}</code> — {u[1]} ball\n"
    bot.send_message(msg.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📘 Qo‘llanma")
def guide(msg):
    bot.send_message(msg.chat.id, "📖 Qo'llanma: Link orqali do'stlaringizni taklif qiling va ball yig'ing.")

# Admin qismi (Siz yuborgan admin funksiyalari bu yerda ulanadi)
admin_start(bot)
admin_handlers(bot)

if __name__ == "__main__":
    print("Bot ishlamoqda...")
    bot.infinity_polling(skip_pending=True)
