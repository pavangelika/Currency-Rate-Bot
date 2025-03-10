FROM python:3.12-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y netcat-openbsd git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

CMD ["python", "main.py"]