import os
import logging
import sys
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from motor.motor_asyncio import AsyncIOMotorClient

# 1. Sozlamalarni yuklash
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.getenv("PORT", 8000))

WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. Baza ulanishi
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["kino_bot_db"]
movies_collection = db["movies"]

router = Router()
dp = Dispatcher()
dp.include_router(router)

# Kanalingiz username-i (@ belgisiz toza matn holatida tekshirish uchun)
TARGET_CHANNEL_USERNAME = "super_kino_yukla_film"
CHANNEL_CHAT_ID = "@super_kino_yukla_film" 

@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"Salom, {message.from_user.full_name}! 🎬\n\n"
        f"Kino kodini yuboring, men uni zudlik bilan topib beraman!"
    )

# KANALGA YANGI POST TASHALGANIDA UNI AVTOMATIK BAZAGA YOZISH
@router.channel_post()
async def auto_save_channel_post(channel_post: types.Message):
    # Kanal username-ini tekshirish (kichik harflarda)
    ch_username = (channel_post.chat.username or "").lower()
    
    if TARGET_CHANNEL_USERNAME in ch_username or channel_post.chat.title:
        text = channel_post.caption or channel_post.text or ""
        logging.info(f"Kanalga post keldi, matn: {text[:50]}...")
        
        # Matn ichidan "Kod: 3764" shaklidagi raqamni qidirib topish
        match = re.search(r'(?:Kod|ID):\s*(\d+)', text, re.IGNORECASE)
        if match:
            movie_code = match.group(1)
            # Bazaga saqlash yoki yangilash
            await movies_collection.update_one(
                {"movie_code": movie_code},
                {"$set": {"message_id": channel_post.message_id, "text": text}},
                upsert=True
            )
            logging.info(f"Yangi kino bazaga MUVAFFAQIYATLI qo'shildi! Kod: {movie_code}")
        else:
            logging.warning("Post keldi, lekin ichidan 'Kod: raqam' topilmadi!")

# FOYDALANUVCHI KOD YUBORGANIDA BAZADAN QIDIRISH
@router.message()
async def search_movie_handler(message: types.Message, bot: Bot) -> None:
    msg_text = message.text.strip()
    
    if msg_text.isdigit():
        # Bazadan kodni qidirish
        movie = await movies_collection.find_one({"movie_code": msg_text})
        
        if movie:
            try:
                # Agar baza ichidan topilsa, o'sha xabarni to'g'ridan-to'g'ri forward qilish
                await bot.forward_message(
                    chat_id=message.chat.id,
                    from_chat_id=CHANNEL_CHAT_ID,
                    message_id=movie["message_id"]
                )
            except Exception as e:
                logging.error(f"Forward xatoligi: {e}")
                await message.answer("😔 Kinoni yuborishda xatolik yuz berdi. Bot kanalda admin ekanligini va xabar o'chib ketmaganini tekshiring.")
        else:
            await message.answer("😔 Kechirasiz, ushbu kod bilan hech qanday kino topilmadi.")
    else:
        await message.answer("Iltimos, faqat kino kodini (raqam) kiriting.")

async def index_handler(request):
    return web.Response(text="Bot is active with MongoDB! 🚀", content_type="text/plain")

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(url=BASE_URL)

def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.startup.register(on_startup)

    app = web.Application()
    app.router.add_get('/', index_handler)

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
