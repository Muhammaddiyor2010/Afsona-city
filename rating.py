from telebot import types
from rating import get_top_100, get_active_users, generate_rating_pdf
from db import user_exists

# 🔐 Admin telefon raqami (FAKAT SHU ADMIN BO‘LADI)
ADMIN_PHONE = "+998901234567"  # <-- o'zingni nomeringni yoz
ADMIN_SESSIONS = set()


# 🔐 /admin buyrug‘i
def admin_start(bot):
    @bot.message_handler(commands=["admin"])
    def admin_login(msg):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn = types.KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)
        kb.add(btn)

        bot.send_message(
            msg.chat.id,
            "🔐 Admin panelga kirish uchun telefon raqamingizni yuboring:",
            reply_markup=kb,
        )


    # 📞 Telefonni qabul qilish
    @bot.message_handler(content_types=["contact"])
    def check_admin_contact(msg):
        phone = msg.contact.phone_number

        if phone.startswith("998"):
            phone = "+" + phone

        if phone == ADMIN_PHONE:
            ADMIN_SESSIONS.add(msg.from_user.id)
            show_admin_panel(bot, msg)
        else:
            bot.send_message(msg.chat.id, "❌ Siz admin emassiz")


# 🛡 Admin tekshirish
def is_admin(user_id):
    return user_id in ADMIN_SESSIONS


# 🛠 Admin panel menyusi
def show_admin_panel(bot, msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏆 Top 100", "👥 Faol ishtirokchilar")
    kb.add("📄 Top 100 PDF", "📄 Faollar PDF")
    kb.add("⬅️ Chiqish")

    bot.send_message(
        msg.chat.id,
        "🛠 <b>Admin panel</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )


# 🏆 Top 100 (TEXT)
def admin_handlers(bot):
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


    # 👥 Faol ishtirokchilar
    @bot.message_handler(func=lambda m: m.text == "👥 Faol ishtirokchilar")
    def active_users(msg):
        if not is_admin(msg.from_user.id):
            return

        data = get_active_users()
        bot.send_message(
            msg.chat.id,
            f"👥 Faol foydalanuvchilar soni: {len(data)}"
        )


    # 📄 Top 100 PDF
    @bot.message_handler(func=lambda m: m.text == "📄 Top 100 PDF")
    def top_pdf(msg):
        if not is_admin(msg.from_user.id):
            return

        data = get_top_100()
        file = generate_rating_pdf(data, "Top 100 Reyting")

        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)


    # 📄 Faollar PDF
    @bot.message_handler(func=lambda m: m.text == "📄 Faollar PDF")
    def active_pdf(msg):
        if not is_admin(msg.from_user.id):
            return

        data = get_active_users()
        file = generate_rating_pdf(data, "Faol ishtirokchilar")

        with open(file, "rb") as f:
            bot.send_document(msg.chat.id, f)


    # ⬅️ Chiqish
    @bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
    def admin_exit(msg):
        ADMIN_SESSIONS.discard(msg.from_user.id)
        bot.send_message(msg.chat.id, "🚪 Admin paneldan chiqildi")
