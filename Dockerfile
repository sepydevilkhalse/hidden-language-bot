FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY bot.db .
COPY Hidden_Language.apk .

# پورت پیش‌فرض برای Cloudflare Containers
EXPOSE 8080

CMD ["python", "bot.py"]
