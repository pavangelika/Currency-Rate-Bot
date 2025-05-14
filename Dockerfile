FROM python:3.12-slim

## Устанавливаем SSH-клиент
#RUN apt-get update && apt-get install -y openssh-client git
#
## Создаём папку для SSH-ключей (если её нет)
#RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh
#
## Добавляем GitHub в known_hosts
#RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "main.py"]