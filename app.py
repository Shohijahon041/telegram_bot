import os
import logging
import sys
import re
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from motor.motor_asyncio import AsyncIOMotorClient

# 1. Sozlamalar va Atrof-muhit o'zgaruvchilari
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.getenv("PORT", 8000))

# ADMIN ID-SI (Bu yerga Telegram ID-raqamingizni yozing)
ADMIN_ID = 5372439160  

WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. Baza Ulanishi
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["kino_bot_db"]
movies_collection = db["movies"]
users_collection = db["users"]

router = Router()
dp = Dispatcher()
dp.include_router(router)

TARGET_CHANNEL_USERNAME = "super_kino_yukla_film"
CHANNEL_CHAT_ID = "@super_kino_yukla_film"

# FOYDALANUVCHI PROFILINI YARATISH VA KUZATISH
@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    full_name = message.from_user.full_name

    # Foydalanuvchini bazaga qo'shish yoki yangilash
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "full_name": full_name,
            "last_active": datetime.utcnow()
        }, "$setOnInsert": {"joined_at": datetime.utcnow(), "searches": []}},
        upsert=True
    )

    await message.answer(
        f"Salom, {full_name}! 🎬\n\n"
        f"Kino yoki Serial kodini yuboring, men uni zudlik bilan topib beraman!\n\n"
        f"👤 /profile - Profilingizni ko'rish"
    )

# FOYDALANUVCHI PROFILI
@router.message(Command("profile"))
async def user_profile_handler(message: types.Message) -> None:
    user = await users_collection.find_one({"user_id": message.from_user.id})
    if user:
        joined = user.get("joined_at", datetime.utcnow()).strftime("%Y-%m-%d")
        searches_count = len(user.get("searches", []))
        await message.answer(
            f"👤 **Sizning Profilingiz:**\n\n"
            f"🆔 ID: `{message.from_user.id}`\n"
            f"📅 Ro'yxatdan o'tilgan sana: {joined}\n"
            f"🔍 Jami qidirilgan kinolar: {searches_count} ta"
        )

