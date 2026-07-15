import os
import logging
import sys
import re
import asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.utils.keyboard import InlineKeyboardBuilder
from motor.motor_asyncio import AsyncIOMotorClient

# 1. Konfiguratsiya
TOKEN = os.getenv("KINO_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.getenv("PORT", 8000))

# Admin Telegram ID-ingiz
ADMIN_ID = 5372439160  

# Webhook yo'lini oddiy va xatosiz qilamiz
WEBHOOK_PATH = "/webhook"
BASE_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# 2. Baza ulanishi
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["kino_bot_db"]
movies_collection = db["movies"]
users_collection = db["users"]
counters_collection = db["counters"]

router = Router()
dp = Dispatcher()
dp.include_router(router)

CHANNEL_CHAT_ID = "@super_kino_yukla_film"
BOT_LINK = "https://t.me/super_kino_yukla_bot" 

# KINO KODINI AVTOMATIK GENERATSIYA QILISH
async def get_next_movie_code() -> str:
    counter = await counters_collection.find_one_and_update(
        {"_id": "movie_code"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    if counter.get("sequence_value") == 1:
        await counters_collection.update_one({"_id": "movie_code"}, {"$set": {"sequence_value": 3765}})
        return "3765"
    return str(counter["sequence_value"])

# FOYDALANUVCHINI BAZAGA QO'SHISH
async def register_user(user: types.User):
    await users_collection.update_one(
        {"user_id": user.id},
        {"$set": {
            "username": user.username or "No Username",
            "full_name": user.full_name,
            "last_active": datetime.utcnow()
        }, "$setOnInsert": {"joined_at": datetime.utcnow(), "searches": []}},
        upsert=True
    )

# MATNNI TOZALASH VA FORMATLASH
def format_caption(text: str, code: str) -> str:
    if not text:
        return f"🎬 **Yangi Film**\n━━━━━━━━━━━━━━━━━━━\n🔑 **Kino Kodi:** `{code}`\n━━━━━━━━━━━━━━━━━━━\n📥 Yuklab olish: {BOT_LINK}"
    
    clean_text = re.sub(r'https?://\S+|www\.\S+|@\S+', '', text).strip()
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    title = lines[0] if lines else "Yangi Film"
    title = re.sub(r'[^\w\s\d\-\(\)\[\]«»"\'\.\,а-яА-ЯёЁўқғҳЎҚҒҲ]', '', title).strip()

    yili = re.search(r'(?:Yili|Yil):\s*([^\n]+)', clean_text, re.IGNORECASE)
    tili = re.search(r'(?:Tili|Til):\s*([^\n]+)', clean_text, re.IGNORECASE)
    janri = re.search(r'(?:Janri|Janr):\s*([^\n]+)', clean_text, re.IGNORECASE)
    sifati = re.search(r'(?:Sifati|Sifat):\s*([^\n]+)', clean_text, re.IGNORECASE)
    hajmi = re.search(r'(?:Hajmi|Hajm):\s*([^\n]+)', clean_text, re.IGNORECASE)
    bahosi = re.search(r'(?:Bahosi|Reyting):\s*([^\n]+)', clean_text, re.IGNORECASE)
    
    if not yili and len(lines) > 1:
        tavsif_text = " ".join(lines[1:4])
    else:
        tavsif = re.search(r'(?:Tavsif|Tavsifi):\s*([^\n]+)', clean_text, re.IGNORECASE)
        tavsif_text = tavsif.group(1).strip() if tavsif else "Ajoyib kino, tomosha qilishni tavsiya etamiz!"

    return (
        f"🎬 **{title}**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 **Kino Kodi:** `{code}`\n"
        f"📅 **Yili:** {yili.group(1).strip() if yili else 'Noma`lum'}\n"
        f"🇺🇿 **Tili:** {tili.group(1).strip() if tili else 'O`zbekcha'}\n"
        f"🎭 **Janri:** {janri.group(1).strip() if janri else 'Drama, Sarguzasht'}\n"
        f"💿 **Sifati:** {sifati.group(1).strip() if sifati else '720p HD'}\n"
        f"💾 **Hajmi:** {hajmi.group(1).strip() if hajmi else 'Noma`lum'}\n"
        f"⭐️ **Bahosi:** {bahosi.group(1).strip() if bahosi else 'Yaxshi 🍿'}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **Tavsif:** {tavsif_text}\n\n"
        f"📥 Kinoni yuklab olish uchun botimizga kiring:\n👉 {BOT_LINK}"
    )

@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await register_user(message.from_user)
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Profilim", callback_data="btn_profile")
    if message.from_user.id == ADMIN_ID:
        builder.button(text="📊 Admin Panel", callback_data="btn_admin")
    builder.adjust(1)
    await message.answer(f"Salom, {message.from_user.full_name}! 👋\n\nKino kodini yuboring!", reply_markup=builder.as_markup())

@router.callback_query(F.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    user = await users_collection.find_one({"user_id": callback.from_user.id})
    if user:
        joined = user.get("joined_at", datetime.utcnow()).strftime("%Y-%m-%d")
        searches_count = len(user.get("searches", []))
        await callback.message.edit_text(f"👤 **Profilingiz:**\n\n🆔 ID: `{callback.from_user.id}`\n📅 A'zo: {joined}\n🔍 Qidiruvlar: {searches_count} ta")

@router.callback_query(F.data == "btn_admin")
async def cb_admin(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    users_count = await users_collection.count_documents({})
    movies_count = await movies_collection.count_documents({})
    await callback.message.edit_text(f"📊 **Admin Panel:**\n\n👥 A'zolar: {users_count} ta\n🎬 Kinolar: {movies_count} ta")

# FORWARD BO'LGAN KINOLARNI QABUL QILISH VA BAZAGA YOZISH
@router.message(F.video | F.document)
async def process_admin_movie_forward(message: types.Message, bot: Bot):
    # Har doim ADMIN yuborganini chat darajasida qat'iy tekshiramiz
    if message.chat.id != ADMIN_ID:
        return

    old_caption = message.caption or ""
    new_code = await get_next_movie_code()
    new_caption = format_caption(old_caption, new_code)
    
    status_msg = await message.answer(f"⏳ Kino kanalga va bazaga yuklanmoqda...")

    try:
        if message.video:
            channel_msg = await bot.send_video(chat_id=CHANNEL_CHAT_ID, video=message.video.file_id, caption=new_caption, parse_mode=ParseMode.MARKDOWN)
        else:
            channel_msg = await bot.send_document(chat_id=CHANNEL_CHAT_ID, document=message.document.file_id, caption=new_caption, parse_mode=ParseMode.MARKDOWN)

        # Muvaffaqiyatli MongoDB ga yozish
        await movies_collection.update_one(
            {"movie_code": new_code},
            {
                "$set": {
                    "text": new_caption,
                    "message_id": channel_msg.message_id,
                    "file_id": message.video.file_id if message.video else message.document.file_id,
                    "created_at": datetime.utcnow()
                },
                "$addToSet": {"message_ids": channel_msg.message_id}
            },
            upsert=True
        )
        await status_msg.edit_text(f"✅ Muvaffaqiyatli bajarildi!\n🔑 Kino Kodi: `{new_code}`\n📡 Baza va kanalga saqlandi!")
        
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await status_msg.edit_text(f"❌ Xatolik yuz berdi. Bot kanalda admin ekanligini tekshiring.")

@router.message()
async def search_movie_handler(message: types.Message, bot: Bot) -> None:
    msg_text = message.text.strip()
    user_id = message.from_user.id
    
    if msg_text.isdigit():
        movie = await movies_collection.find_one({"movie_code": msg_text})
        if movie:
            await users_collection.update_one({"user_id": user_id}, {"$addToSet": {"searches": msg_text}, "$set": {"last_active": datetime.utcnow()}})
            message_ids = movie.get("message_ids", [movie.get("message_id")])
            for msg_id in message_ids:
                if msg_id:
                    try: await bot.copy_message(chat_id=user_id, from_chat_id=CHANNEL_CHAT_ID, message_id=msg_id, protect_content=True)
                    except: pass
        else:
            await message.answer("😔 Kechirasiz, ushbu kod bilan kino topilmadi.")
    else:
        await message.answer("Iltimos, faqat kino kodini (raqam) yuboring.")

async def index_handler(request):
    return web.Response(text="Bot runs perfectly! 🚀", content_type="text/plain")

async def on_startup(bot: Bot) -> None:
    # ⚠️ MUHIM: Telegramga eski noto'g'ri webhooklarni o'chirishni va yangisini o'rnatishni buyuramiz
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)
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
