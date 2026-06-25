import telebot
import re

TOKEN = "8943897493:AAEBKncLQgRKNZ0Gidw2WDtwYmQO_2_8GL4"

bot = telebot.TeleBot(TOKEN)

letters = {
    'ا':'1',
    'آ':'1',
    'ب':'2','پ':'3','ت':'4','ث':'5',
    'ج':'6','چ':'7','ح':'8','خ':'9',
    'د':'10','ذ':'11','ر':'12','ز':'13',
    'ژ':'14','س':'15','ش':'16','ص':'17',
    'ض':'18','ط':'19','ظ':'20','ع':'21',
    'غ':'22','ف':'23','ق':'24','ک':'25',
    'گ':'26','ل':'27','م':'28','ن':'29',
    'و':'30','ه':'31','ی':'32'
}

numbers = {
    '1': 'ا',
    '2': 'ب',
    '3': 'پ',
    '4': 'ت',
    '5': 'ث',
    '6': 'ج',
    '7': 'چ',
    '8': 'ح',
    '9': 'خ',
    '10': 'د',
    '11': 'ذ',
    '12': 'ر',
    '13': 'ز',
    '14': 'ژ',
    '15': 'س',
    '16': 'ش',
    '17': 'ص',
    '18': 'ض',
    '19': 'ط',
    '20': 'ظ',
    '21': 'ع',
    '22': 'غ',
    '23': 'ف',
    '24': 'ق',
    '25': 'ک',
    '26': 'گ',
    '27': 'ل',
    '28': 'م',
    '29': 'ن',
    '30': 'و',
    '31': 'ه',
    '32': 'ی'
}

persian_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

SPECIAL_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F]|'
    r'[\U0001F300-\U0001F5FF]|'
    r'[\U0001F680-\U0001F6FF]|'
    r'[\U0001F700-\U0001F77F]|'
    r'[\U0001F780-\U0001F7FF]|'
    r'[\U0001F800-\U0001F8FF]|'
    r'[\U0001F900-\U0001F9FF]|'
    r'[\U0001FA00-\U0001FA6F]|'
    r'[\U0001FA70-\U0001FAFF]|'
    r'[\U00002702-\U000027B0]|'
    r'[\U000024C2-\U0001F251]|'
    r'[\u2600-\u27BF]|'
    r'[!؟.،,;:؟؟٬٪×÷+-=@#$%^&*()_\[\]{}<>~`\'"\\/|]'
)


@bot.message_handler(commands=['start'])
def start(message):

    text = """✨🔐 𝙃𝙞𝙙𝙙𝙚𝙣 𝙇𝙖𝙣𝙜𝙪𝙖𝙜𝙚 🔐✨

👋 به ربات زبان مخفی خوش آمدید

━━━━━━━━━━━━━━
💠 تبدیل متن فارسی ⇄ کد مخفی

✨ مثال:

سلام خوبی
➜ 15_27_1_28•9_30_2_32

15_27_1_28•9_30_2_32
➜ سلام خوبی

سلام😁
➜ 15_27_1_28😁

━━━━━━━━━━━━━━

⚡ ویژگی‌ها:
🔹 تبدیل سریع و هوشمند
🧠 تشخیص خودکار متن و کد
😎 پشتیبانی از اعداد فارسی و انگلیسی
😈 حفظ کامل ایموجی‌ها
🔐 رمزگذاری سبک و سریع

📩 فقط پیام خودتو بفرست...
"""

    bot.send_message(message.chat.id, text)

    try:
        loading = bot.send_message(
            message.chat.id,
            "📦 در حال ارسال برنامه..."
        )

        bot.delete_message(
            message.chat.id,
            loading.message_id
        )

        with open("Hidden-Langauage.apk", "rb") as apk:
            bot.send_document(
                message.chat.id,
                apk,
                caption="🔥 Hidden Language 🔐\n📱 برنامه رسمی زبان مخفی"
            )

    except:
        pass


def validate(text):
    text = text.translate(persian_digits)
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
                        nums.append(ch)
                if nums:
                    result_parts.append("_".join(nums))

        final_lines.append("".join(result_parts))

    return "\n".join(final_lines)


def decode(text):
    text = text.translate(persian_digits)
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

            match = re.match(r'^([\d_]+)(.*)$', part)
            if match:
                code = match.group(1)
                special = match.group(2)
                result = ""
                for c in code.split("_"):
                    if c in numbers:
                        result += numbers[c]
                result += special
                result_words.append(result)
            else:
                result_words.append(part)

        final_lines.append(" ".join(result_words))

    return "\n".join(final_lines)


@bot.message_handler(func=lambda m: True)
def handler(message):

    text = message.text or ""

    if not text:
        return

    if text.startswith("/"):
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
        bot.reply_to(
            message,
            "❌ فقط متن فارسی وارد کنید."
        )
        return

    if not validate(text):
        bot.reply_to(
            message,
            "❌ عدد وارد شده در زبان نمی‌باشد."
        )
        return

    if re.search(r'\d', text):
        result = decode(text)
    else:
        result = encode(text)

    # ارسال با <code> برای کپی (علامت‌ها داخل <code> قرار میگیرن)
    bot.reply_to(
        message,
        f"<code>{result}</code>",
        parse_mode="HTML"
    )


print("Bot started...")
bot.infinity_polling(
    skip_pending=True,
    timeout=20,
    long_polling_timeout=20
)
