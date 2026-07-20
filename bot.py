import telebot
import re
import sqlite3
from datetime import datetime

from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand
)

TOKEN = "8943897493:AAEBKncLQgRKNZ0Gidw2WDtwYmQO_2_8GL4"
bot = telebot.TeleBot(TOKEN)

# ==============================================
# دیکشنری اصلی
# ==============================================
letters = {
    'ا': '1', 'آ': '1', 'ب': '2', 'پ': '3', 'ت': '4', 'ث': '5',
    'ج': '6', 'چ': '7', 'ح': '8', 'خ': '9', 'د': '10', 'ذ': '11',
    'ر': '12', 'ز': '13', 'ژ': '14', 'س': '15', 'ش': '16', 'ص': '17',
    'ض': '18', 'ط': '19', 'ظ': '20', 'ع': '21', 'غ': '22', 'ف': '23',
    'ق': '24', 'ک': '25', 'گ': '26', 'ل': '27', 'م': '28', 'ن': '29',
    'و': '30', 'ه': '31', 'ی': '32'
}

# عدد → حرف (۱ → ا، نه آ)
num_to_letter = {}
for key, val in letters.items():
    if val == '1':
        num_to_letter[val] = 'ا'
    elif val not in num_to_letter:
        num_to_letter[val] = key

# اعداد به یونانی (جداگانه برای ۰ و ۱)
number_to_greek = {
    '0': 'ο',    # امیکرون (صفر)
    '1': 'α',    # آلفا (یک)
    '2': 'β',    # بتا
    '3': 'γ',    # گاما
    '4': 'δ',    # دلتا
    '5': 'ε',    # اپسیلون
    '6': 'ϛ',    # استیگما
    '7': 'ζ',    # زتا
    '8': 'η',    # اتا
    '9': 'θ',    # تتا
    '10': 'ι'    # یوتا
}

# دیکشنری معکوس (یونانی به عدد)
greek_to_num = {
    'ο': '0', 'α': '1', 'β': '2', 'γ': '3', 'δ': '4',
    'ε': '5', 'ϛ': '6', 'ζ': '7', 'η': '8', 'θ': '9', 'ι': '10'
}

