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
            logger.info(f"The daily newsletter will not be sent to user {user_id}. Data has been published on {day}")
        elif course_today(selected_data, day) != f"Данные на {day} не опубликованы":
            await bot.send_message(user_id, course_today(selected_data, day))
            logger.info(f"The daily newsletter has been sent to user {user_id}.")
    except Exception as e:
        logger.error(f"Error. The daily newsletter has been not sent: {e}")


def schedule_daily_greeting(user_id, scheduler, selected_data, day):
    """Запланировать ежедневную рассылку в 7:00 по московскому времени."""
    job_id = f"daily_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return
    else:
            try:
                scheduler.add_job(
                    send_greeting,
                    CronTrigger(hour=7, minute=00, timezone='Europe/Moscow'),
                    args=[user_id, selected_data, day],
                    id=job_id
                )
                logger.info(f"Success. Task ID {job_id} has been added to scheduler.")
            except Exception as e:
                logger.error(e)

def schedule_interval_greeting(user_id, scheduler, selected_data, day): # Добавили scheduler в параметры
    """Запланировать отправку 'Привет!' каждые 30 секунд."""
    job_id = f"interval_greeting_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return
    else:
        try:
            scheduler.add_job(send_greeting, IntervalTrigger(seconds=30), args=[user_id, selected_data, day], id=job_id)
            logger.info(f"Success. Task ID {job_id} has been added to scheduler.")
        except Exception as e:
            logger.error(e)


def schedule_interval_user(user_id, reminder_text, minutes, scheduler):
    """Запланировать отправку напоминания через указанное количество минут."""
    job_id = f"interval_user_{user_id}"

    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return

    try:
        scheduler.add_job(
            send_reminder_message,
            IntervalTrigger(minutes=minutes),
            args=[user_id, reminder_text],
            id=job_id
        )
        logger.info(f"Success. Task ID {job_id} has been added to scheduler.")
        logger.info(f"Newsletter'{reminder_text}' has been scheduled for {user_id} in {minutes} minutes.")
    except Exception as e:
        logger.error(f"Error. Task ID {job_id} has not been added: {e}")


async def send_reminder_message(user_id, reminder_text):
    """Отправляет пользователю сохранённый текст напоминания."""
    try:
        await bot.send_message(chat_id=user_id, text=f"🔔 {reminder_text}")
        logger.info(f"Success. Reminder has been sent {user_id}")
    except Exception as e:
        logger.error(f"Error. Reminder has not been sent: {e}")

def schedule_unsubscribe(job_id, scheduler):
    # Удаляем задачи из расписания
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error(e)