# ADMIN PANEL buyrug'i
@router.message(Command("admin"))
async def admin_panel_handler(message: types.Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    users_count = await users_collection.count_documents({})
    movies_count = await movies_collection.count_documents({})

    await message.answer(
        f"📊 **Bot Boshqaruv Paneli (Admin):**\n\n"
        f"👥 Jami foydalanuvchilar: {users_count} ta\n"
        f"🎬 Jami kinolar soni: {movies_count} ta\n\n"
        f"📢 **Reklama yuborish uchun:**\n"
        f"`/send reklama_matni` buyrug'idan foydalaning."
    )

# REKLAMA TARQATISH FUNKSIYASI (SEND ALL)
@router.message(Command("send"))
async def send_all_handler(message: types.Message, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    text_to_send = message.text.replace("/send", "").strip()
    if not text_to_send:
        await message.answer("Iltimos, reklama matnini yozing. Masalan: `/send Yangi kino yuklandi!`")
        return

    users = users_collection.find({})
    success = 0
    failed = 0

    async for user in users:
        try:
            await bot.send_message(chat_id=user["user_id"], text=text_to_send)
            success += 1
        except Exception:
            failed += 1

    await message.answer(f"📢 Reklama yakunlandi:\n✅ Yuborildi: {success}\n❌ Taqiqlangan/Xato: {failed}")

# KANALGA FORWARD QILINGANDA CAPTIONNI TO'G'RILASH VA SAQLASH
@router.channel_post()
async def auto_save_channel_post(channel_post: types.Message):
    ch_username = (channel_post.chat.username or "").lower()
    
    if TARGET_CHANNEL_USERNAME in ch_username:
        text = channel_post.caption or channel_post.text or ""
        logging.info("Kanalga post keldi, tahrirlanmoqda...")

        # Matndan ma'lumotlarni qidirish (Regex yordamida)
        movie_code = re.search(r'(?:Kod|ID):\s*(\d+)', text, re.IGNORECASE)
        yili = re.search(r'Yili:\s*([^\n]+)', text, re.IGNORECASE)
        tili = re.search(r'Tili:\s*([^\n]+)', text, re.IGNORECASE)
        janri = re.search(r'Janri:\s*([^\n]+)', text, re.IGNORECASE)
        sifati = re.search(r'Sifati:\s*([^\n]+)', text, re.IGNORECASE)
        hajmi = re.search(r'Hajmi:\s*([^\n]+)', text, re.IGNORECASE)
        bahosi = re.search(r'Bahosi:\s*([^\n]+)', text, re.IGNORECASE)
        tavsif = re.search(r'Tavsif\s*📝\s*([^\n]+)', text, re.IGNORECASE)

        if movie_code:
            code = movie_code.group(1)
            
            # Yangi tozalangan, chiroyli matn shakli
            cleaned_caption = (
                f"🎬 **Yangi film joylandi!**\n\n"
                f"🔑 **Kodi:** {code}\n"
                f"📅 **Yili:** {yili.group(1) if yili else 'Noma`lum'}\n"
                f"🇺🇿 **Tili:** {tili.group(1) if tili else 'O`zbekcha'}\n"
                f"🎭 **Janri:** {janri.group(1) if janri else 'Drama'}\n"
                f"💿 **Sifati:** {sifati.group(1) if sifati else '720p'}\n"
                f"💾 **Hajmi:** {hajmi.group(1) if hajmi else 'Noma`lum'}\n"
                f"⭐️ **Bahosi:** {bahosi.group(1) if bahosi else 'Yaxshi'}\n\n"
                f"📝 **Tavsif:** {tavsif.group(1) if tavsif else 'Film tavsifi mavjud emas.'}\n\n"
                f"📥 Botdan olish uchun kodni yuboring!"
            )

            # Bazaga saqlash va fayllar ro'yxatini to'plash (Birlashtirish)
            await movies_collection.update_one(
                {"movie_code": code},
                {
                    "$set": {"text": cleaned_caption},
                    "$addToSet": {"message_ids": channel_post.message_id}
                },
                upsert=True
            )
            logging.info(f"Yangi kino/qism bazaga muvaffaqiyatli saqlandi! Kod: {code}")

# FOYDALANUVCHILAR QIDIRGANDA FILMNI TAQDIM ETISH (FORWARD TAQIQLANGAN)
@router.message()
async def search_movie_handler(message: types.Message, bot: Bot) -> None:
    msg_text = message.text.strip()
    user_id = message.from_user.id
    
    if msg_text.isdigit():
        movie = await movies_collection.find_one({"movie_code": msg_text})
        
        if movie:
            # Foydalanuvchi qidiruv tarixini yangilash
            await users_collection.update_one(
                {"user_id": user_id},
                {"$addToSet": {"searches": msg_text}, "$set": {"last_active": datetime.utcnow()}}
            )

            # Birlashtirilgan barcha xabar ID-larini yuborish (Seriallar yoki har xil hajmdagi kinolar uchun)
            message_ids = movie.get("message_ids", [])
            if not message_ids and "message_id" in movie:
                message_ids = [movie["message_id"]]

            for msg_id in message_ids:
                try:
                    # 🔐 PROTECT CONTENT = True: Forward qilish, saqlash va screenshot butunlay taqiqlanadi!
                    await bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=CHANNEL_CHAT_ID,
                        message_id=msg_id,
                        protect_content=True
                    )
                except Exception as e:
                    logging.error(f"Kino yuborishda xato: {e}")
                    await message.answer("😔 Afsuski, kinoni yuborib bo'lmadi. Kanal o'chgan yoki bot adminlikdan ketgan bo'lishi mumkin.")
        else:
            await message.answer("😔 Kechirasiz, ushbu kod bilan kino topilmadi.")
    else:
        await message.answer("Iltimos, faqat kino kodini (raqam) yuboring.")

async def index_handler(request):
    return web.Response(text="Bot is Active and Upgraded! 🚀", content_type="text/plain")

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