numbers = {v: k for k, v in letters.items()}
persian_to_english = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
SPECIAL_PATTERN = re.compile(r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\u2600-\u27BF]|[!؟.،,;:؟؟٬٪×÷+-=@#$%^&*(){}<>~`\'"/|]')

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
        greek_buffer = []
        in_greek = False
        
        for part_type, part_text in parts:
            if part_type == "space":
                if greek_buffer:
                    result_parts.append('|' + '_'.join(greek_buffer) + '|')
                    greek_buffer = []
                    in_greek = False
                result_parts.append("•")
            elif part_type == "special":
                if greek_buffer:
                    result_parts.append('|' + '_'.join(greek_buffer) + '|')
                    greek_buffer = []
                    in_greek = False
                result_parts.append(part_text)
            else:
                nums = []
                for ch in part_text:
                    if ch in letters:
                        if greek_buffer:
                            result_parts.append('|' + '_'.join(greek_buffer) + '|')
                            greek_buffer = []
                            in_greek = False
                        nums.append(letters[ch])
                    elif ch.isdigit():
                        greek_buffer.append(number_to_greek.get(ch, ch))
                        in_greek = True
                    else:
                        if greek_buffer:
                            result_parts.append('|' + '_'.join(greek_buffer) + '|')
                            greek_buffer = []
                            in_greek = False
                        nums.append(ch)
                
                if greek_buffer:
                    nums.append('|' + '_'.join(greek_buffer) + '|')
                    greek_buffer = []
                    in_greek = False
                
                if nums:
                    result_parts.append("_".join(nums))
        
        if greek_buffer:
            result_parts.append('|' + '_'.join(greek_buffer) + '|')
        
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
        
        parts = []
        current = ""
        in_bracket = False
        
        for ch in line:
            if ch == '|':
                if in_bracket:
                    parts.append(('greek', current))
                    current = ""
                    in_bracket = False
                else:
                    if current:
                        parts.append(('normal', current))
                        current = ""
                    in_bracket = True
            else:
                current += ch
        
        if current:
            parts.append(('normal', current) if not in_bracket else ('greek', current))
        
        result_words = []
        current_word = ""
        
        for ptype, ptext in parts:
            if ptype == 'greek':
                tokens = ptext.split('_')
                for token in tokens:
                    if token in greek_to_num:
                        current_word += greek_to_num[token]
                    else:
                        current_word += token
            else:
                if '•' in ptext:
                    word_parts = ptext.split('•')
                    for i, wp in enumerate(word_parts):
                        if wp:
                            nums = wp.split('_')
                            for n in nums:
                                if n in num_to_letter:
                                    current_word += num_to_letter[n]
                                else:
                                    current_word += n
                        if i < len(word_parts) - 1:
                            result_words.append(current_word)
                            current_word = ""
                else:
                    if ptext:
                        nums = ptext.split('_')
                        for n in nums:
                            if n in num_to_letter:
                                current_word += num_to_letter[n]
                            else:
                                current_word += n
        
        if current_word:
            result_words.append(current_word)
        
        final_lines.append(" ".join(result_words))
    
    return "\n".join(final_lines)

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    add_user(user.id, user.first_name, user.last_name, user.username)
    text = """✨🔐 **Hidden Language** 🔐✨

👋 به ربات زبان مخفی خوش آمدید!

💠 **چطوری کار می‌کنه؟**
فقط پیام خودتو بفرست، من خودم تشخیص می‌دم که متن فارسیه یا کد مخفی!

**مثال:**
`سلام ۶` ➜ `15_27_1_28•|ϛ|`
`15_27_1_28•|ϛ|` ➜ `سلام 6`

⚡ **ویژگی‌ها:**
🔹 تبدیل سریع و هوشمند
🧠 تشخیص خودکار متن و کد
😎 پشتیبانی از اعداد یونانی (ο, α, β, γ, ...) با `|`
😈 حفظ کامل ایموجی‌ها
📜 ذخیره تاریخچه تبدیل‌ها
📊 آمار شخصی

📩 فقط پیام خودتو بفرست..."""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['about'])
def about_command(message):
    about_button(message)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    stats_button(message)

@bot.message_handler(commands=['history'])
def history_command(message):
    history_button(message)

def about_button(message):
    about_text = """ℹ️ **درباره ربات**

🤖 نسخه: 3.34
📅 1404/11/25

✅ تبدیل فارسی ↔ کد مخفی
✅ تشخیص خودکار
✅ پشتیبانی از اعداد یونانی (ο, α, β, γ, ...) با `|`
✅ تاریخچه و آمار"""
    bot.reply_to(message, about_text, parse_mode="Markdown")

def stats_button(message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    if stats:
        total, first = stats
        stats_text = f"📊 **آمار شما**\n\n📝 تعداد تبدیل‌ها: {total}\n📆 عضویت: {first[:10]}"
    else:
        stats_text = "📊 هنوز تبدیلی انجام ندادید!"
    bot.reply_to(message, stats_text, parse_mode="Markdown")

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

@bot.message_handler(func=lambda m: True)
def handler(message):
    user = message.from_user
    add_user(user.id, user.first_name, user.last_name, user.username)
    text = message.text or ""
    if not text or text.startswith("/"):
        return
    if text in ["ℹ️ درباره", "📊 آمار من", "📜 تاریخچه"]:
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
        conv_type = "encode_greek"
    else:
        result = decode(text)
        conv_type = "decode"
    
    update_conversion(user.id, text, result, conv_type)
    bot.reply_to(message, f"<code>{result}</code>", parse_mode="HTML")

print("🤖 ربات روشن شد...")
bot.set_my_commands([
    BotCommand("start", "شروع ربات"),
    BotCommand("about", "درباره ربات"),
    BotCommand("stats", "آمار من"),
    BotCommand("history", "تاریخچه"),
])
bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
