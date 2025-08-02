# bot.py

import asyncio
import logging
import os
import threading
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# --- Veb-server qismi (Render uchun) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "AI Assistant Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
# Muhit o'zgaruvchilaridan kerakli kalitlarni olish
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN muhit o'zgaruvchisi topilmadi!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY muhit o'zgaruvchisi topilmadi!")

# Google Gemini modelini sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Loglashni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- BOT FUNKSIYALARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchini kutib oladi."""
    user = update.effective_user
    await update.message.reply_html(
        f"Salom, {user.mention_html()}!\n\n"
        f"Men sizning shaxsiy AI yordamchingizman. Menga istalgan savolingizni berishingiz mumkin. "
        f"Suhbat tarixini tozalash uchun /clear buyrug'ini yuboring."
    )
    # Foydalanuvchi uchun suhbat tarixini bo'sh holatda yaratish
    context.user_data['history'] = []


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Suhbat tarixini tozalaydi."""
    context.user_data['history'] = []
    await update.message.reply_text("Suhbat tarixi tozalandi. Yangidan boshlashimiz mumkin!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchidan kelgan matnli xabarlarni qayta ishlaydi."""
    user_message = update.message.text
    user_id = update.effective_user.id

    # "Yozmoqda..." statusini ko'rsatish
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # Foydalanuvchi uchun suhbat tarixini olish yoki yaratish
        if 'history' not in context.user_data:
            context.user_data['history'] = []
        
        chat_history = context.user_data['history']

        # Suhbatni boshlash
        chat = model.start_chat(history=chat_history)
        
        # Gemini'dan javobni olish
        response = await chat.send_message_async(user_message)
        
        # Javobni foydalanuvchiga yuborish
        await update.message.reply_text(response.text)
        
        # Suhbat tarixini yangilash
        context.user_data['history'] = chat.history

    except Exception as e:
        logger.error(f"Error handling message for user {user_id}: {e}")
        await update.message.reply_text("Kechirasiz, javob berishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")


# --- ASOSIY FUNKSIYA ---
def main() -> None:
    # Veb-serverni alohida oqimda ishga tushirish
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Botni ishga tushirish
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("AI Assistant Bot ishga tushdi...")
    application.run_polling()


if __name__ == "__main__":
    main()
