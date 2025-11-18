import os
import sqlite3
import asyncio
import re
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv

# Environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
MOVIE_CHANNEL_ID = os.getenv('MOVIE_CHANNEL_ID', '-1003134037650')
INSTAGRAM_LINK = os.getenv('INSTAGRAM_LINK', 'https://instagram.com/your_profile')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Database funksiyalari
def init_db():
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS kino(
        id TEXT PRIMARY KEY,
        file_id TEXT,
        name TEXT,
        date TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS config(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_channel(channel_id):
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("INSERT INTO channels(channel_id) VALUES(?)", (channel_id,))
    conn.commit()
    conn.close()

def list_channels():
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("SELECT channel_id FROM channels")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def save_kino(code, file_id, name):
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO kino(id, file_id, name, date) VALUES(?,?,?,datetime('now'))", (code, file_id, name))
    conn.commit()
    conn.close()

def get_kino(code):
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("SELECT file_id, name FROM kino WHERE id=?", (code,))
    row = c.fetchone()
    conn.close()
    return row

def record_log(user_id, action):
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs(user_id, action, date) VALUES(?,?,datetime('now'))", (user_id, action))
    conn.commit()
    conn.close()

# Bazani boshlash
init_db()

def generate_code(message_id: int) -> str:
    return f"K{message_id}"

# Obuna tekshirish funksiyasi
async def check_subscriptions(user_id: int) -> bool:
    rows = list_channels()
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

# Admin panel komandasi
@dp.message(Command(commands=["admin"]))
async def admin_panel(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    text = ("Admin panel:\n"
            "/addchannel <channel_id> - kanal qo'shish\n"
            "/listchannels - kanallar ro'yxati\n"
            "/setinsta <link> - Instagram linki\n"
            "Botga video yoki hujjat yuborsangiz, kino avtomatik qo'shiladi.")
    await message.answer(text)

# Kanal qo'shish
@dp.message(Command(commands=["addchannel"]))
async def add_channel_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Iltimos kanal username yoki ID kiriting.")
        return
    channel = parts[1].strip()
    add_channel(channel)
    await message.answer(f"✅ Kanal qo'shildi: {channel}")

# Kanallar roʻyxati
@dp.message(Command(commands=["listchannels"]))
async def list_channels_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    rows = list_channels()
    if not rows:
        await message.answer("Hozircha kanal yoʻq.")
        return
    text = "Kanallar:\n" + "\n".join(rows)
    await message.answer(text)

# Instagram linkini sozlash
@dp.message(Command(commands=["setinsta"]))
async def set_insta_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Iltimos Instagram link kiriting.")
        return
    link = parts[1].strip()
    conn = sqlite3.connect("kino.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config(key, value) VALUES(?,?)", ("insta", link))
    conn.commit()
    conn.close()
    await message.answer("Instagram link o'rnatildi.")

# Admin tomonidan kino qo'shiladi
@dp.message()
async def catch_movie(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        await handle_user_message(message)
        return
    if message.video or message.document:
        file_id = message.video.file_id if message.video else message.document.file_id
        name = message.caption or f"Movie {message.message_id}"
        code = generate_code(message.message_id)
        save_kino(code, file_id, name)
        await message.answer(f"🎬 Kino saqlandi! KOD: {code}")
        return
    return

# Foydalanuvchi kodi yuborsa
async def handle_user_message(message: Message):
    text = (message.text or "").strip()
    # Regex ni tuzatamiz
    if re.match(r"^K\d+$", text.upper()):
        code = text.upper()
        row = get_kino(code)
        if not row:
            await message.answer("❌ Bunday kod topilmadi.")
            return
        if not await check_subscriptions(message.from_user.id):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Instagram", url=INSTAGRAM_LINK)],
                [InlineKeyboardButton(text="⏺ Obuna tekshirish", callback_data="check_subs")]
            ])
            await message.answer("Iltimos kanal(lar)ga obuna bo'ling va keyin «Obuna tekshirish» tugmasini bosing.", reply_markup=kb)
            return
        file_id, name = row
        try:
            await bot.send_video(message.chat.id, file_id, caption=name)
        except Exception:
            try:
                await bot.send_document(message.chat.id, file_id, caption=name)
            except Exception:
                await message.answer("Kino yuborishda xato. Iltimos admin bilan bog'laning.")
        record_log(message.from_user.id, f"sent_movie_{code}")
        return
    await message.answer("Iltimos kino kodi yuboring (masalan: K123).")

@dp.callback_query(lambda c: c.data == "check_subs")
async def cb_check_subs(callback):
    ok = await check_subscriptions(callback.from_user.id)
    if ok:
        chs = list_channels()
        for ch in chs:
            record_log(callback.from_user.id, f"subscribed_{ch}")
        await callback.message.answer("✔️ Obuna tasdiqlandi. Endi kino kodi yuboring.")
    else:
        await callback.answer("❌ Hali obuna emassiz.", show_alert=True)

async def main():
    try:
        print("Bot ishlamoqda...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Xato: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
