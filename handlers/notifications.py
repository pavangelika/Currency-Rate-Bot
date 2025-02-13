# notifications.py

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from logger.logging_settings import logger
from aiogram import Bot
from config_data import config

from service.CbRF import course_today

bot = Bot(token=config.BOT_TOKEN)

async def send_greeting(user_id, selected_data, day):
    """Отправляет курс валют пользователю с указанным user_id."""
    try:
        if course_today(selected_data, day) == f"Данные на {day} не опубликованы":
            logger.info(f"Рассылка 'Курс валют завтра' не отправлена пользователю {user_id}. Курс валют на завтра неизвестен")
        elif course_today(selected_data, day) != f"Данные на {day} не опубликованы":
            await bot.send_message(user_id, course_today(selected_data, day))
            logger.info(f"Сообщение course_today() отправлено пользователю {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


def schedule_daily_greeting(user_id, scheduler, selected_data, day):
    """Запланировать ежедневную рассылку в 7:00 по московскому времени."""
    job_id = f"daily_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Задача с ID {job_id} уже существует. Пропускаем добавление.")
        return
    else:
            try:
                scheduler.add_job(
                    send_greeting,
                    CronTrigger(hour=7, minute=00, timezone='Europe/Moscow'),
                    args=[user_id, selected_data, day],
                    id=job_id
                )
                logger.info(f"Задача с ID {job_id} успешно добавлена.")
            except Exception as e:
                logger.error(e)

def schedule_interval_greeting(user_id, scheduler, selected_data, day): # Добавили scheduler в параметры
    """Запланировать отправку 'Привет!' каждые 2 секунды."""
    job_id = f"interval_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Задача с ID {job_id} уже существует. Пропускаем добавление.")
        return
    else:
        try:
            scheduler.add_job(send_greeting, IntervalTrigger(seconds=30), args=[user_id, selected_data, day], id=job_id)
            logger.info(f"Задача с ID {job_id} успешно добавлена.")
        except Exception as e:
            logger.error(e)


def schedule_interval_user(user_id, reminder_text, minutes, scheduler):
    """Запланировать отправку напоминания через указанное количество минут."""
    job_id = f"interval_user_{user_id}"

    if scheduler.get_job(job_id):
        logger.info(f"Задача {job_id} уже существует. Пропускаем добавление.")
        return

    try:
        scheduler.add_job(
            send_reminder_message,
            IntervalTrigger(minutes=minutes),
            args=[user_id, reminder_text],
            id=job_id
        )
        logger.info(f"Задача с ID {job_id} успешно добавлена.")
        logger.info(f"Напоминание '{reminder_text}' для {user_id} запланировано через {minutes} минут.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении напоминания: {e}")


async def send_reminder_message(user_id, reminder_text):
    """Отправляет пользователю сохранённый текст напоминания."""
    try:
        logger.info(f"Отправка напоминания '{reminder_text}' пользователю {user_id}")
        await bot.send_message(chat_id=user_id, text=f"🔔 {reminder_text}")
        logger.info(f"Напоминание успешно отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")

def schedule_unsubscribe(job_id, scheduler):
    # Удаляем задачи из расписания
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error(e)