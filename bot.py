import sqlite3
import asyncio
import re
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import TOKEN, ADMIN_ID, MOVIE_CHANNEL_ID, INSTAGRAM_LINK
import database

bot = Bot(token=TOKEN)
dp = Dispatcher()

# DB init
database.init_db()

def generate_code(message_id: int) -> str:
    return f"K{message_id}"

# Obuna tekshirish
async def check_subscriptions(user_id: int) -> bool:
    rows = database.list_channels()
    if not rows:
        return True
    for ch in rows:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True

# Admin komandalar
@dp.message(Command(commands=["admin"]))
async def admin_panel(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return
    text = ("Admin panel:\n"
            "/addchannel <channel_id> - qo'shish\n"
            "/listchannels - ro'yxat\n"
            "/setinsta <link> - instagram link\n"
            "Video/document yuborsangiz kino avtomatik saqlanadi.")
    await message.answer(text)

@dp.message(Command(commands=["addchannel"]))
async def add_channel_cmd(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Iltimos kanal username yoki ID kiriting.")
        return
    channel = parts[1].strip()
    database.add_channel(channel)
    await message.answer(f"✅ Kanal qo'shildi: {channel}")

@dp.message(Command(commands=["listchannels"]))
async def list_channels_cmd(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return
    rows = database.list_channels()
    if not rows:
        await message.answer("Hozircha kanal yo'q.")
        return
    text = "Kanallar:\n" + "\n".join(rows)
    await message.answer(text)

@dp.message(Command(commands=["setinsta"]))
async def set_insta_cmd(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Iltimos instagram link kiriting.")
        return
    link = parts[1].strip()
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config(key, value) VALUES(?,?)", ("insta", link))
    conn.commit()
    conn.close()
    await message.answer("Instagram link o'rnatildi.")

# Admin kino yuboradi
@dp.message()
async def catch_movie(message: Message):
    if message.from_user.id != int(ADMIN_ID):
        await handle_user_message(message)
        return
    if message.video or message.document:
        file_id = message.video.file_id if message.video else message.document.file_id
        name = message.caption or f"Movie {message.message_id}"
        code = generate_code(message.message_id)
        database.save_kino(code, file_id, name)
        await message.answer(f"🎬 Kino saqlandi! KOD: {code}")
        return
    return

async def handle_user_message(message: Message):
    text = (message.text or "").strip()
    if re.match(r"^K\d+$", text.upper()):
        code = text.upper()
        row = database.get_kino(code)
        if not row:
            await message.answer("❌ Bunday kod topilmadi.")
            return
        if not await check_subscriptions(message.from_user.id):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Instagram", url=INSTAGRAM_LINK or "https://instagram.com")],
                [InlineKeyboardButton(text="⏺ Obuna tekshirish", callback_data="check_subs")]
            ])
            await message.answer("Iltimos kanal(lar)ga obuna bo'ling va keyin tekshirish tugmasini bosing.", reply_markup=kb)
            return
        file_id, name = row
        try:
            await bot.send_video(message.chat.id, file_id, caption=name)
        except Exception:
            try:
                await bot.send_document(message.chat.id, file_id, caption=name)
            except Exception:
                await message.answer("Kino yuborishda xatolik yuz berdi. Iltimos admin bilan bog'laning.")
        database.record_log(message.from_user.id, f"sent_movie_{code}")
        return
    await message.answer("Iltimos kino kodi yuboring (masalan: K123).")

@dp.callback_query(lambda c: c.data == "check_subs")
async def cb_check_subs(callback):
    ok = await check_subscriptions(callback.from_user.id)
    if ok:
        chs = database.list_channels()
        for ch in chs:
            database.record_log(callback.from_user.id, f"subscribed_{ch}")
        await callback.message.answer("✔️ Obuna tasdiqlandi. Endi kino kodi yuboring.")
    else:
        await callback.answer("❌ Hali obuna emassiz.", show_alert=True)

async def main():
    try:
        print("Bot ishlamoqda...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
