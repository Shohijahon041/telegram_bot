# Telegram Kino Bot

Bu bot orqali maxfiy kanalga yuklangan kinolar kodi bilan yuboriladi, va foydalanuvchilar faqat obuna bo‘lganidan keyin kodi orqali film olishi mumkin.

## Asosiy funksiyalar:
- Kino kodi avtomatik generatsiya qilinadi  
- “/admin” orqali kanal qo‘shish, Instagram linki o‘rnatish  
- Obuna tekshirish: Telegram kanallarga obuna bo‘lganini tekshiradi  
- Xotirali SQLite ma’lumotlar bazasi bilan ishlaydi  

## O‘rnatish:
1. Python 3.10+ ni o‘rnating  
2. `pip install -r requirements.txt`  
3. `python bot.py` ishlating  

## Railway-ga deploy:
- GitHub repo yaratib, ushbu fayllarni yuklang  
- Railway da yangi loyiha oching → GitHub dan deploy qiling  
- Rail­way da Env Variables (TOKEN, ADMIN_ID, MOVIE_CHANNEL_ID) ni sozlang  
- Deploy qiling, va bot ishlaydi
