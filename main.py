import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot import types

# ──────────────────────────────────────────────
# 1. KEEP-ALIVE SERVER (Render 24/7 ishlashi uchun)
# ──────────────────────────────────────────────

KEEP_ALIVE_PORT = 5000

class _PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Yigitlar Boti Is Running Successfully!")

    def log_message(self, format, *args):
        return

def _start_keep_alive():
    server = HTTPServer(("0.0.0.0", KEEP_ALIVE_PORT), _PingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

_start_keep_alive()

# ──────────────────────────────────────────────
# 2. BAZA SOZLAMALARI (SQLite)
# ──────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect("male_bot.db", check_same_thread=False)
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
    conn = sqlite3.connect("male_bot.db", check_same_thread=False)
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

# Telegram Bot Token va Admin Guruhi ID-si
MALE_BOT_TOKEN = 8870393893:AAG7VI8-b1YIzSyE1KaxY17uuF1EAt4mw6I
GROUP_ID = -1003828834561

# Olingan FILE_ID'lar joylandi:
VOICE_1_FILE_ID = "AwACAgIAAxkBAAEsqSBqYB9kbzZv0yg2IjrlPcRSj5cZCgACB6YAAm4aoUpuaZH9rR8grj0E"  # 00:57 ovoz
VOICE_2_FILE_ID = "AwACAgIAAxkBAAEsqSFqYB9kwrYRpDNQOvVycYSa31-kWQACCqYAAm4aoUqto1E_nxiBdz0E"  # 00:17 ovoz
VOICE_3_FILE_ID = "AwACAgIAAxkBAAEsqSJqYB9kphwuXXjxyL3fAAHQbme0QBAAAhOmAAJuGqFKtbCsh59O-3Y9BA"  # 00:51 ovoz
EXAMPLE_PHOTO_ID = "AgACAgIAAxkBAAEsqTBqYCBzn-yk87bvwlBrhUsCdoZ9AANBG2sbDIsBS16fA4RwVXg0AQADAgADdwADPQQ" # Model rasm

bot = telebot.TeleBot(MALE_BOT_TOKEN)

# ──────────────────────────────────────────────
# 4. YIGITLAR BOTI LOGIKASI
# ──────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def male_start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("📝 Anketa to'ldirish"))

    # 1. Avtosms matni
    text = (
        "💋 <b>AVTOSMS</b>\n\n"
        "Murojat uchun rahmat tezda aloqaga chiqib javob beraman❤️\n\n"
        "Qaysi anketa bo'yicha yozuvdingiz? Ismini aytsangiz yoki rasmi tashlasangiz, "
        "hozir band yoki bo'shligini tekshirib beraman."
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=keyboard)

    # 2. Ketma-ket boradigan ovozli xabarlar (00:57 va 00:17)
    try:
        bot.send_voice(message.chat.id, VOICE_1_FILE_ID)
        bot.send_voice(message.chat.id, VOICE_2_FILE_ID)
    except Exception as e:
        print(f"Start ovozli xabarlarda xato: {e}")

@bot.message_handler(
    func=lambda m: m.chat.type == "private",
    content_types=['text', 'photo', 'video', 'voice', 'audio', 'document', 'sticker', 'video_note']
)
def handle_male_private(message):
    user_id = message.from_user.id

    # Anketa to'ldirish tugmasi bosilganda
    if message.text == "📝 Anketa to'ldirish":
        # 1. 3-ovozli xabar (00:51) boradi
        try:
            bot.send_voice(user_id, VOICE_3_FILE_ID)
        except Exception as e:
            print(f"Anketa ovozli xabarida xato: {e}")

        # 2. Namuna Rasm va tagidagi matn boradi
        caption_text = (
            "Mana misol!\n"
            "shudo akkuratni rasm va 2-3 ogiz qiziqishiz va razmer haqida yozsangiz.\n"
            "Kliyentkalar shuncha tez sizni tanlaydi!"
        )
        try:
            bot.send_photo(user_id, EXAMPLE_PHOTO_ID, caption=caption_text)
        except Exception as e:
            print(f"Rasm yuborishda xato: {e}")
            bot.send_message(user_id, caption_text)
        return

    # User bazada bor-yo'qligini tekshirish (#S1, #S2 kodi bilan)
    user_data = db_query("SELECT code, topic_id FROM male_users WHERE user_id = ?", (user_id,), fetchone=True)

    if not user_data:
        # Yangi unikal kod berish (#S1, #S2...)
        last_user = db_query("SELECT MAX(id) FROM male_users", fetchone=True)
        next_id = (last_user[0] or 0) + 1
        code = f"S{next_id}"

        first_name = message.from_user.first_name or "Yigit"
        topic = bot.create_forum_topic(chat_id=GROUP_ID, name=f"👨 #{code} - {first_name}")
        topic_id = topic.message_thread_id

        db_query("INSERT INTO male_users (user_id, code, topic_id) VALUES (?, ?, ?)", 
                 (user_id, code, topic_id), commit=True)

        info = (
            f"<b>Yangi Yigit Anketasi!</b>\n"
            f"<b>KOD:</b> <code>#{code}</code>\n"
            f"<b>Ism:</b> {first_name}\n"
            f"<b>ID:</b> <code>{user_id}</code>"
        )
        bot.send_message(GROUP_ID, info, message_thread_id=topic_id, parse_mode="HTML")
    else:
        code, topic_id = user_data

    # Xabarni guruhdagi topikga nusxalash
    bot.copy_message(GROUP_ID, message.chat.id, message.message_id, message_thread_id=topic_id)


# ──────────────────────────────────────────────
# 5. GURUHDAN JAVOB BERISH VA BUYRUQLAR (Admin)
# ──────────────────────────────────────────────

@bot.message_handler(
    func=lambda m: m.chat.id == GROUP_ID and m.message_thread_id is not None and not m.from_user.is_bot,
    content_types=['text', 'photo', 'video', 'voice', 'audio', 'document', 'sticker', 'video_note']
)
def handle_group_reply(message):
    topic_id = message.message_thread_id
    text = message.text or ""

    # BUYRUQ: Rad etish xabarini ommaviy yuborish
    # Ishlatish usuli: /reject_all S1, S3, S5
    if text.startswith("/reject_all"):
        codes_str = text.replace("/reject_all", "").strip()
        codes = [c.strip().replace("#", "").upper() for c in codes_str.split(",") if c.strip()]

        reject_msg = (
            "Afsuski, ushbu e'lon bo'yicha nomzod tanlab bo'lindi. "
            "Keyingi e'lonlarni kuzatib boring va tezroq aloqaga chiqing!"
        )

        success_codes = []
        for code in codes:
            male_data = db_query("SELECT user_id FROM male_users WHERE code = ?", (code,), fetchone=True)
            if male_data:
                try:
                    bot.send_message(male_data[0], reject_msg)
                    success_codes.append(f"#{code}")
                except Exception as e:
                    print(f"Xato {code}: {e}")

        if success_codes:
            bot.send_message(
                GROUP_ID, 
                f"🚫 Rad etish xabari quyidagi kod egalariga yuborildi:\n{', '.join(success_codes)}", 
                message_thread_id=topic_id
            )
        else:
            bot.send_message(GROUP_ID, "❌ Hech qanday to'g'ri KOD topilmadi!", message_thread_id=topic_id)
        return

    # Guruhda oddiy javob yozsak, o'sha topik egasi bo'lgan yigitga boradi
    male_data = db_query("SELECT user_id FROM male_users WHERE topic_id = ?", (topic_id,), fetchone=True)
    if male_data:
        try:
            bot.copy_message(chat_id=male_data[0], from_chat_id=GROUP_ID, message_id=message.message_id)
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    bot.infinity_polling()
  
