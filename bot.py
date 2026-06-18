import telebot
import re

TOKEN = "8943897493:AAFSF1b4_7h5o3hVQmqR9_QYb0EpOCaf3pE"

bot = telebot.TeleBot(TOKEN)

letters = {
    'ا':'1','آ':'1',
    'ب':'2','پ':'3','ت':'4','ث':'5',
    'ج':'6','چ':'7','ح':'8','خ':'9',
    'د':'10','ذ':'11','ر':'12','ز':'13',
    'ژ':'14','س':'15','ش':'16','ص':'17',
    'ض':'18','ط':'19','ظ':'20','ع':'21',
    'غ':'22','ف':'23','ق':'24','ک':'25',
    'گ':'26','ل':'27','م':'28','ن':'29',
    'و':'30','ه':'31','ی':'32'
}

numbers = {v: k for k, v in letters.items()}
persian_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


@bot.message_handler(commands=['start'])
def start(message):

    text = """✨🔐 𝙃𝙞𝙙𝙙𝙚𝙣 𝙇𝙖𝙣𝙜𝙪𝙖𝙜𝙚 🔐✨

👋 به ربات زبان مخفی خوش آمدید

━━━━━━━━━━━━━━
💠 تبدیل متن فارسی ⇄ کد مخفی

✨ مثال:

سلام خوبی
➜ 15_27_1_28__9_30_2_32

15_27_1_28__9_30_2_32
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


def encode(text):

    lines = text.split("\n")
    final = []

    for line in lines:

        words = line.split()
        out_words = []

        for word in words:

            nums = []
            emoji = ""

            for ch in word:

                if ch in letters:
                    nums.append(letters[ch])

                elif ch.isdigit():
                    nums.append(ch)

                else:
                    emoji += ch

            result = "_".join(nums)

            if result and emoji:
                result += emoji
            elif emoji:
                result = emoji

            out_words.append(result)

        final.append("__".join(out_words))

    return "\n".join(final)


def decode(text):

    text = text.translate(persian_digits)

    lines = text.split("\n")
    final = []

    for line in lines:

        words = line.split("__")
        out_words = []

        for word in words:

            match = re.match(r'^([\d_]+)(.*)$', word)

            if match:
                code = match.group(1)
                emoji = match.group(2)
            else:
                code = ""
                emoji = word

            result = ""

            for c in code.split("_"):

                if c in numbers:
                    result += numbers[c]

            result += emoji
            out_words.append(result)

        final.append(" ".join(out_words))

    return "\n".join(final)


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

    bot.reply_to(
        message,
        result,
        disable_web_page_preview=True
    )


print("Bot started...")
bot.infinity_polling(
    skip_pending=True,
    timeout=20,
    long_polling_timeout=20
)
