import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot import types

# ──────────────────────────────────────────────
# 1. KEEP ALIVE SERVER (RENDER UCHUN)
# ──────────────────────────────────────────────
KEEP_ALIVE_PORT = 5000

class _PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Yigitlar Boti Is Alive")

    def log_message(self, format, *args):
        return

def _start_keep_alive():
    server = HTTPServer(("0.0.0.0", KEEP_ALIVE_PORT), _PingHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

_start_keep_alive()

# ──────────────────────────────────────────────
# 2. BAZA SOZLAMALARI (SQLite)
# ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("erkak_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS male_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            code TEXT UNIQUE,
            topic_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect("erkak_bot.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = None
    if fetchone:
        data = cursor.fetchone()
    elif fetchall:
        data = cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return data

# ──────────────────────────────────────────────
# 3. BOT SOZLAMALARI VA FAYL ID'LARI
# ──────────────────────────────────────────────
MALE_BOT_TOKEN = "8870393893:AAFne4hdyQGMdC24-kSOSB8HKdQKD8aqCvA"
GROUP_ID = -1003828834561

EXAMPLE_PHOTO_URL = "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=1000&auto=format&fit=crop"

bot = telebot.TeleBot(MALE_BOT_TOKEN)

user_steps = {}
user_data = {}

def get_or_create_user(user):
    user_id = user.id
    user_info = db_query("SELECT topic_id, code FROM male_users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not user_info:
        last_user = db_query("SELECT MAX(id) FROM male_users", fetchone=True)
        next_id = (last_user[0] or 0) + 1
        code = f"S{next_id}"
        
        user_name = user.first_name or "Yigit"
        
        # Guruhda Yangi Topic ochish
        topic = bot.create_forum_topic(GROUP_ID, name=f"{code} - {user_name}")
        topic_id = topic.message_thread_id
        
        db_query("INSERT INTO male_users (user_id, code, topic_id) VALUES (?, ?, ?)", 
                 (user_id, code, topic_id), commit=True)
        
        # PROFILGA O'TISH UCHUN TO'G'RIDAN-TO'G'RI HAVOLA (tg://user?id=...)
        profile_link = f"tg://user?id={user_id}"
        
        profile_msg = (
            f"👤 <b>YANGI FOYDALANUVCHI PROFILI</b>\n\n"
            f"<b>KOD:</b> <code>#{code}</code>\n"
            f"<b>Ism va Profil:</b> <a href='{profile_link}'>{user_name}</a>\n"
            f"<b>Telegram ID:</b> <code>{user_id}</code>"
        )
        bot.send_message(GROUP_ID, profile_msg, parse_mode="HTML", message_thread_id=topic_id)
        return topic_id, code
    
    return user_info[0], user_info[1]

# ──────────────────────────────────────────────
# 4. YIGITLAR BOTI LOGIKASI
# ──────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def erkak_boshlash(message):
    user_id = message.from_user.id
    user_steps.pop(user_id, None)
    user_data.pop(user_id, None)
    
    get_or_create_user(message.from_user)
    
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("📝 Anketa to'ldirish"))
    
    text = (
        "💋 AVTOSMS\n\n"
        "Murojat uchun rahmat tezda aloqaga chiqib javob beraman❤️\n\n"
        "Qaysi anketa bo'yicha yozuvdingiz?\n"
        "Ismini aytsangiz yoki rasmi tashlasangiz, hozir band yoki bo'shligini tekshirib beraman."
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.type == "private", content_types=['text', 'photo', 'voice', 'document', 'audio', 'video'])
def handle_male_private(message):
    user_id = message.from_user.id
    text = message.text or ""
    
    topic_id, code = get_or_create_user(message.from_user)

    # 1. ANKETA TO'LDIRISH TUGMASI BOSILGANDA
    if text == "📝 Anketa to'ldirish":
        user_steps[user_id] = "WAIT_NAME"
        user_data[user_id] = {}
        
        header_text = (
            "Mana misol!\n"
            "shudo akkuratni rasm va 2-3 ogiz qiziqishiz va razmer haqida yozsangiz.\n"
            "Kliyentkalar shuncha tez sizni tanlaydi!"
        )
        try:
            bot.send_photo(user_id, EXAMPLE_PHOTO_URL, caption=header_text)
        except Exception as e:
            bot.send_message(user_id, header_text)
            
        bot.send_message(user_id, "Ismingizni yozing:")
        return

    # 2. ANKETA BOSQICHLARI (FSM)
    step = user_steps.get(user_id)

    if step == "WAIT_NAME":
        if not message.text:
            bot.send_message(user_id, "Iltimos, ismingizni matn ko'rinishida yozing:")
            return
        user_data[user_id]['name'] = message.text
        user_steps[user_id] = "WAIT_BODY"
        bot.send_message(user_id, "Bo'yingiz va vazningizni kiriting:")
        return

    elif step == "WAIT_BODY":
        if not message.text:
            bot.send_message(user_id, "Iltimos, bo'yingiz va vazningizni matn ko'rinishida yozing:")
            return
        user_data[user_id]['body'] = message.text
        user_steps[user_id] = "WAIT_BIO"
        bot.send_message(user_id, "O'zingiz haqingizda qisqacha ma'lumot:")
        return

    elif step == "WAIT_BIO":
        if not message.text:
            bot.send_message(user_id, "Iltimos, ma'lumotni matn ko'rinishida yozing:")
            return
        user_data[user_id]['bio'] = message.text
        user_steps[user_id] = "WAIT_PHOTO"
        bot.send_message(user_id, "Rasmingizni kiriting:")
        return

    elif step == "WAIT_PHOTO":
        if message.content_type != 'photo':
            bot.send_message(user_id, "⚠️ Iltimos, faqat rasm yuboring!")
            return
            
        photo_id = message.photo[-1].file_id
        data = user_data.get(user_id, {})

        caption = (
            f"📋 <b>TO'LDIRILGAN ANKETA</b>\n\n"
            f"<b>KOD:</b> <code>#{code}</code>\n"
            f"<b>Ism:</b> {data.get('name', 'Ko-rsatilmadi')}\n"
            f"<b>Bo'y/Vazn:</b> {data.get('body', 'Ko-rsatilmadi')}\n"
            f"<b>Ma'lumot:</b> {data.get('bio', 'Ko-rsatilmadi')}"
        )
        bot.send_photo(GROUP_ID, photo_id, caption=caption, parse_mode="HTML", message_thread_id=topic_id)

        bot.send_message(
            user_id, 
            f"Rahmat, anketangiz qabul qilindi.\n"
            f"Sizning anketa raqamingiz {code}.\n"
            f"Raqamingizni eslab qoling, sizga qiziqish bo'lsa xabar yuboriladi."
        )

        user_steps.pop(user_id, None)
        user_data.pop(user_id, None)
        return

    # 3. ODDIY MULOQOT VA MA'LUMOT MATNI
    if user_steps.get(user_id) is None:
        intro_text = (
            "Salom DJentelmenlar agentligi xush kelibsiz bizni agetligimiz ayollarga xizmat ko'rsatish bilan shug'ullanadi "
            "bizga ayollar o'zi bog'ilishadi o'zlarigi vaqtinchalik yigit qidirib biz anketasi bor yigitlarni ularga tavsiya beramiz.\n\n"
            "Uchrashuvga chiqqan har bir yigitga ayol tomonidan haq to'lanadi rozi bo'lsangiz anketa to'ldirish tugmasini bosing."
        )
        bot.send_message(user_id, intro_text)
        bot.copy_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=topic_id)

# ──────────────────────────────────────────────
# 5. GURUHDAN JAVOB BERISH (ADMIN -> YIGIT)
# ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID, content_types=['text', 'photo', 'voice', 'document', 'audio', 'video'])
def javob_berish_guruhi(message):
    topic_id = message.message_thread_id
    text = message.text or ""
    
    if text.startswith("/barchasini_rad_etish"):
        codes_str = text.replace("/barchasini_rad_etish", "").strip()
        codes = [c.strip() for c in codes_str.split(",") if c.strip()]
        
        reject_msg = (
            "Afsuski, bu e'lon bo'yicha taklifingiz rad etildi.\n"
            "Keyingi e'lonlarni kuzatib boring!"
        )
        
        success_codes = []
        for code in codes:
            male = db_query("SELECT user_id FROM male_users WHERE code = ?", (code,), fetchone=True)
            if male:
                try:
                    bot.send_message(male[0], reject_msg)
                    success_codes.append(code)
                except Exception as e:
                    print(f"Xato {code}: {e}")
                    
        if success_codes:
            bot.send_message(GROUP_ID, f"🚫 Rad etish xabari yuborildi: {', '.join(success_codes)}", message_thread_id=topic_id)
        else:
            bot.send_message(GROUP_ID, "❌ Hech qaysi kod bo'yicha foydalanuvchi topilmadi.", message_thread_id=topic_id)
        return

    male = db_query("SELECT user_id FROM male_users WHERE topic_id = ?", (topic_id,), fetchone=True)
    if male:
        try:
            bot.copy_message(male[0], message.chat.id, message.message_id)
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
    
