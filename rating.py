import telebot
from telebot import types
# admin_plugin.py faylidan barcha narsani import qilamiz
from admin_plugin import * # TOKENNI SHU YERGA YOZING
TOKEN = "8011686611:AAHuyfCBOPdNkQQ-hPpy7E2Ju3wZX__ExMU"
CHANNEL_USERNAME = "@afsonacity" # Kanal useri (masalan @yangiliklar)

bot = telebot.TeleBot(TOKEN)
user_referrals = {}

# Bazani boshlash (Jadval yaratish)
get_connection()

# Admin funksiyalarini ulash
admin_start(bot)
admin_handlers(bot)

# 🔹 Kanalga obuna tekshirish
def check_sub(user_id):
    try:
        # Bot kanal admini bo'lishi kerak!
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Obuna xatosi: {e}")
        return False

# 🔹 /start komandasi
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id

    # Referral saqlash (link orqali kirsa)
    if len(msg.text.split()) > 1:
        try:
            ref_id = int(msg.text.split()[1])
            if ref_id != user_id: # O'ziga o'zi referral bo'lolmasin
                user_referrals[user_id] = ref_id
        except:
            pass

    text = (
        f"🎉 Konkursga xush kelibsiz!\n\n"
        "1. Kanalga obuna bo'ling.\n"
        "2. '✅ Tekshirish' tugmasini bosing.\n"
        "3. Ro'yxatdan o'tib, do'stlaringizni taklif qiling va sovg'alar yuting!"
    )

    # Kanalga obuna bo‘lmaganlar uchun
    if not check_sub(user_id):
        kb = types.InlineKeyboardMarkup()
        clean_channel = CHANNEL_USERNAME.replace("@", "")
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url=f"https://t.me/{clean_channel}"))
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        
        # Rasm bo'lsa yuboradi, bo'lmasa shunchaki tekst
        try:
            with open("main.jpg", "rb") as photo:
                bot.send_photo(msg.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(msg.chat.id, text, reply_markup=kb)
        return

    # Agar user allaqachon ro'yxatdan o'tgan bo'lsa
    if user_exists(user_id):
        # Agar telefoni yo'q bo'lsa (eski user)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone FROM users WHERE user_id=?", (user_id,))
        p = cur.fetchone()
        conn.close()
        
        if p and p[0]: # Telefoni bor
            show_main_menu(msg.chat.id)
            return

    # Ro'yxatdan o'tish uchun telefon so‘rash
    ask_phone(msg.chat.id)

def ask_phone(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    bot.send_message(chat_id, "📞 Konkursda qatnashish uchun telefon raqamingizni yuboring:", reply_markup=kb)

def show_main_menu(chat_id):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🔗 Mening havolam", "💰 Mening hisobim")
    menu.add("📘 Qo‘llanma", "🏆 Top 100")
    bot.send_message(chat_id, "🖥 Asosiy menyu:", reply_markup=menu)

# 🔹 Callback check (Obunani tekshirish)
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval kanalga obuna bo‘ling!", show_alert=True)
        return

    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Bazaga qo'shamiz (telefon yo'q holatda)
    if not user_exists(uid):
        ref = user_referrals.get(uid)
        # Username ni saqlash
        username = call.from_user.username
        add_user(uid, referrer_id=ref, username=username)
        
        # Referalga ball berish (Faqat raqam tasdiqlanganda emas, obuna bo'lganda beriladigan bo'lsa)
        # Hozirgi mantiq bo'yicha raqam yuborganda ball berish to'g'riroq bo'ladi, 
        # lekin kodda shu yerda turibdi. Agar raqam shart bo'lsa pastga olamiz.
        if ref:
            add_score(ref)
            try:
                bot.send_message(ref, "👏 Sizning havolangiz orqali yangi ishtirokchi qo'shildi! (+1 ball)")
            except:
                pass

    ask_phone(call.message.chat.id)

# 🔹 Telefon raqami qabul qilish (ODDIY USER UCHUN)
# BU YERDA ENDI ADMIN KODI BILAN TO'QNASHUV BO'LMAYDI
@bot.message_handler(content_types=["contact"])
def phone(msg):
    uid = msg.from_user.id
    # Kontaktni saqlash
    add_user(uid, phone=msg.contact.phone_number)
    
    bot.send_message(msg.chat.id, "✅ Telefon raqamingiz muvaffaqiyatli saqlandi!")
    show_main_menu(msg.chat.id)

# 🔹 Mening havolam
@bot.message_handler(func=lambda m: m.text == "🔗 Mening havolam")
def my_link(msg):
    uid = msg.from_user.id
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={uid}"
    
    text = (
        f"📣 <b>Konkursda qatnashing va sovg'alar yuting!</b>\n\n"
        f"Mening havolam orqali kiring:\n{link}"
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("↗️ Ulashish", switch_inline_query=text))
    
    bot.send_message(msg.chat.id, f"🔗 Sizning referal havolangiz:\n<code>{link}</code>", parse_mode="HTML", reply_markup=kb)

# 🔹 Mening hisobim
@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    score = get_score(msg.from_user.id)
    bot.send_message(msg.chat.id, f"👤 <b>Sizning hisobingiz:</b>\n💰 Ballaringiz: {score}", parse_mode="HTML")

# 🔹 Qo‘llanma
@bot.message_handler(func=lambda m: m.text == "📘 Qo‘llanma")
def guide(msg):
    bot.send_message(msg.chat.id, 
        "ℹ️ <b>Qo'llanma:</b>\n\n"
        "1. '🔗 Mening havolam' tugmasini bosing.\n"
        "2. Havolani do'stlaringizga yuboring.\n"
        "3. Har bir qo'shilgan do'stingiz uchun ball oling.\n"
        "4. Ko'p ball to'plang va g'olib bo'ling!", 
        parse_mode="HTML"
    )

# 🔹 Botni ishga tushirish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
