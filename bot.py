import telebot
import re
import sqlite3
import html
import logging
import time
import os
from datetime import datetime, timedelta
from functools import wraps
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    BotCommand,
    ReplyParameters
)
import emoji
from flask import Flask, request, jsonify
import requests

# ==============================================
# تنظیمات اصلی
# ==============================================
TOKEN = "8943897493:AAEBKncLQgRKNZ0Gidw2WDtwYmQO_2_8GL4"
RATE_LIMIT = 5
RATE_LIMIT_TIME = 60
VERSION = "3.3.4"
MAX_TELEGRAM_MESSAGE = 4096

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
# Flask App برای Webhook
# ==============================================
app = Flask(__name__)

# ==============================================
# دیکشنری‌ها (کد قبلی)
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
    '5': 'ε', '6': 'π', '7': 'ζ', '8': 'η', '9': 'θ'
}

greek_to_num = {
    'ο': '0', 'α': '1', 'β': '2', 'γ': '3', 'δ': '4',
    'ε': '5', 'π': '6', 'ζ': '7', 'η': '8', 'θ': '9'
}

VALID_GREEK = set(greek_to_num.keys())

persian_to_english = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
arabic_to_persian = str.maketrans({
    'ي': 'ی', 'ك': 'ک', 'ة': 'ه'
})

ZERO_WIDTH = ['\u200c', '\u200d', '\u200b', '\u2060', '\ufeff']
RTL_LTR_MARKS = ['\u200e', '\u200f', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e']

def clean_text(text):
    if not text:
        return text
    text = text.translate(arabic_to_persian)
    text = text.replace('ـ', '')
    for z in ZERO_WIDTH:
        text = text.replace(z, '')
    for m in RTL_LTR_MARKS:
        text = text.replace(m, '')
    text = text.replace('\t', ' ')
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    text = text.translate(persian_to_english)
    return text

def remove_first_mention(text, mention):
    if not text or not mention:
        return text
    pattern = r'^@?' + re.escape(mention) + r'\s*'
    return re.sub(pattern, '', text)

def split_message(text, size=MAX_TELEGRAM_MESSAGE):
    parts = []
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        if cut == -1:
            cut = text.rfind(" ", 0, size)
        if cut == -1:
            cut = size
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts

def validate_code(text):
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
                    if token and token not in VALID_GREEK:
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

def tokenize(text):
    tokens = []
    i = 0
    emoji_list = emoji.emoji_list(text)
    emoji_positions = {e['match_start']: e['match_end'] for e in emoji_list}
    
    while i < len(text):
        if i in emoji_positions:
            end = emoji_positions[i]
            tokens.append(('EMOJI', text[i:end]))
            i = end
            continue
        if text[i].isdigit():
            num = ''
            while i < len(text) and text[i].isdigit():
                num += text[i]
                i += 1
            tokens.append(('NUMBER', num))
            continue
        if text[i] in letter_to_num or text[i] in 'آ':
            tokens.append(('PERSIAN', text[i]))
            i += 1
            continue
        if text[i] in ['•', '|', '_', ' ']:
            tokens.append(('SEPARATOR', text[i]))
            i += 1
            continue
        tokens.append(('OTHER', text[i]))
        i += 1
    return tokens

def convert_number_to_greek(num_str):
    result = []
    for ch in num_str:
        if ch.isdigit():
            result.append(number_to_greek.get(ch, ch))
        else:
            result.append(ch)
    return '_'.join(result)

def encode(text):
    try:
        text = clean_text(text)
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
                    greek_buffer.append(convert_number_to_greek(token_value))
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
                else:
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
    try:
        text = clean_text(text)
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
                else:
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

def detect_conversion_type(text):
    text = clean_text(text)
    
    if re.search(r'[ا-ی]', text):
        return 'encode'
    
    if re.match(r'^[0-9_•|α-ωοπϛΑ-ΩΟϚ]+$', text, re.UNICODE):
        return 'decode'
    
    if re.search(r'[α-ωοπϛ]', text) or re.search(r'[Α-ΩΟϚ]', text):
        return 'decode'
    
    if '•' in text or '|' in text:
        return 'decode'
    
    if '_' in text and re.search(r'\d', text):
        return 'decode'
    
    return 'encode'

def send_long_message(chat_id, text, reply_to_message_id=None, parse_mode="HTML"):
    if len(text) <= MAX_TELEGRAM_MESSAGE:
        if reply_to_message_id:
            bot.send_message(
                chat_id,
                f"<code>{text}</code>",
                parse_mode=parse_mode,
                reply_parameters=ReplyParameters(message_id=reply_to_message_id)
            )
        else:
            bot.send_message(chat_id, f"<code>{text}</code>", parse_mode=parse_mode)
        return
    
    parts = split_message(text)
    total = len(parts)
    
    for i, part in enumerate(parts, 1):
        caption = f"📄 بخش {i} از {total}"
        if i == 1 and reply_to_message_id:
            bot.send_message(
                chat_id,
                f"<code>{part}</code>",
                parse_mode=parse_mode,
                reply_parameters=ReplyParameters(
                    message_id=reply_to_message_id,
                    quote=caption
                )
            )
        else:
            bot.send_message(
                chat_id,
                f"<code>{part}</code>",
                parse_mode=parse_mode
            )

# ==============================================
# هندلرهای ربات (برای Webhook)
# ==============================================

def handle_message(message):
    """پردازش پیام‌های دریافتی"""
    try:
        user = message.from_user
        # add_user(user.id, user.first_name, user.last_name, user.username)
        
        text = message.text or ""
        if not text or text.startswith("/"):
            return
        
        if text in ["ℹ️ درباره", "📊 آمار من", "📜 تاریخچه"]:
            return
        
        # پردازش گروه‌ها
        if message.chat.type in ["group", "supergroup"]:
            # BOT_USERNAME رو باید تنظیم کنی
            pass
        
        conv_type = detect_conversion_type(text)
        
        if conv_type == 'encode':
            result = encode(text)
        else:
            result = decode(text)
        
        # update_conversion(user.id, text, result, conv_type)
        
        # ارسال پاسخ
        bot.send_message(message.chat.id, f"<code>{result}</code>", parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")

@bot.message_handler(func=lambda m: True)
def webhook_handler(message):
    handle_message(message)

# ==============================================
# Webhook Endpoint
# ==============================================
@app.route('/', methods=['POST'])
def webhook():
    try:
        # دریافت داده از تلگرام
        data = request.get_json()
        
        if not data:
            return jsonify({'ok': False, 'error': 'No data'}), 400
        
        # پردازش پیام
        try:
            # استفاده از telebot برای پردازش
            bot.process_new_updates([telebot.types.Update.de_json(data)])
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500
        
        return jsonify({'ok': True})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/', methods=['GET'])
def health():
    return 'Bot is running! 🚀', 200

# ==============================================
# تنظیم Webhook روی تلگرام
# ==============================================
def set_webhook():
    """تنظیم Webhook روی تلگرام"""
    try:
        # لینک سرویس (برای Cloudflare باید تنظیم بشه)
        webhook_url = os.environ.get('WEBHOOK_URL', 'https://hidden-language-bot.workers.dev/')
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set: {result}")
        return result
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False

# ==============================================
# اجرا
# ==============================================
if __name__ == '__main__':
    # تنظیم Webhook (فقط یکبار)
    set_webhook()
    
    # اجرای Flask
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
