import os
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# 1. Muhit o'zgaruvchilarini Render panelidan o'qib olish
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Render avtomatik ravishda PORT taqdim etadi
PORT = int(os.getenv("PORT", 8000))

# Webhook manzili (Telegram bot yangiliklarni shu yo'lga yuboradi)
WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Loglarni Render konsolida ko'rish uchun sozlama
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot, Router va Dispatcherlarni sozlash
router = Router()
dp = Dispatcher()
dp.include_router(router)

# /start buyrug'i kelganda ishlaydigan kod
@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"Salom, {message.from_user.full_name}! 🎬\n\n"
        f"Kino botingiz muvaffaqiyatli ishga tushdi va Render platformasida webhook orqali faol ishlamoqda!"
    )

# Bot ishga tushganda webhookni Telegram tizimida ro'yxatdan o'tkazish
async def on_startup(bot: Bot) -> None:
    logging.info(f"Webhook sozlanmoqda: {BASE_URL}")
    await bot.set_webhook(url=BASE_URL)

def main() -> None:
    # YANGI AIOGRAM STANDARTI: parse_mode'ni DefaultBotProperties orqali uzatamiz
    bot = Bot(
        token=TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Ishga tushish funksiyasini ulash
    dp.startup.register(on_startup)

    # aiohttp veb-server dasturini yaratish
    app = web.Application()

    # Webhook so'rovlarini boshqaruvchi handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Dispatcher va bot sozlamalarini aiohttp'ga ulash
    setup_application(app, dp, bot=bot)

    # Render uchun maxsus portda serverni ishga tushirish
    logging.info(f"Server {PORT}-portda faollashtirilmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
