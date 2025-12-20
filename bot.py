import telebot
from telebot import types
from config import *
from db import *
from reportlab.pdfgen import canvas
from rating import *


def check_sub(user_id: int) -> bool:
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


bot = telebot.TeleBot(TOKEN)

user_referrals = {}


@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    # referal ID ni saqlash
    if len(msg.text.split()) > 1:
        try:
            ref_id = int(msg.text.split()[1])
            user_referrals[user_id] = ref_id
        except ValueError:
            pass

    # start xabar matni
    start_text = (
        "🎉Assalom alaykum Afsona city loyihasidan Namanganliklar uchun qilayotgan kunkurs botiga xush kelibsiz\n\n"
        "Konkursga qatnashish uchun pastda so’ralgan ma’lumotlarni yuboring va aytilgan amallarni bajaring. "
        "Onlayn taqdimot kanalga qo’shilib 📱Televizor, Muzlatgich  va boshqa sovg'alardan birini yutib oling 🎁\n\n"
        "Qani kettik!!!\n\n"
        "Birinchi navbatda kanalga qo'shiling va Bajarildi ✅ tugmasini bosing"
    )
    call_text = (
        "Juda yaxshi!\n"
        "Sizga bog'lana olishim uchun pastdagi “📞 Telefon yuborish” tugmasini bosib telefon raqamingizni yuboring yoki raqamingizni 99******* kabi yozib yuboring."
    )

    if not check_sub(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "📢 Kanalga obuna", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )
        )
        kb.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        bot.send_message(msg.chat.id, start_text, reply_markup=kb)
        return

    # user allaqachon ro‘yxatdan o‘tgan bo‘lsa menu
    if user_exists(user_id):
        menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu.add("🔗 Mening havolam", "💰 Mening hisobim")
        menu.add("📘 Qo‘llanma")
        bot.send_message(
            msg.chat.id,
            start_text + "\n\n✅ Siz allaqachon ro‘yxatdan o‘tgansiz",
            reply_markup=menu,
        )
        return

    # telefon so‘rash
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📞 Telefon yuborish", request_contact=True))
    bot.send_message(
        msg.chat.id,
        start_text + "\n\n " + call_text,
        reply_markup=kb,
    )


# Obuna tekshirish va ball berish
@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(call):
    user_id = call.from_user.id

    if not check_sub(user_id):
        bot.answer_callback_query(
            call.id, "❌ Avval kanalga obuna bo‘ling", show_alert=True
        )
        return

    # faqat yangi user uchun
    if not user_exists(user_id):
        ref_id = user_referrals.get(user_id)

        add_user(user_id=user_id, phone=None, ref_by=ref_id)

        # ball berish faqat referal mavjud bo‘lsa
        if ref_id:
            add_score(ref_id)

        # userga ball berilganini belgilash
        mark_joined(user_id)

    bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi")

    # avtomatik start
    fake_msg = call.message
    fake_msg.text = "/start"
    fake_msg.from_user = call.from_user
    start(fake_msg)


# 🔹 TELEFON
@bot.message_handler(content_types=["contact"])
def phone(msg):
    add_user(msg.from_user.id, msg.contact.phone_number)
    

    link = f"https://t.me/{bot.get_me().username}?start={msg.from_user.id}"

    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🔗 Mening havolam", "💰 Mening hisobim")
    menu.add("📘 Qo‘llanma")

    bot.send_message(
        msg.chat.id, f"✅ Ro‘yxatdan o‘tdingiz", reply_markup=menu
    )
    bot.send_message(
        msg.chat.id, f"📢 🥳 Namanganliklar uchun Afsona city kompaniyasidan KATTA YANGILIK tayyorlaganmiz.\n\n"
        "🤫 Yaqin kunlarda, aynan shu telegram kanalimizda barchasini sizlarga e'lon qilamiz.\n\n"
        "✈️ Siz esa kanalga obuna bo'ling va barcha Namanganlik yaqinlaringizni kanalimizga taklif qiling.\n\n"

        "Bundan tashqari kanalga odam qo’shi b, uy xarid qilmasdanham Televizor, Muzlatgich yoki boshqa sovg’alardan birini yutib olishingiz mumkin!\n\n"

        "Qatnashish uchun quyidagi havola orqali o’ting 👇👇👇\n"

        f"🔗 Sizning referal havolangiz:\n{link}"
        )


# 🔹 MENU
@bot.message_handler(func=lambda m: m.text == "🔗 Mening havolam")
def my_link(msg):
    link = f"https://t.me/{bot.get_me().username}?start={msg.from_user.id}"
    
    bot.send_message(
        msg.chat.id, 
        f"🔗 Sizning referal havolangiz:\n{link}"
        )


@bot.message_handler(func=lambda m: m.text == "💰 Mening hisobim")
def my_score(msg):
    score = get_score(msg.from_user.id)
    bot.send_message(msg.chat.id, f"💰 Sizning balingiz: {score}")


@bot.message_handler(func=lambda m: m.text == "📘 Qo‘llanma")
def guide(msg):
    bot.send_message(
        msg.chat.id,
        "❓ Tanishlarni qanday qo‘shish kerak va ballar qanday hisoblanadi?\n\n"
        "👥 Sizga berilgan shaxsiy link orqali kanalga qo‘shilgan har bir  tanishingiz uchun sizga +1 ball beriladi.\n\n"
        "📌 O‘yinni muvaffaqiyatli o‘tish uchun menyudagi bo‘limlardan yoki pastdagi tugmalardan foydalaning.\n"
        "Faollik ko‘rsating, vazifalarni bajaring va sovg‘alarni qo‘lga kiriting! 🎁\n\n"
        "🔗 Tanishlarni taklif qilish uchun:\n"
        "“Mening shaxsiy linkim 🔗” tugmasini bosing va do‘stlaringiz bilan ulashing.\n\n"
        "📑 Hisobingizni tekshirish uchun:\n"
        "👉 “Mening hisobim 📑” tugmasini bosing va nechta tanishingiz qo‘shilganini bilib oling.",
    )

# 🔹 ADMIN
@bot.message_handler(commands=["admin"])
def admin(msg):
    bot.send_message(msg.chat.id, "🔑 Parolni kiriting")
    bot.register_next_step_handler(msg, check_admin)


def check_admin(msg):
    if msg.text == ADMIN_PASSWORD:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🏆 Top 100", "📄 PDF chiqarish")
        bot.send_message(msg.chat.id, "👑 Admin panel", reply_markup=kb)
    else:
        bot.send_message(msg.chat.id, "❌ Noto‘g‘ri parol")


# 🔹 PDF
@bot.message_handler(func=lambda m: m.text == "📄 PDF chiqarish")
def pdf(msg):
    data = get_active_users()
    pdf = canvas.Canvas("rating.pdf")
    y = 800
    for i, u in enumerate(data, 1):
        pdf.drawString(50, y, f"{i}. ID:{u[0]} | Ball:{u[1]}")
        y -= 20
    pdf.save()
    bot.send_document(msg.chat.id, open("rating.pdf", "rb"))


bot.infinity_polling()


@bot.message_handler(func=lambda m: m.text == "🏆 Top 100")
def admin_top_100(msg):
    data = get_top_100()

    if not data:
        bot.send_message(msg.chat.id, "📭 Reyting bo‘sh")
        return

    text = "🏆 TOP 100 REYTING\n\n"
    for i, (uid, score) in enumerate(data, 1):
        text += f"{i}. ID: {uid} — {score} ball\n"
    
    bot.send_message(msg.chat.id, text)
    bot.send_message(msg.chat.id, "Salom")
