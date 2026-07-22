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
MALE_BOT_TOKEN = "8870393893:AAFne4hdyQGMdC24-kSOSB8g-sLd8fKog9A"
GROUP_ID = -1003828834561

# Yangi fayl ID'lari
VOICE_1_FILE_ID = "AwACAgIAAxkBAAEsq2ZqYG-chrPWGJowI_DKQcO8xaSQ7AAC7JoAAvImAAFLMqSHENaLUk49BA"
VOICE_2_FILE_ID = "AwACAgIAAxkBAAEsq2dqYG-cRxDLZD5--xRITgRDdJ9kHgAC7ZoAAvImAAFLoETTWwOrdDs9BA"
VOICE_3_FILE_ID = "AwACAgIAAxkBAAEsq2hqYG-c1GOc0-f-M7C45PV_EDAkPQAC7poAAvImAAFLvsxER2bDyCg9BA"

# O'rta o'lchamdagi namuna rasm
EXAMPLE_PHOTO_ID = "AgACAgIAAxkBAAEsqTBqYCBzn-yk87bvwlBrhUsCdoZ9AANBG2sbDIsBS16fA4RwVXg0AQADAgADeAADPQQ"

bot = telebot.TeleBot(MALE_BOT_TOKEN)

# ──────────────────────────────────────────────
# 4. YIGITLAR BOTI LOGIKASI
# ──────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def erkak_boshlash(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("📝 Anketa to'ldirish"))
    
    text = (
        "💋 AVTOSMS\n\n"
        "Murojat uchun rahmat tezda aloqaga chiqib javob beraman❤️\n\n"
        "Qaysi anketa bo'yicha yozuvdingiz?\n"
        "Ismini aytsangiz yoki rasmi tashlasangiz, hozir band yoki bo'shligini tekshirib beraman."
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)
    
    try:
        bot.send_voice(message.chat.id, VOICE_1_FILE_ID)
        bot.send_voice(message.chat.id, VOICE_2_FILE_ID)
    except Exception as e:
        print(f"Start ovozli xabarlarda xato: {e}")

@bot.message_handler(func=lambda m: m.chat.type == "private", content_types=['text', 'photo', 'voice', 'document'])
def handle_male_private(message):
    user_id = message.from_user.id
    
    if message.text == "📝 Anketa to'ldirish":
        try:
            bot.send_voice(user_id, VOICE_3_FILE_ID)
        except Exception as e:
            print(f"Anketa ovozli xabarida xato: {e}")
            
        header_text = (
            "Mana misol!\n"
            "shudo akkuratni rasm va 2-3 ogiz qiziqishiz va razmer haqida yozsangiz.\n"
            "Kliyentkalar shuncha tez sizni tanlaydi!"
        )
        try:
            bot.send_photo(user_id, EXAMPLE_PHOTO_ID, caption=header_text)
        except Exception as e:
            print(f"Rasm yuborishda xato: {e}")
            bot.send_message(user_id, header_text)
        return

    user_info = db_query("SELECT topic_id, code FROM male_users WHERE user_id = ?", (user_id,), fetchone=True)
    
    if not user_info:
        last_user = db_query("SELECT MAX(id) FROM male_users", fetchone=True)
        next_id = (last_user[0] or 0) + 1
        code = f"S{next_id}"
        
        name = message.from_user.first_name or "Yigit"
        topic = bot.create_forum_topic(GROUP_ID, name=f"{code} - {name}")
        topic_id = topic.message_thread_id
        
        db_query("INSERT INTO male_users (user_id, code, topic_id) VALUES (?, ?, ?)", 
                 (user_id, code, topic_id), commit=True)
        
        info_msg = (
            f"<b>Yangi Yigit Anketasi!</b>\n"
            f"<b>KOD:</b> <code>#{code}</code>\n"
            f"<b>Ism:</b> {name}\n"
            f"<b>ID:</b> <code>{user_id}</code>"
        )
        bot.send_message(GROUP_ID, info_msg, parse_mode="HTML", message_thread_id=topic_id)
    else:
        topic_id, code = user_info

    # Xabarni guruhga nusxalash
    bot.copy_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=topic_id)
    
    # Anketa yuborilgach foydalanuvchiga tasdiq xabari
    bot.send_message(message.chat.id, "Rahmat, anketangiz qabul qilindi!")

# ──────────────────────────────────────────────
# 5. GURUHDAN JAVOB BERISH VA BUYRUQLAR
# ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID, content_types=['text', 'photo', 'voice', 'document'])
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
    
