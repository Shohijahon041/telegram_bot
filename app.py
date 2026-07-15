import os
from flask import Flask, request
import telebot

# Render-dagi KINO_BOT_TOKEN muhit o'zgaruvchisini o'qiymiz
BOT_TOKEN = os.environ.get('KINO_BOT_TOKEN')
# Render sizga bergan sayt manzili: https://telegram-bot-6zm1.onrender.com
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Telegram'dan keladigan xabarlarni qabul qilish uchun route
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Webhook'ni sozlash va bot holatini tekshirish uchun bosh sahifa
@app.route("/")
def webhook():
    bot.remove_webhook()
    # Webhook manzilini Telegram serveriga bog'laymiz
    bot.set_webhook(url=WEBHOOK_URL + '/' + BOT_TOKEN)
    return "Webhook muvaffaqiyatli sozlandi va kino botingiz faol!", 200

# --- KINO BOTINGIZNING ASOSIY FUNKSIYALARI ---
# (Siz o'z botingiz funksiyalarini aynan shu qismga yozishingiz mumkin)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Assalomu alaykum! Kino botimizga xush kelibsiz! 🎬\n\nMen Render serverida 24/7 rejimda ishlamoqdaman.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Siz yuborgan xabar: {message.text}\nTez orada bu yerga kino qidirish tizimi ulanadi!")

# --- SERVERNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
