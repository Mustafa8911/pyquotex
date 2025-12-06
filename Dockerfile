FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# اسم ملف البوت لديك
CMD ["python", "rsi_otc_bot.py"]
