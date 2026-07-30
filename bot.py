import telebot
import re
import sqlite3
import html
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand
)
import emoji

# ==============================================
# تنظیمات اصلی
# ==============================================
TOKEN = "8943897493:AAEBKncLQgRKNZ0Gidw2WDtwYmQO_2_8GL4"
MAX_TEXT_LENGTH = 4000
RATE_LIMIT = 5  # درخواست در دقیقه
RATE_LIMIT_TIME = 60

# ==============================================
# لاگ‌گیری
# ==============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)

# ==============================================
# Cache برای جلوگیری از درخواست اضافی
# ==============================================
BOT_USERNAME = None
try:
    BOT_USERNAME = bot.get_me().username
except Exception as e:
    logger.error(f"Failed to get bot username: {e}")

# ==============================================
# دیکشنری‌های اصلی
# ==============================================
letter_to_num = {
    'ا': '1', 'آ': '1', 'ب': '2', 'پ': '3', 'ت': '4', 'ث': '5',
    'ج': '6', 'چ': '7', 'ح': '8', 'خ': '9', 'د': '10', 'ذ': '11',
    'ر': '12', 'ز': '13', 'ژ': '14', 'س': '15', 'ش': '16', 'ص': '17',
    'ض': '18', 'ط': '19', 'ظ': '20', 'ع': '21', 'غ': '22', 'ف': '23',
    'ق': '24', 'ک': '25', 'گ': '26', 'ل': '27', 'م': '28', 'ن': '29',
    'و': '30', 'ه': '31', 'ی': '32'
}

num_to_letter = {}
for key, val in letter_to_num.items():
    if val == '1':
        num_to_letter[val] = 'ا'
    elif val not in num_to_letter:
        num_to_letter[val] = key

number_to_greek = {
    '0': 'ο', '1': 'α', '2': 'β', '3': 'γ', '4': 'δ',
    '5': 'ε', '6': 'ϛ', '7': 'ζ', '8': 'η', '9': 'θ'
}

greek_to_num = {
    'ο': '0', 'α': '1', 'β': '2', 'γ': '3', 'δ': '4',
    'ε': '5', 'ϛ': '6', 'ζ': '7', 'η': '8', 'θ': '9'
}

# ==============================================
# تبدیل‌ها و پاکسازی
# ==============================================
persian_to_english = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
arabic_to_persian = str.maketrans({
    'ي': 'ی', 'ك': 'ک', 'ة': 'ه'
})

