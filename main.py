import os
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# 1. Muhit o'zgaruvchilarini Render'dan o'qib olish
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Render avtomatik taqdim etadigan PORT (bepul tarifda odatda 10000 yoki o'zgaruvchan)
PORT = int(os.getenv("PORT", 8000))

# Webhook yo'lagi (Telegram yangiliklarni shu manzilga yuboradi)
WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

# Logger sozlamalari (Render jurnallarida xatoliklarni ko'rish uchun)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Bot va Routerlarni yaratish
router = Router()
dp = Dispatcher()
dp.include_router(router)

# /start komandasi uchun handler
@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(f"Salom, {message.from_user.full_name}! Kino bot muvaffaqiyatli ulindi va Render'da ishlamoqda! 🎬")

# Bot ishga tushganda bajariladigan funksiya (Webhookni Telegramga ro'yxatdan o'tkazish)
async def on_startup(bot: Bot) -> None:
    logging.info(f"Webhook sozlanmoqda: {BASE_URL}")
    await bot.set_webhook(url=BASE_URL)

def main() -> None:
    # Bot obyektini yaratish
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)

    # Dispatcherga start funksiyasini biriktirish
    dp.startup.register(on_startup)

    # aiohttp veb ilovasini yaratish
    app = web.Application()

    # Telegram so'rovlarini qayta ishlovchi handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    # So'rov keladigan yo'lakni ro'yxatdan o'tkazish
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Ilovaga bot va dispatcher muhitini sozlash
    setup_application(app, dp, bot=bot)

    # Render talab qiladigan port va hostda serverni ishga tushirish
    logging.info(f"Server {PORT}-portda ishga tushmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
