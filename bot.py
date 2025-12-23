import telebot
from telebot import types
from config import *
from db import *
from rating import *
from reportlab.pdfgen import canvas
from rating import admin_start, admin_handlers
    
bot = telebot.TeleBot(TOKEN)
user_referrals = {}


admin_start(bot)
admin_handlers(bot)

# 🔹 Kanalga obuna tekshirish
def check_sub(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False


# 🔹 /start komandasi
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id

    # Referral
    if len(msg.text.split()) > 1:
        try:
            user_referrals[user_id] = int(msg.text.split()[1])
        except:
            pass

    text = (
        f"Konkursga qatnashish uchun pastda so’ralgan ma’lumotlarni yuboring va aytilgan amallarni bajaring. "
        "Onlayn taqdimot kanalga qo’shilib 📱Televizor, Muzlatgich  va boshqa sovg'alardan birini yutib oling 🎁\n"
        "Qani kettik!!!\n\n"
        f"Birinchi navbatda kanalga qo'shiling va Bajarildi ✅ tugmasini bosing"
    )

    # Kanalga obuna bo‘lmaganlar
    if not check_sub(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "📢 Kanalga obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )
        )
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        with open("main.jpg", "rb") as photo:
            bot.send_photo(msg.chat.id, photo, caption=text, reply_markup=kb)
        return

    # Agar user bazada bo‘lsa
    if user_exists(user_id):
        menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu.add("🔗 Mening havolam", "💰 Mening hisobim")
        menu.add("📘 Qo‘llanma")
        bot.send_message(
            msg.chat.id, "✅ Siz allaqachon ro‘yxatdan o‘tgansiz", reply_markup=menu
        )
        return

    # Telefon so‘rash
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    bot.send_message(msg.chat.id, "📞 Telefon raqamingizni yuboring", reply_markup=kb)


# 🔹 Callback check
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    uid = call.from_user.id

    if not check_sub(uid):
        bot.answer_callback_query(
            call.id, "❌ Avval kanalga obuna bo‘ling", show_alert=True
        )
        return

    if not user_exists(uid):
        ref = user_referrals.get(uid)
        add_user(uid, None, ref)
        if ref and ref != uid:
            add_score(ref)
        mark_joined(uid)

    bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi")

    # Menu ko‘rsatish
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🔗 Mening havolam", "💰 Mening hisobim")
    menu.add("📘 Qo‘llanma")

    bot.send_message(
        call.message.chat.id,
        "🎉 Tabriklaymiz! Siz konkursga muvaffaqiyatli qo‘shildingiz.",
        reply_markup=menu,
    )


# 🔹 Telefon raqami
@bot.message_handler(content_types=["contact"])
def phone(msg):
    add_user(msg.from_user.id, msg.contact.phone_number)
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🔗 Mening havolam", "💰 Mening hisobim")
    menu.add("📘 Qo‘llanma")
    bot.send_message(msg.chat.id, "✅ Ro‘yxatdan o‘tdingiz", reply_markup=menu)


# 🔹 Mening havolam
@bot.message_handler(func=lambda m: m.text == "🔗 Mening havolam")
def my_link(msg):
    uid = msg.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"

    text = (
        f"📢 🥳 Namanganliklar uchun Afsona city kompaniyasidan KATTA YANGILIK tayyorlaganmiz.\n\n"
        "🤫 Yaqin kunlarda, aynan shu telegram kanalimizda barchasini sizlarga e'lon qilamiz.\n\n"
        "✈️ Siz esa kanalga obuna bo'ling va barcha Namanganlik yaqinlaringizni kanalimizga taklif qiling.\n\n"
        "Bundan tashqari kanalga odam qo’shish orqali Televizor, Muzlatgich yoki boshqa sovg’alardan birini yutib olishingiz mumkin!\n\n"
        "Qatnashish uchun quyidagi havola orqali o’ting 👇👇👇\n"
        f"🔗 Sizning referal havolangiz:\n{link}"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Ulashish", switch_inline_query=link))

    with open("main.jpg", "rb") as photo:
        bot.send_photo(msg.chat.id, photo, caption=text, reply_markup=kb)


# 🔹 Mening hisobim
@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    bot.send_message(msg.chat.id, f"💰 Sizning balingiz: {get_score(msg.from_user.id)}")



# 🔹 Top 100
@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def top100(msg):
    data = get_top_100()
    text = "🏆 TOP 100\n\n"
    for i, u in enumerate(data, 1):
        text += f"{i}. {u[0]} — {u[1]} ball\n"
    bot.send_message(msg.chat.id, text)


# 🔹 Qo‘llanma
@bot.message_handler(func=lambda m: m.text == "📘 Qo‘llanma")
def guide(msg):
    bot.send_message(
        msg.chat.id,
        "❓ Tanishlarni qanday qo‘shish kerak va ballar qanday hisoblanadi?\n\n"
        "👥 Sizga berilgan shaxsiy link orqali kanalga qo‘shilgan har bir tanishingiz uchun sizga +1 ball beriladi.\n\n"
        "📌 O‘yinni muvaffaqiyatli o‘tish uchun menyudagi bo‘limlardan yoki pastdagi tugmalardan foydalaning.\n"
        "Faollik ko‘rsating, vazifalarni bajaring va sovg‘alarni qo‘lga kiriting! 🎁\n\n"
        "🔗 Tanishlarni taklif qilish uchun:\n"
        "“Mening shaxsiy linkim 🔗” tugmasini bosing va do‘stlaringiz bilan ulashing.\n\n"
        "📑 Hisobingizni tekshirish uchun:\n"
        "👉 “Mening hisobim 📑” tugmasini bosing va nechta tanishingiz qo‘shilganini bilib oling.",
    )





# 🔹 Infinity polling (409 xatoni oldini olish uchun)
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True, timeout=60)
