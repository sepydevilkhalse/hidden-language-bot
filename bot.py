import telebot
import re
import sqlite3
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8943897493:AAEBKncLQgRKNZ0Gidw2WDtwYmQO_2_8GL4"
bot = telebot.TeleBot(TOKEN)

# ================ دیکشنری‌ها ================
letters = {
    'ا': '1', 'آ': '1', 'ب': '2', 'پ': '3', 'ت': '4', 'ث': '5',
    'ج': '6', 'چ': '7', 'ح': '8', 'خ': '9', 'د': '10', 'ذ': '11',
    'ر': '12', 'ز': '13', 'ژ': '14', 'س': '15', 'ش': '16', 'ص': '17',
    'ض': '18', 'ط': '19', 'ظ': '20', 'ع': '21', 'غ': '22', 'ف': '23',
    'ق': '24', 'ک': '25', 'گ': '26', 'ل': '27', 'م': '28', 'ن': '29',
    'و': '30', 'ه': '31', 'ی': '32'
}

number_to_d = {
    '0': 'd0', '1': 'd1', '2': 'd2', '3': 'd3', '4': 'd4',
    '5': 'd5', '6': 'd6', '7': 'd7', '8': 'd8', '9': 'd9'
}

numbers = {
    '1': 'ا', '2': 'ب', '3': 'پ', '4': 'ت', '5': 'ث',
    '6': 'ج', '7': 'چ', '8': 'ح', '9': 'خ', '10': 'د',
    '11': 'ذ', '12': 'ر', '13': 'ز', '14': 'ژ', '15': 'س',
    '16': 'ش', '17': 'ص', '18': 'ض', '19': 'ط', '20': 'ظ',
    '21': 'ع', '22': 'غ', '23': 'ف', '24': 'ق', '25': 'ک',
    '26': 'گ', '27': 'ل', '28': 'م', '29': 'ن', '30': 'و',
    '31': 'ه', '32': 'ی'
}

persian_to_english = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
english_to_persian = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
SPECIAL_PATTERN = re.compile(r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\u2600-\u27BF]|[!؟.،,;:؟؟٬٪×÷+-=@#$%^&*(){}<>~`\'"/|]')

# ================ دیتابیس ================
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, username TEXT, first_join TEXT, last_active TEXT, total_conversions INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS conversions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, input_text TEXT, output_text TEXT, conversion_type TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()
init_db()

def add_user(user_id, first_name, last_name, username):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if c.fetchone():
            c.execute('UPDATE users SET last_active = ?, first_name = ?, last_name = ?, username = ? WHERE user_id = ?', (now, first_name, last_name, username, user_id))
        else:
            c.execute('INSERT INTO users (user_id, first_name, last_name, username, first_join, last_active) VALUES (?, ?, ?, ?, ?, ?)', (user_id, first_name, last_name, username, now, now))
        conn.commit()
        conn.close()
    except:
        pass

def update_conversion(user_id, input_text, output_text, conv_type):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('INSERT INTO conversions (user_id, input_text, output_text, conversion_type, timestamp) VALUES (?, ?, ?, ?, ?)', (user_id, input_text[:200], output_text[:200], conv_type, now))
        c.execute('UPDATE users SET total_conversions = total_conversions + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_stats(user_id):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('SELECT total_conversions, first_join FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result
    except:
        return None

def get_history(user_id, limit=5):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute('SELECT input_text, output_text, timestamp FROM conversions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
        results = c.fetchall()
        conn.close()
        return results
    except:
        return []

def validate(text):
    text = text.translate(persian_to_english)
    nums = re.findall(r'\d+', text)
    for n in nums:
        if int(n) > 32:
            return False
    return True

def split_by_space_and_special(text):
    parts = []
    i = 0
    current_word = ""
    while i < len(text):
        if text[i].isspace():
            if current_word:
                parts.append(("word", current_word))
                current_word = ""
            space = ""
            while i < len(text) and text[i].isspace():
                space += text[i]
                i += 1
            parts.append(("space", space))
            continue
        special_match = SPECIAL_PATTERN.match(text[i:])
        if special_match:
            if current_word:
                parts.append(("word", current_word))
                current_word = ""
            parts.append(("special", special_match.group()))
            i += len(special_match.group())
            continue
        current_word += text[i]
        i += 1
    if current_word:
        parts.append(("word", current_word))
    return parts

def encode(text):
    text = text.translate(persian_to_english)
    lines = text.split("\n")
    final_lines = []
    for line in lines:
        if not line.strip():
            final_lines.append("")
            continue
        parts = split_by_space_and_special(line)
        result_parts = []
        for part_type, part_text in parts:
            if part_type == "space":
                result_parts.append("•")
            elif part_type == "special":
                result_parts.append(part_text)
            else:
                nums = []
                for ch in part_text:
                    if ch in letters:
                        nums.append(letters[ch])
                    elif ch.isdigit():
                        nums.append(number_to_d.get(ch, ch))
                    else:
                        nums.append(ch)
                if nums:
                    result_parts.append("_".join(nums))
        final_lines.append("".join(result_parts))
    return "\n".join(final_lines)

def decode(text):
    text = text.translate(persian_to_english)
    lines = text.split("\n")
    final_lines = []
    for line in lines:
        if not line.strip():
            final_lines.append("")
            continue
        parts = line.split("•")
        result_words = []
        for part in parts:
            if not part:
                continue
            if 'd' in part:
                codes = part.split('_')
                word = ''
                for c in codes:
                    if c.startswith('d') and c[1:].isdigit():
                        num = c[1:]
                        word += num.translate(english_to_persian)
                    elif c in numbers:
                        word += numbers[c]
                    else:
                        word += c
                result_words.append(word)
            else:
                match = re.match(r'^([\d_]+)(.*)$', part)
                if match:
                    code = match.group(1)
                    special = match.group(2)
                    result = ""
                    for c in code.split("_"):
                        if c in numbers:
                            result += numbers[c]
                        else:
                            result += c
                    result += special
                    result_words.append(result)
                else:
                    result_words.append(part)
        final_lines.append(" ".join(result_words))
    return "\n".join(final_lines)

# ================ منوی پایین صفحه (فقط یک بار) ================
def reply_menu():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("ℹ️ درباره"),
        KeyboardButton("📊 آمار من")
    )
    keyboard.add(
        KeyboardButton("📜 تاریخچه"),
        KeyboardButton("📱 برنامه")
    )
    return keyboard

# ================ منوی شیشه‌ای (برای برنامه) ================
def inline_app_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "🌐 باز کردن برنامه",
            web_app=WebAppInfo(url="https://hiddenlanguage.netlify.app")
        )
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    add_user(user.id, user.first_name, user.last_name, user.username)
    text = """✨🔐 **Hidden Language** 🔐✨

👋 به ربات زبان مخفی خوش آمدید!

💠 **چطوری کار می‌کنه؟**
فقط پیام خودتو بفرست، من خودم تشخیص می‌دم که متن فارسیه یا کد مخفی!

**مثال:**
`سلام ۵` ➜ `15_27_1_28•d5`
`15_27_1_28•d5` ➜ `سلام ۵`

⚡ **ویژگی‌ها:**
🔹 تبدیل سریع و هوشمند
🧠 تشخیص خودکار متن و کد
😎 پشتیبانی از اعداد (d1, d2, ...)
😈 حفظ کامل ایموجی‌ها
📜 ذخیره تاریخچه تبدیل‌ها
📊 آمار شخصی

📩 فقط پیام خودتو بفرست..."""
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=reply_menu())

