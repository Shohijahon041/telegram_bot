import os
import sqlite3
import asyncio
import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiohttp import web

# Loggerni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

if not TOKEN or not ADMIN_ID:
    raise ValueError("TOKEN va ADMIN_ID environment variables talab qilinadi")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Database funksiyalari
def init_db():
    conn = sqlite3.connect("kino.db", check_same_thread=False)
    c = conn.cursor()
    
    # Kinolar jadvali
    c.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        movie_name TEXT,
        message_id INTEGER,
        date TEXT
    )
    """)
    
    # Telegram kanallari jadvali
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        channel_name TEXT,
        created_date TEXT
    )
    """)
    
    # Konfiguratsiya jadvali
    c.execute("""
    CREATE TABLE IF NOT EXISTS config(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Loglar jadvali
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        date TEXT
    )
    """)
    
    # Statistika jadvali
    c.execute("""
    CREATE TABLE IF NOT EXISTS stats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        user_id INTEGER,
        action TEXT,
        date TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def add_channel(channel_id, channel_name=""):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO channels(channel_id, channel_name, created_date) VALUES(?,?,?)", 
                  (channel_id, channel_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        logger.info(f"Kanal qo'shildi: {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Kanal qo'shish xatosi: {e}")
        return False

def remove_channel(channel_id):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
        conn.commit()
        conn.close()
        logger.info(f"Kanal o'chirildi: {channel_id}")
        return True
    except Exception as e:
        logger.error(f"Kanal o'chirish xatosi: {e}")
        return False

def list_channels():
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT channel_id, channel_name FROM channels")
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Kanallar ro'yxatini olish xatosi: {e}")
        return []

def get_channel_stats():
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("""
            SELECT channel_id, COUNT(DISTINCT user_id) as user_count 
            FROM stats 
            WHERE action='subscribed' 
            GROUP BY channel_id
        """)
        stats = c.fetchall()
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Statistika olish xatosi: {e}")
        return []

def save_movie(code, movie_name, message_id):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO movies(code, movie_name, message_id, date) VALUES(?,?,?,?)", 
                  (code, movie_name, message_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        logger.info(f"Kino saqlandi: {code} - {movie_name}")
        return True
    except Exception as e:
        logger.error(f"Kino saqlash xatosi: {e}")
        return False

def get_movie(code):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT movie_name, message_id FROM movies WHERE code=?", (code,))
        row = c.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"Kino olish xatosi: {e}")
        return None

def get_all_movies():
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT code, movie_name FROM movies ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Kinolar ro'yxatini olish xatosi: {e}")
        return []

def set_config(key, value):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config(key, value) VALUES(?,?)", (key, value))
        conn.commit()
        conn.close()
        logger.info(f"Config o'rnatildi: {key} = {value}")
        return True
    except Exception as e:
        logger.error(f"Config o'rnatish xatosi: {e}")
        return False

def get_config(key):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT value FROM config WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Config olish xatosi: {e}")
        return None

def record_log(user_id, action):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO logs(user_id, action, date) VALUES(?,?,?)", 
                  (user_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Log yozish xatosi: {e}")

def record_stat(channel_id, user_id, action):
    try:
        conn = sqlite3.connect("kino.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO stats(channel_id, user_id, action, date) VALUES(?,?,?,?)", 
                  (channel_id, user_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Statistika yozish xatosi: {e}")

# Bazani boshlash
init_db()

def generate_code():
    import random
    return f"K{random.randint(1000, 9999)}"

# Obuna tekshirish funksiyasi
async def check_subscriptions(user_id: int) -> bool:
    channels = list_channels()
    if not channels:
        return True
    
    for channel_id, channel_name in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                logger.info(f"Foydalanuvchi {user_id} kanal {channel_id} ga obuna emas")
                return False
        except Exception as e:
            logger.error(f"Obuna tekshirish xatosi {channel_id}: {e}")
            return False
    
    return True

# Start komandasi
@dp.message(Command(commands=["start"]))
async def start_command(message: Message):
    user_id = message.from_user.id
    record_log(user_id, "start_command")
    
    text = ("🎬 *Kino Botga Xush Kelibsiz!*\n\n"
           "Kino olish uchun quyidagi kanallarga obuna bo'ling va Instagram sahifamizga tashrif buyuring.\n"
           "So'ngra kino kodini yuboring.\n\n"
           "Kino kodini olish uchun admin bilan bog'laning.")
    
    channels = list_channels()
    instagram_link = get_config('instagram_link') or "https://instagram.com"
    
    keyboard_buttons = []
    
    # Har bir kanal uchun tugma
    for channel_id, channel_name in channels:
        try:
            chat = await bot.get_chat(channel_id)
            channel_title = channel_name or chat.title
            invite_link = await chat.export_invite_link() if chat.invite_link else f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📺 {channel_title}", 
                url=invite_link
            )])
        except Exception as e:
            logger.error(f"Kanal {channel_id} uchun link olish xatosi: {e}")
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📺 {channel_name or channel_id}", 
                url=f"https://t.me/{channel_id}" if str(channel_id).startswith('@') else f"https://t.me/c/{str(channel_id)[4:]}"
            )])
    
    # Instagram tugmasi
    keyboard_buttons.append([InlineKeyboardButton(
        text="📷 Instagram", 
        url=instagram_link
    )])
    
    # Obunani tekshirish tugmasi
    keyboard_buttons.append([InlineKeyboardButton(
        text="✅ Obunani Tekshirish", 
        callback_data="check_subs"
    )])
    
    # Admin panel tugmasi (faqat admin uchun)
    if str(user_id) == ADMIN_ID:
        keyboard_buttons.append([InlineKeyboardButton(
            text="⚙️ Admin Panel", 
            callback_data="admin_panel"
        )])
    
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# Admin panel komandasi
@dp.message(Command(commands=["admin"]))
async def admin_command(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ Sizga ruxsat yo'q!")
        return
    
    record_log(message.from_user.id, "admin_panel_accessed")
    
    text = ("⚙️ *Admin Panel*\n\n"
           "Quyidagi tugmalar orqali botni boshqaring:")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📺 Kanal Qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="🗑 Kanal O'chirish", callback_data="remove_channel")],
        [InlineKeyboardButton(text="📷 Instagram Link", callback_data="set_instagram")],
        [InlineKeyboardButton(text="🎬 Kinolar Ro'yxati", callback_data="movie_list")],
        [InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="main_menu")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# Callback query handlerlar
@dp.callback_query(lambda c: c.data == "check_subs")
async def cb_check_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    ok = await check_subscriptions(user_id)
    
    if ok:
        # Obuna bo'lgan kanallarni statistika ga yozish
        channels = list_channels()
        for channel_id, channel_name in channels:
            record_stat(channel_id, user_id, "subscribed")
        
        record_log(user_id, "subscription_checked_success")
        await callback.message.edit_text(
            "✅ *Obuna tasdiqlandi!*\n\nEndi kino kodini yuboring. Kod format: `K1234`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        record_log(user_id, "subscription_checked_failed")
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)

@dp.callback_query(lambda c: c.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    text = "⚙️ *Admin Panel*"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📺 Kanal Qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="🗑 Kanal O'chirish", callback_data="remove_channel")],
        [InlineKeyboardButton(text="📷 Instagram Link", callback_data="set_instagram")],
        [InlineKeyboardButton(text="🎬 Kinolar Ro'yxati", callback_data="movie_list")],
        [InlineKeyboardButton(text="🔙 Asosiy Menyu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "stats")
async def cb_stats(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    # Statistika ma'lumotlari
    channels = list_channels()
    movies = get_all_movies()
    channel_stats = get_channel_stats()
    
    text = "📊 *Bot Statistikalari*\n\n"
    
    # Kanallar statistikasi
    text += "📺 *Kanallar:*\n"
    stats_dict = {channel_id: count for channel_id, count in channel_stats}
    
    for channel_id, channel_name in channels:
        count = stats_dict.get(channel_id, 0)
        try:
            chat = await bot.get_chat(channel_id)
            channel_title = channel_name or chat.title
            text += f"• {channel_title}: {count} obunachi\n"
        except:
            text += f"• {channel_name or channel_id}: {count} obunachi\n"
    
    # Kinolar statistikasi
    text += f"\n🎬 *Kinolar:* {len(movies)} ta\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "movie_list")
async def cb_movie_list(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    movies = get_all_movies()
    
    if not movies:
        text = "🎬 *Hozircha hech qanday kino yo'q*"
    else:
        text = "🎬 *Kinolar Ro'yxati:*\n\n"
        for code, name in movies:
            text += f"• `{code}` - {name}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(lambda c: c.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await start_command(callback.message)

# Kanal qo'shish callback
@dp.callback_query(lambda c: c.data == "add_channel")
async def cb_add_channel(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    text = ("📺 *Kanal Qo'shish*\n\n"
           "Kanal qo'shish uchun quyidagi formatda yuboring:\n"
           "`/addchannel @kanal_username yoki -1001234567890 \"Kanal Nomi\"`\n\n"
           "Masalan:\n"
           "`/addchannel @my_channel \"Mening Kanallim\"`\n"
           "yoki\n"
           "`/addchannel -1001234567890 \"Maxfiy Kanal\"`")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# Kanal o'chirish callback
@dp.callback_query(lambda c: c.data == "remove_channel")
async def cb_remove_channel(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    channels = list_channels()
    
    if not channels:
        text = "📺 *Hozircha kanal yo'q*"
    else:
        text = "📺 *Mavjud Kanallar:*\n\n"
        for i, (channel_id, channel_name) in enumerate(channels, 1):
            text += f"{i}. `{channel_id}` - {channel_name}\n"
        
        text += "\nO'chirish uchun:\n`/removechannel @kanal_username yoki -1001234567890`"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# Instagram link sozlash callback
@dp.callback_query(lambda c: c.data == "set_instagram")
async def cb_set_instagram(callback: CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Sizga ruxsat yo'q!", show_alert=True)
        return
    
    text = ("📷 *Instagram Linkini Sozlash*\n\n"
           "Instagram linkini quyidagi formatda yuboring:\n"
           "`/setinstagram https://instagram.com/username`\n\n"
           "Masalan:\n"
           "`/setinstagram https://instagram.com/my_profile`")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# Admin tomonidan kino qo'shish
@dp.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    
    # Admin uchun kino qo'shish
    if str(user_id) == ADMIN_ID and (message.video or message.document):
        movie_name = message.caption or "Noma'lum kino"
        code = generate_code()
        
        # Maxfiy kanal ID sini olish
        movie_channel_id = get_config('movie_channel_id')
        if not movie_channel_id:
            await message.answer("❌ *Iltimos, avval maxfiy kanal ID sini sozlang:*\n`/setmoviechannel -1001234567890`", 
                               parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            # Kino maxfiy kanalga yuboriladi
            if message.video:
                sent_message = await bot.send_video(
                    chat_id=movie_channel_id, 
                    video=message.video.file_id, 
                    caption=f"🎬 {movie_name}\n\nKod: `{code}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                sent_message = await bot.send_document(
                    chat_id=movie_channel_id,
                    document=message.document.file_id,
                    caption=f"🎬 {movie_name}\n\nKod: `{code}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Kino bazaga saqlanadi
            if save_movie(code, movie_name, sent_message.message_id):
                await message.answer(
                    f"✅ *Kino saqlandi!*\n\nKod: `{code}`\nNomi: {movie_name}", 
                    parse_mode=ParseMode.MARKDOWN
                )
                record_log(user_id, f"movie_added_{code}")
            else:
                await message.answer("❌ *Kino saqlashda xato!*", parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Kino qo'shish xatosi: {e}")
            await message.answer(f"❌ *Xato:* {str(e)}", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Foydalanuvchi kino kodi yuborsa
    text = message.text or ""
    if re.match(r"^K\d+$", text.upper()):
        code = text.upper()
        movie_data = get_movie(code)
        
        if not movie_data:
            await message.answer("❌ *Bunday kod topilmadi!*", parse_mode=ParseMode.MARKDOWN)
            record_log(user_id, f"invalid_code_{code}")
            return
        
        # Obunani tekshirish
        if not await check_subscriptions(user_id):
            channels = list_channels()
            instagram_link = get_config('instagram_link') or "https://instagram.com"
            
            keyboard_buttons = []
            
            for channel_id, channel_name in channels:
                try:
                    chat = await bot.get_chat(channel_id)
                    channel_title = channel_name or chat.title
                    invite_link = await chat.export_invite_link() if chat.invite_link else f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"
                    keyboard_buttons.append([InlineKeyboardButton(
                        text=f"📺 {channel_title}", 
                        url=invite_link
                    )])
                except Exception as e:
                    logger.error(f"Kanal {channel_id} uchun link olish xatosi: {e}")
                    continue
            
            keyboard_buttons.append([InlineKeyboardButton(
                text="📷 Instagram", 
                url=instagram_link
            )])
            
            keyboard_buttons.append([InlineKeyboardButton(
                text="✅ Obunani Tekshirish", 
                callback_data="check_subs"
            )])
            
            kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.answer(
                "❌ *Iltimos, avval barcha kanallarga obuna bo'ling!*",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN
            )
            record_log(user_id, f"access_denied_{code}")
            return
        
        # Kino yuborish
        movie_name, message_id = movie_data
        movie_channel_id = get_config('movie_channel_id')
        
        if not movie_channel_id:
            await message.answer("❌ *Texnik xato! Admin bilan bog'laning.*", parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            # Kino forvard qilinadi
            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=movie_channel_id,
                message_id=message_id
            )
            
            record_log(user_id, f"movie_sent_{code}")
            record_stat("movie_delivery", user_id, "sent")
            
        except Exception as e:
            logger.error(f"Kino yuborish xatosi: {e}")
            await message.answer(f"❌ *Kino yuborishda xato: {str(e)}*", parse_mode=ParseMode.MARKDOWN)
        
        return
    
    # Boshqa xabarlar
    if str(user_id) != ADMIN_ID:
        await message.answer(
            "🎬 *Kino Bot*\n\nKino olish uchun kod yuboring yoki /start buyrug'ini bering.",
            parse_mode=ParseMode.MARKDOWN
        )

# Admin kanal qo'shish
@dp.message(Command(commands=["addchannel"]))
async def add_channel_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("❌ *Iltimos kanal ID sini kiriting:*\n`/addchannel @channel_id yoki -1001234567890 \"Kanal Nomi\"`", 
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    channel_id = parts[1].strip()
    channel_name = parts[2].strip('"') if len(parts) > 2 else ""
    
    try:
        # Kanal mavjudligini tekshirish
        chat = await bot.get_chat(channel_id)
        if not channel_name:
            channel_name = chat.title
        
        if add_channel(channel_id, channel_name):
            await message.answer(f"✅ *Kanal qo'shildi!*\nID: `{channel_id}`\nNomi: {channel_name}", 
                               parse_mode=ParseMode.MARKDOWN)
            record_log(message.from_user.id, f"channel_added_{channel_id}")
        else:
            await message.answer("❌ *Kanal qo'shishda xato!*", parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Kanal qo'shish xatosi: {e}")
        await message.answer(f"❌ *Kanal topilmadi yoki bot kanalga kirish huquqiga ega emas!*\nXato: {str(e)}", 
                           parse_mode=ParseMode.MARKDOWN)

# Admin kanal o'chirish
@dp.message(Command(commands=["removechannel"]))
async def remove_channel_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ *Iltimos kanal ID sini kiriting:*\n`/removechannel @channel_id yoki -1001234567890`", 
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    channel_id = parts[1].strip()
    
    try:
        if remove_channel(channel_id):
            await message.answer(f"✅ *Kanal o'chirildi!*\nID: `{channel_id}`", parse_mode=ParseMode.MARKDOWN)
            record_log(message.from_user.id, f"channel_removed_{channel_id}")
        else:
            await message.answer("❌ *Kanal o'chirishda xato!*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Kanal o'chirish xatosi: {e}")
        await message.answer(f"❌ *Xato:* {str(e)}", parse_mode=ParseMode.MARKDOWN)

# Instagram linkini sozlash
@dp.message(Command(commands=["setinstagram"]))
async def set_instagram_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ *Iltimos Instagram linkini kiriting:*\n`/setinstagram https://instagram.com/username`", 
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    instagram_link = parts[1].strip()
    if set_config('instagram_link', instagram_link):
        await message.answer(f"✅ *Instagram linki o'rnatildi!*\n{instagram_link}", parse_mode=ParseMode.MARKDOWN)
        record_log(message.from_user.id, "instagram_updated")
    else:
        await message.answer("❌ *Instagram linkini o'rnatishda xato!*", parse_mode=ParseMode.MARKDOWN)

# Maxfiy kino kanalini sozlash
@dp.message(Command(commands=["setmoviechannel"]))
async def set_movie_channel_cmd(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ *Iltimos maxfiy kanal ID sini kiriting:*\n`/setmoviechannel -1001234567890`", 
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    movie_channel_id = parts[1].strip()
    
    try:
        # Kanal mavjudligini tekshirish
        chat = await bot.get_chat(movie_channel_id)
        
        if set_config('movie_channel_id', movie_channel_id):
            await message.answer(
                f"✅ *Maxfiy kino kanali o'rnatildi!*\nID: `{movie_channel_id}`\nNomi: {chat.title}", 
                parse_mode=ParseMode.MARKDOWN
            )
            record_log(message.from_user.id, "movie_channel_updated")
        else:
            await message.answer("❌ *Maxfiy kanal o'rnatishda xato!*", parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Maxfiy kanal sozlash xatosi: {e}")
        await message.answer(f"❌ *Kanal topilmadi yoki bot kanalga kirish huquqiga ega emas!*\nXato: {str(e)}", 
                           parse_mode=ParseMode.MARKDOWN)

# Health check uchun web server
async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Health check server started on port {port}")

async def main():
    # Web server va botni birga ishga tushirish
    await start_web_server()
    
    try:
        logger.info("🤖 Bot ishga tushdi...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Xato: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
