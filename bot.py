import telebot
from telebot import types
import re
import PyPDF2

from config import *   # TOKEN, ADMIN_ID, CHANNEL_USERNAME
from db import *       # eski db funksiyalar
from rating import *   # admin panel funksiyalari

# ================= SOZLAMALAR =================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= START (YANGI) =================

@bot.message_handler(commands=["start"])
def start(msg):
    text = (
        "❌ <b>Aksiya yakunlandi!</b>\n\n"
        "🏠 Lekin siz <b>Afsona City</b> dan uylarni "
        "<b>chegirma narxlarda</b> sotib olishingiz mumkin.\n\n"
        "🌐 Batafsil ma’lumot: <b>afsonastart.uz</b>\n\n"
        "👇 Quyidagi tugmalardan foydalaning:"
    )

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "📢 Telegram", url="https://t.me/afsonacity"
        ),
        types.InlineKeyboardButton(
            "📸 Instagram", url="https://www.instagram.com/afsona.city/"
        ),
        types.InlineKeyboardButton(
            "🏷 Chegirma olish", url="https://afsonastart.uz"
        )
    )

    bot.send_message(msg.chat.id, text, reply_markup=kb)

# ================= ADMIN PANEL (ESKI HOLATDA) =================

try:
    admin_start(bot)
    admin_handlers(bot)
except Exception as e:
    print("Admin panel yuklanmadi:", e)

# ================= RUN =================

if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