ZERO_WIDTH = ['\u200c', '\u200d', '\u200b', '\u2060', '\ufeff']
RTL_LTR_MARKS = ['\u200e', '\u200f', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e']

def clean_text(text):
    """پاکسازی کامل متن ورودی"""
    if not text:
        return text
    
    # تبدیل عربی به فارسی
    text = text.translate(arabic_to_persian)
    
    # حذف کشیدگی
    text = text.replace('ـ', '')
    
    # حذف کاراکترهای نامرئی
    for z in ZERO_WIDTH:
        text = text.replace(z, '')
    
    # حذف RTL/LTR Marks
    for m in RTL_LTR_MARKS:
        text = text.replace(m, '')
    
    # تبدیل تب به فاصله
    text = text.replace('\t', ' ')
    
    # تبدیل چند فاصله به یکی
    text = re.sub(r' +', ' ', text)
    
    # حذف فاصله اول و آخر
    text = text.strip()
    
    # تبدیل اعداد فارسی به انگلیسی
    text = text.translate(persian_to_english)
    
    return text

# ==============================================
# اعتبارسنجی کد مخفی
# ==============================================
def validate_code(text):
    """اعتبارسنجی کامل کد مخفی"""
    errors = []
    
    if text.count('|') % 2 != 0:
        errors.append("❌ تعداد | باید زوج باشد")
    
    if '||' in text:
        errors.append("❌ | خالی مجاز نیست")
    
    if '__' in text:
        errors.append("❌ __ مجاز نیست")
    
    if text.startswith('_') or text.endswith('_'):
        errors.append("❌ _ در ابتدا یا انتها مجاز نیست")
    
    if '••' in text:
        errors.append("❌ •• مجاز نیست")
    
    in_bracket = False
    bracket_content = ""
    for ch in text:
        if ch == '|':
            if in_bracket:
                tokens = bracket_content.split('_')
                for token in tokens:
                    if token and token not in greek_to_num:
                        errors.append(f"❌ کاراکتر نامعتبر در |: {token}")
                bracket_content = ""
                in_bracket = False
            else:
                in_bracket = True
                bracket_content = ""
        elif in_bracket:
            bracket_content += ch
    
    outside_bracket = re.sub(r'\|[^|]*\|', '', text)
    nums = re.findall(r'\d+', outside_bracket)
    for num in nums:
        if int(num) > 32:
            errors.append(f"❌ عدد {num} معتبر نیست (بزرگتر از ۳۲)")
    
    return errors

# ==============================================
# Tokenizer (با پشتیبانی کامل از ایموجی)
# ==============================================
def tokenize(text):
    """تجزیه متن به توکن‌ها با پشتیبانی کامل از ایموجی"""
    tokens = []
    i = 0
    
    # تشخیص ایموجی با کتابخانه emoji
    emoji_list = emoji.emoji_list(text)
    emoji_positions = {e['match_start']: e['match_end'] for e in emoji_list}
    
    while i < len(text):
        # ایموجی
        if i in emoji_positions:
            end = emoji_positions[i]
            tokens.append(('EMOJI', text[i:end]))
            i = end
            continue
        
        # عدد
        if text[i].isdigit():
            num = ''
            while i < len(text) and text[i].isdigit():
                num += text[i]
                i += 1
            tokens.append(('NUMBER', num))
            continue
        
        # حرف فارسی
        if text[i] in letter_to_num or text[i] in 'آ':
            tokens.append(('PERSIAN', text[i]))
            i += 1
            continue
        
        # جداکننده‌ها
        if text[i] in ['•', '|', '_']:
            tokens.append(('SEPARATOR', text[i]))
            i += 1
            continue
        
        # بقیه
        tokens.append(('OTHER', text[i]))
        i += 1
    
    return tokens

# ==============================================
# دیتابیس (با WAL و Context Manager)
# ==============================================
def get_db_connection():
    conn = sqlite3.connect('bot.db', timeout=10)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    first_join TEXT,
                    last_active TEXT,
                    total_conversions INTEGER DEFAULT 0
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    input_text TEXT,
                    output_text TEXT,
                    conversion_type TEXT,
                    timestamp TEXT
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")

init_db()

def add_user(user_id, first_name, last_name, username):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if c.fetchone():
                c.execute('''
                    UPDATE users 
                    SET last_active = ?, first_name = ?, last_name = ?, username = ?
                    WHERE user_id = ?
                ''', (now, first_name, last_name, username, user_id))
            else:
                c.execute('''
                    INSERT INTO users (user_id, first_name, last_name, username, first_join, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, first_name, last_name, username, now, now))
            conn.commit()
            logger.info(f"User {user_id} added/updated")
    except Exception as e:
        logger.error(f"Error adding user: {e}")

def update_conversion(user_id, input_text, output_text, conv_type):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute('''
                INSERT INTO conversions (user_id, input_text, output_text, conversion_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, input_text[:200], output_text[:200], conv_type, now))
            c.execute('''
                UPDATE users 
                SET total_conversions = total_conversions + 1
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error updating conversion: {e}")

def get_user_stats(user_id):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT total_conversions, first_join FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return None

def get_history(user_id, limit=5):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT input_text, output_text, timestamp 
                FROM conversions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            results = c.fetchall()
            return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return []

# ==============================================
# Rate Limit (ضد اسپم)
# ==============================================
rate_limit_store = {}

def rate_limit(func):
    @wraps(func)
    def wrapper(message):
        user_id = message.from_user.id
        now = time.time()
        
        if user_id not in rate_limit_store:
            rate_limit_store[user_id] = []
        
        # پاک کردن درخواست‌های قدیمی
        rate_limit_store[user_id] = [
            t for t in rate_limit_store[user_id] 
            if now - t < RATE_LIMIT_TIME
        ]
        
        if len(rate_limit_store[user_id]) >= RATE_LIMIT:
            bot.reply_to(message, f"⏳ لطفاً صبر کنید. حداکثر {RATE_LIMIT} درخواست در دقیقه.")
            return
        
        rate_limit_store[user_id].append(now)
        return func(message)
    return wrapper

# ==============================================
# توابع اصلی تبدیل
# ==============================================
def encode(text):
    """تبدیل فارسی به کد مخفی"""
    try:
        text = clean_text(text)
        
        if len(text) > MAX_TEXT_LENGTH:
            return f"❌ متن خیلی طولانی است (حداکثر {MAX_TEXT_LENGTH} کاراکتر)"
        
        lines = text.split('\n')
        result_lines = []

        for line in lines:
            if not line.strip():
                result_lines.append('')
                continue

            tokens = tokenize(line)
            output_parts = []
            current_part = []
            greek_buffer = []
            
            for token_type, token_value in tokens:
                if token_type == 'PERSIAN':
                    if greek_buffer:
                        current_part.append('|' + '_'.join(greek_buffer) + '|')
                        greek_buffer = []
                    current_part.append(letter_to_num[token_value])
                
                elif token_type == 'NUMBER':
                    greek_buffer.append(number_to_greek.get(token_value, token_value))
                
                elif token_type == 'SEPARATOR':
                    if token_value == ' ':
                        if greek_buffer:
                            current_part.append('|' + '_'.join(greek_buffer) + '|')
                            greek_buffer = []
                        if current_part:
                            output_parts.append('_'.join(current_part))
                            current_part = []
                        output_parts.append('•')
                    else:
                        if greek_buffer:
                            current_part.append('|' + '_'.join(greek_buffer) + '|')
                            greek_buffer = []
                        if current_part:
                            output_parts.append('_'.join(current_part))
                            current_part = []
                        output_parts.append(token_value)
                
                elif token_type == 'EMOJI':
                    if greek_buffer:
                        current_part.append('|' + '_'.join(greek_buffer) + '|')
                        greek_buffer = []
                    if current_part:
                        output_parts.append('_'.join(current_part))
                        current_part = []
                    output_parts.append(token_value)
                
                else:  # OTHER
                    if greek_buffer:
                        current_part.append('|' + '_'.join(greek_buffer) + '|')
                        greek_buffer = []
                    if current_part:
                        output_parts.append('_'.join(current_part))
                        current_part = []
                    output_parts.append(token_value)
            
            if greek_buffer:
                current_part.append('|' + '_'.join(greek_buffer) + '|')
                greek_buffer = []
            if current_part:
                output_parts.append('_'.join(current_part))

            result_lines.append(''.join(output_parts))

        result = '\n'.join(result_lines)
        return html.escape(result)
        
    except Exception as e:
        logger.error(f"Encode error: {e}")
        return f"❌ خطا در تبدیل: {str(e)}"

def decode(text):
    """تبدیل کد مخفی به فارسی"""
    try:
        text = clean_text(text)
        
        if len(text) > MAX_TEXT_LENGTH:
            return f"❌ متن خیلی طولانی است (حداکثر {MAX_TEXT_LENGTH} کاراکتر)"
        
        errors = validate_code(text)
        if errors:
            return "\n".join(errors[:3])
        
        lines = text.split('\n')
        final_lines = []

        for line in lines:
            if not line.strip():
                final_lines.append("")
                continue

            tokens = tokenize(line)
            result_words = []
            current_word = ""
            in_bracket = False
            bracket_content = ""
            
            for token_type, token_value in tokens:
                if token_type == 'SEPARATOR' and token_value == '|':
                    if in_bracket:
                        in_bracket = False
                        greek_tokens = bracket_content.split('_')
                        for gt in greek_tokens:
                            if gt in greek_to_num:
                                current_word += greek_to_num[gt]
                            else:
                                return f"❌ کاراکتر نامعتبر در |: {gt}"
                        bracket_content = ""
                    else:
                        in_bracket = True
                        bracket_content = ""
                    continue
                
                if in_bracket:
                    bracket_content += token_value
                    continue
                
                if token_type == 'NUMBER':
                    num = int(token_value)
                    if num > 32:
                        return f"❌ عدد {num} معتبر نیست (بزرگتر از ۳۲)"
                    if num_to_letter.get(token_value):
                        current_word += num_to_letter[token_value]
                    else:
                        current_word += token_value
                
                elif token_type == 'SEPARATOR':
                    if token_value == '•':
                        if current_word:
                            result_words.append(current_word)
                            current_word = ""
                
                elif token_type == 'EMOJI':
                    if current_word:
                        result_words.append(current_word)
                        current_word = ""
                    result_words.append(token_value)
                
                elif token_type == 'PERSIAN':
                    current_word += token_value
                
                else:  # OTHER
                    if current_word:
                        result_words.append(current_word)
                        current_word = ""
                    result_words.append(token_value)
            
            if current_word:
                result_words.append(current_word)
            
            final_lines.append(" ".join(result_words))

        result = '\n'.join(final_lines)
        return html.escape(result)
        
    except Exception as e:
        logger.error(f"Decode error: {e}")
        return f"❌ خطا در تبدیل: {str(e)}"

# ==============================================
# تشخیص خودکار نوع ورودی
# ==============================================
def detect_conversion_type(text):
    """تشخیص خودکار نوع ورودی با Regex کامل"""
    text = clean_text(text)
    
    # الگوی کد مخفی کامل
    code_pattern = r'^[0-9_•|α-ωοϛΑ-ΩΟϚ]+$'
    
    if re.match(code_pattern, text, re.UNICODE):
        return 'decode'
    
    if re.search(r'[α-ωοϛ]', text) or re.search(r'[Α-ΩΟϚ]', text):
        return 'decode'
    
    if '•' in text or '|' in text:
        return 'decode'
    
    if '_' in text and re.search(r'\d', text):
        return 'decode'
    
    return 'encode'

# ==============================================
# هندلرهای دستورات
# ==============================================
@bot.message_handler(commands=['start'])
@rate_limit
def start(message):
    user = message.from_user
    add_user(user.id, user.first_name, user.last_name, user.username)

    text = """✨🔐 **Hidden Language** 🔐✨

👋 به ربات زبان مخفی خوش آمدید!

💠 **چطوری کار می‌کنه؟**
فقط پیام خودتو بفرست، من خودم تشخیص می‌دم که متن فارسیه یا کد مخفی!

**مثال:**
`ا۱` ➜ `1|α|`
`1|α|` ➜ `ا1`
`سلام ۶` ➜ `15_27_1_28•|ϛ|`
`15_27_1_28•|ϛ|` ➜ `سلام 6`
`سلام ۶۷` ➜ `15_27_1_28•|ϛ_ζ|`
`15_27_1_28•|ϛ_ζ|` ➜ `سلام 67`

⚡ **ویژگی‌ها:**
🔹 تبدیل سریع و هوشمند
🧠 تشخیص خودکار متن و کد
😎 پشتیبانی از اعداد یونانی (ο, α, β, γ, ...) با `|`
😈 حفظ کامل ایموجی‌ها
📜 ذخیره تاریخچه تبدیل‌ها
📊 آمار شخصی

📩 فقط پیام خودتو بفرست..."""

    bot.reply_to(message, text, parse_mode="Markdown")

    try:
        with open('Hidden_Language.apk', 'rb') as apk:
            bot.send_document(
                message.chat.id,
                apk,
                caption="📱 **برنامه Hidden Language**\n\nدانلود و نصب کن! 🚀",
                parse_mode="Markdown"
            )
    except FileNotFoundError:
        logger.warning("APK file not found")

@bot.message_handler(commands=['about'])
@rate_limit
def about_command(message):
    about_text = """ℹ️ **درباره ربات**

🤖 نسخه: 4.0
📅 1404/11/25

✅ تبدیل فارسی ↔ کد مخفی
✅ تشخیص خودکار
✅ پشتیبانی از اعداد یونانی (ο, α, β, γ, ...) با `|`
✅ تاریخچه و آمار"""
    bot.reply_to(message, about_text, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
@rate_limit
def stats_command(message):
    user_id = message.from_user.id
    stats = get_user_stats(user_id)
    if stats:
        stats_text = f"📊 **آمار شما**\n\n📝 تعداد تبدیل‌ها: {stats['total_conversions']}\n📆 عضویت: {stats['first_join'][:10]}"
    else:
        stats_text = "📊 هنوز تبدیلی انجام ندادید!"
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.message_handler(commands=['history'])
@rate_limit
def history_command(message):
    user_id = message.from_user.id
    history = get_history(user_id, 5)
    if history:
        history_text = "📜 **۵ تبدیل اخیر:**\n\n"
        for i, record in enumerate(history, 1):
            history_text += f"{i}. `{record['input_text'][:30]}` ➜ `{record['output_text'][:30]}`\n"
            history_text += f"   📅 {record['timestamp'][:16]}\n\n"
    else:
        history_text = "📜 هنوز تبدیلی انجام ندادید!"
    bot.reply_to(message, history_text, parse_mode="Markdown")

# ==============================================
# هندلر اصلی پیام‌ها
# ==============================================
@bot.message_handler(func=lambda m: True)
@rate_limit
def handler(message):
    try:
        user = message.from_user
        add_user(user.id, user.first_name, user.last_name, user.username)
        
        text = message.text or ""
        if not text or text.startswith("/"):
            return
        
        if text in ["ℹ️ درباره", "📊 آمار من", "📜 تاریخچه"]:
            return
        
        if message.chat.type in ["group", "supergroup"]:
            if not BOT_USERNAME:
                return
            mention = f"@{BOT_USERNAME}"
            if mention not in text:
                return
            text = text.replace(mention, "").strip()
            if not text:
                return
        
        # جلوگیری از حروف انگلیسی
        if re.search(r'[A-Za-z\u0041-\u005A\u0061-\u007A]', text):
            bot.reply_to(message, "❌ فقط متن فارسی وارد کنید.")
            return
        
        conv_type = detect_conversion_type(text)
        
        if conv_type == 'encode':
            result = encode(text)
        else:
            result = decode(text)
        
        update_conversion(user.id, text, result, conv_type)
        bot.reply_to(message, f"<code>{result}</code>", parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==============================================
# اجرا
# ==============================================
logger.info("🤖 ربات Hidden Language نسخه 4.0 روشن شد...")
bot.set_my_commands([
    BotCommand("start", "🚀 شروع"),
    BotCommand("about", "ℹ️ درباره"),
    BotCommand("stats", "📊 آمار من"),
    BotCommand("history", "📜 تاریخچه"),
])

try:
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
except Exception as e:
    logger.error(f"Bot polling error: {e}")
