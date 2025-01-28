# notifications.py

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from logging_settings import logger
from aiogram import Bot
from config_data import config

from service.CbRF import course_today

bot = Bot(token=config.BOT_TOKEN)

async def send_greeting(user_id):
    """Отправляет сообщение 'Привет!' пользователю с указанным user_id."""
    try:
        # await bot.send_message(chat_id=user_id, text="Привет!")
        await bot.send_message(user_id, course_today())
        logger.info(f"Сообщение course_today() отправлено пользователю {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")


def schedule_daily_greeting(user_id, scheduler):
    """Запланировать ежедневную рассылку в 10:00 по московскому времени."""
    job_id = f"daily_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Задача с ID {job_id} уже существует. Пропускаем добавление.")
        return
    else:
            try:
                scheduler.add_job(
                    send_greeting,
                    CronTrigger(hour=7, minute=00, timezone='Europe/Moscow'),
                    args=[user_id],
                    id=job_id
                )
                logger.info(f"Задача с ID {job_id} успешно добавлена.")
            except Exception as e:
                logger.error(e)

def schedule_interval_greeting(user_id, scheduler): # Добавили scheduler в параметры
    """Запланировать отправку 'Привет!' каждые 2 секунды."""
    job_id = f"interval_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Задача с ID {job_id} уже существует. Пропускаем добавление.")
        return
    else:
        try:
            scheduler.add_job(send_greeting, IntervalTrigger(minutes=10), args=[user_id], id=f"interval_greeting_{user_id}")
            logger.info(f"Задача с ID {job_id} успешно добавлена.")
        except Exception as e:
            logger.error(e)

def schedule_unsubscribe(job_id, scheduler):
    # Удаляем задачи из расписания
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error(e)