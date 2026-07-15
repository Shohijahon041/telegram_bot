import os
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# 1. Muhit o'zgaruvchilarini Render panelidan o'qib olish
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

router = Router()
dp = Dispatcher()
dp.include_router(router)

# 📣 SIZNING KANALINGIZ USERNAME-SI (Bot kanalizda admin bo'lishi shart!)
CHANNEL_ID = "@super_kino_yukla_film" 

# /start buyrug'i kelganda
@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"Salom, {message.from_user.full_name}! 🎬\n\n"
        f"Kino kodini yuboring va men uni kanaldan topib beraman!"
    )

# BOSH SAHIFA UCHUN HANDLER (UptimeRobot uchun 200 OK qaytaradi va uxlashdan asraydi)
async def index_handler(request):
    return web.Response(text="Bot is active and running! 🚀", content_type="text/plain")

# Foydalanuvchi kod (raqam) yuborganda ishlaydigan qidiruv tizimi
@router.message()
async def search_movie_in_channel(message: types.Message, bot: Bot) -> None:
    msg_text = message.text.strip()
    
    # Faqat raqamlardan iborat kino kodi bo'lsa
    if msg_text.isdigit():
        try:
            # Kanaldagi xabar ID-si foydalanuvchi yuborgan kodga teng deb olamiz
            movie_message_id = int(msg_text) 
            
            # Xabarni foydalanuvchiga yo'naltirish (Forward)
            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=movie_message_id
            )
            
        except Exception as e:
            logging.error(f"Kino topishda xatolik: {e}")
            await message.answer("😔 Kechirasiz, ushbu kod bilan kino topilmadi yoki bot kanalga admin qilinmagan. Kodni to'g'ri kiritganingizni tekshiring.")
    else:
        await message.answer("Iltimos, kino yuklab olish uchun faqat kino kodini (raqam) kiriting.")

async def on_startup(bot: Bot) -> None:
    logging.info(f"Webhook sozlanmoqda: {BASE_URL}")
    await bot.set_webhook(url=BASE_URL)

def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.startup.register(on_startup)

    app = web.Application()
    
    # Bosh sahifa yo'lagini ulash
    app.router.add_get('/', index_handler)

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logging.info(f"Server {PORT}-portda faollashtirilmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
