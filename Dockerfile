FROM python:3.12-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y netcat-openbsd git openssh-client && rm -rf /var/lib/apt/lists/*

# Копируем SSH-ключ
COPY id_ed25519 /root/.ssh/id_ed25519
RUN chmod 600 /root/.ssh/id_ed25519

# Добавляем GitHub в известные хосты
RUN mkdir -p /root/.ssh && touch /root/.ssh/known_hosts
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

CMD ["python", "main.py"]