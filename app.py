import os
from flask import Flask, request
import telebot

# Environment Variables (Muhit o'zgaruvchilari) orqali ma'lumotlarni olamiz
KINO_BOT_TOKEN = os.environ.get('KINO_BOT_TOKEN')
# Render sizga beradigan sayt manzili (masalan: https://mening-botim.onrender.com)
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

bot = telebot.TeleBot(KINO_BOT_TOKEN)
app = Flask(__name__)

# Telegram'dan keladigan xabarlarni qabul qilish
@app.route('/' + KINO_BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Webhook'ni sozlash va tekshirish uchun bosh sahifa
@app.route("/")
def webhook():
    bot.remove_webhook()
    # Webhook manzilini Telegram'ga bog'laymiz
    bot.set_webhook(url=WEBHOOK_URL + '/' + KINO_BOT_TOKEN)
    return "Webhook muvaffaqiyatli sozlandi va bot faol!", 200

# --- BOT FUNKSIYALARI (Buyruqlar) ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Salom! Men Render serverida 24/7 ishlovchi botman. 🚀")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Siz yozdingiz: {message.text}")

# --- SERVERNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    # Render avtomatik ravishda PORT muhit o'zgaruvchisini taqdim etadi
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