# ================ هندلر دکمه‌های پایین ================
@bot.message_handler(func=lambda m: m.text == "ℹ️ درباره")
def about_button(message):
    about_text = """ℹ️ **درباره ربات**

🤖 نسخه: 2.1
📅 2025

✅ تبدیل فارسی ↔ کد مخفی
✅ تشخیص خودکار
✅ پشتیبانی از اعداد (d1, d2, ...)
✅ تاریخچه و آمار"""
    bot.reply_to(message, about_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def stats_button(message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    if stats:
        total, first = stats
        stats_text = f"📊 **آمار شما**\n\n📝 تعداد تبدیل‌ها: {total}\n📆 عضویت: {first[:10]}"
    else:
        stats_text = "📊 هنوز تبدیلی انجام ندادید!"
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📜 تاریخچه")
def history_button(message):
    user_id = message.from_user.id
    history = get_history(user_id, 5)
    if history:
        history_text = "📜 **۵ تبدیل اخیر:**\n\n"
        for i, (inp, out, ts) in enumerate(history, 1):
            history_text += f"{i}. `{inp[:30]}` ➜ `{out[:30]}`\n"
            history_text += f"   📅 {ts[:16]}\n\n"
    else:
        history_text = "📜 هنوز تبدیلی انجام ندادید!"
    bot.reply_to(message, history_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📱 برنامه")
def app_button(message):
    bot.reply_to(message, "📱 برای باز کردن برنامه کلیک کن:", reply_markup=inline_app_menu())

# ================ هندلر اصلی ================
@bot.message_handler(func=lambda m: True)
def handler(message):
    user = message.from_user
    add_user(user.id, user.first_name, user.last_name, user.username)
    text = message.text or ""
    if not text or text.startswith("/"):
        return
    if text in ["ℹ️ درباره", "📊 آمار من", "📜 تاریخچه", "📱 برنامه"]:
        return
    if message.chat.type in ["group", "supergroup"]:
        username = bot.get_me().username
        mention = f"@{username}"
        if mention not in text:
            return
        text = text.replace(mention, "").strip()
        if not text:
            return
    if re.search(r'[A-Za-z]', text):
        bot.reply_to(message, "❌ فقط متن فارسی وارد کنید.")
        return
    if not validate(text):
        bot.reply_to(message, "❌ عدد وارد شده در زبان نمی‌باشد.")
        return
    has_persian = bool(re.search(r'[ا-ی]', text))
    if has_persian:
        result = encode(text)
        conv_type = "encode"
    else:
        result = decode(text)
        conv_type = "decode"
    update_conversion(user.id, text, result, conv_type)
    bot.reply_to(message, f"<code>{result}</code>", parse_mode="HTML")

print("🤖 ربات روشن شد...")
bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
