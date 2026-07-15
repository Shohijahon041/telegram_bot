import os
import logging
import sys
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

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

# 📣 SIZNING KANALINGIZ USERNAME yoki ID-SI
# Diqqat: Bot kanalga admin bo'lishi shart!
CHANNEL_ID = "@super_kino_yukla_film" 

# /start buyrug'i
@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"Salom, {message.from_user.full_name}! 🎬\n\n"
        f"Kino kodini yuboring va men uni kanaldan topib beraman!"
    )

# Foydalanuvchi kod yuborganda ishlaydigan asosiy qidiruv tizimi
@router.message()
async def search_movie_in_channel(message: types.Message, bot: Bot) -> None:
    msg_text = message.text.strip()
    
    # Faqat raqamlardan iborat kod bo'lsa
    if msg_text.isdigit():
        search_code = msg_text
        await message.answer("🔍 Kino qidirilmoqda, iltimos kuting...")
        
        found = False
        last_message_id = None
        
        try:
            # Kanaldagi oxirgi 100 ta xabarni tekshiramiz (bu sonni ko'paytirish mumkin)
            # Murakkabroq qidiruv uchun kelajakda bazadan foydalanamiz, hozircha eng sodda usul:
            for i in range(1, 200): # Oxirgi 200 ta xabarni skanerlash
                try:
                    # Xabarni ID bo'yicha olib ko'ramiz
                    # Telegramda xabarlar ID ketma-ketligi bo'yicha boradi
                    # Kanalning eng so'nggi xabarlaridan boshlab qidirish samarali
                    pass
                except Exception:
                    continue

            # DIQQAT: Telegram bot API orqali kanal ichidan to'g'ridan-to'g'ri matnli qidiruv cheklanganligi sababli,
            # Eng to'g'ri va xatosiz ishlaydigan variant — Inline Query yoki xabarni to'g'ridan-to'g'ri ID bo'yicha bog'lash.
            
            # Agar siz kinolarni kanalga yuklaganingizda xabar havolasini (Link) bilsangiz juda oson bo'ladi.
            # Kanaldan xabarlarni bittalab skanerlash botni sekinlashtiradi.
            
            # Keling, eng optimal yechimni qilamiz: 
            # Botingiz kanaldan xabarlarni forward qilishi uchun bizga kanaldagi xabar ID-si kod bilan mos kelishi kerak.
            # Masalan, kanaldagi xabar linki: t.me/super_kino_yukla_film/3764 bo'lsa, bot uni darhol topadi!
            
            # Agar sizda kod xabarning ID-siga to'g'ri kelmasa, bizga baribir kichik Baza kerak bo'ladi.
            # Hozircha foydalanuvchiga yordam berish uchun qidiruv logikasini ishga tushiramiz:
            
            # Muqobil variant: Foydalanuvchi kod yuborganda, bot kanaldagi o'sha xabarni topib beradi.
            # Hozircha siz kiritgan kod kanalda xabarning ID raqami bilan mos keladimi? 
            # (Masalan, 3764-xabarmi u?)
            
            # Agar mos kelmasa, eng to'g'ri yo'l kodni Telegram kanalingizdagi xabar ID-siga moslab yuborish:
            movie_message_id = int(search_code) 
            
            # Kanaldagi o'sha xabarni foydalanuvchiga yo'naltirish (Forward)
            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=movie_message_id
            )
            found = True
            
        except Exception as e:
            logging.error(f"Xatolik yuz berdi: {e}")
            
        if not found:
            await message.answer("😔 Kechirasiz, ushbu kod bilan kino topilmadi yoki bot kanalga admin qilinmagan.")
            
    else:
        await message.answer("Iltimos, faqat kino kodini (raqam) kiriting.")

# Bosh sahifa (UptimeRobot uchun)
async def index_handler(request):
    return web.Response(text="Bot is active and running! 🚀", content_type="text/plain")

async def on_startup(bot: Bot) -> None:
    logging.info(f"Webhook sozlanmoqda: {BASE_URL}")
    await bot.set_webhook(url=BASE_URL)

def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.startup.register(on_startup)

    app = web.Application()
    app.router.add_get('/', index_handler)

    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logging.info(f"Server {PORT}-portda faollashtirilmoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
