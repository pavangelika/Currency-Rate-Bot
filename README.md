# CurrencyRate Bot - Мониторинг курсов валют
Бот для отслеживания актуальных курсов валют с удобным интерфейсом в Telegram. Получайте уведомления об изменениях курсов и конвертируйте валюты прямо в чате.
<hr>
### ✨ Возможности

🔔 Актуальные курсы ЦБ РФ

📩 Ежедневная рассылка выбранного курса

📊 Графики изменений за период

💲 Актуальные курсы валют в коммерческих банках твоего города

https://github.com/user-attachments/assets/15f86cfb-27ac-4128-9daf-c8884b831fb8

### 🚀 Как начать использовать
Просто перейдите в Telegram и начните общение с ботом:
👉 t.me/EyeRateBot

### 📌 Основные команды
Команда	Описание
/start	Начало работы с ботом
/rates	Текущие курсы валют
/convert	Конвертер валют
/graph USD	График изменений курса
/subscribe	Подписка на уведомления
/help	Справка по командам

###🛠 Технологии
Python 3.10+

aiogram 3.x (Telegram Bot Framework)

BeautifulSoup4/Requests (Парсинг данных)

Plotly (Визуализация графиков)

Apscheduler (Установка расписания)

Docker (Контейнеризация)

### 📦 Установка для разработки
Клонируйте репозиторий:

```bash
git clone https://github.com/pavangelika/CurrencyRate.git
cd CurrencyRate
```
Установите зависимости:
```bash
pip install -r requirements.txt
```
Создайте файл конфигурации .env:

```ini
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=ваш_telegram_id
```
Запустите бота:
```bash
python main.py
```
🐳 Запуск через Docker
```bash
docker-compose up --build
```

