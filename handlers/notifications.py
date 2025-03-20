# notifications.py
import os

from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database.db import get_last_course_data, update_last_course_data, get_all_jobs, create_db_pool
from logger.logging_settings import logger
from service.CbRF import course_today

bot = Bot(token=os.getenv("BOT_TOKEN"))

from tenacity import retry, wait_exponential, stop_after_attempt
from asyncio import run as aiorun

def sync_send_greeting(user_id, selected_data, day):
    """Обертка для асинхронной функции send_greeting."""
    aiorun(send_greeting(user_id, selected_data, day))

async def load_jobs_from_db(scheduler, db_pool):
    """Загружает задачи из базы данных в планировщик."""
    try:
        # Получаем все задачи из базы данных
        jobs = await get_all_jobs(db_pool)
        for job in jobs:
            try:
                scheduler.add_job(
                    send_greeting,
                    IntervalTrigger(hours=1),
                    args=[job['user_id'], job['selected_data'], job['day'], db_pool],
                    id=job['job_id']
                )
                logger.info(f"Job {job['job_id']} loaded from DB.")
            except Exception as e:
                logger.error(f"Failed to load job {job['job_id']}: {e}")
    except Exception as e:
        logger.error(f"Error loading jobs from DB: {e}")


@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(5))
async def send_message_with_retry(user_id, text):
    await bot.send_message(chat_id=user_id, text=text)

async def send_greeting(user_id, selected_data, day):
    """Отправляет курс валют пользователю."""
    db_pool = await create_db_pool()  # Создаем соединение с базой данных внутри задачи
    try:
        course_data = course_today(selected_data, day)
        single_line = " ".join(course_data.splitlines())
        logger.info(f"Course data for {day}: {single_line}")

        if course_data != f"Данные на {day} не опубликованы":
            last_course_data = await get_last_course_data(db_pool, user_id)

            if course_data != last_course_data:
                await bot.send_message(user_id, course_data)
                await update_last_course_data(db_pool, user_id, course_data)
                logger.info(f"New course data sent to user {user_id}.")
            else:
                logger.info(f"Course data for user {user_id} has not changed. Skipping send.")
    except Exception as e:
        logger.error(f"Error. The daily newsletter has been not sent: {e}")
    finally:
        await db_pool.close()  # Закрываем соединение с базой данных


def schedule_daily_greeting(user_id, scheduler, selected_data, day):
    """Запланировать ежедневную рассылку в 7:00 по московскому времени."""
    job_id = f"job_daily_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return
    else:
        try:
            scheduler.add_job(
                send_greeting,
                CronTrigger(hour=7, minute=0, timezone='Europe/Moscow'),
                args=[user_id, selected_data, day],  # Передаем bot как аргумент
                id=job_id
            )
        except Exception as e:
            logger.error(e)
    return job_id


def schedule_interval_greeting(user_id, scheduler, selected_data, day):  # Добавили scheduler в параметры
    """Запланировать отправку 'Привет!' каждые 30 секунд."""
    job_id = f"job_interval_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return
    else:
        try:
            scheduler.add_job(sync_send_greeting, IntervalTrigger(minutes=1), args=[user_id, selected_data, day], id=job_id)
            logger.info(f"Success. Task ID {job_id} has been added to scheduler.")
        except Exception as e:
            logger.error(e)
    return job_id


def schedule_interval_user(user_id, reminder_text, minutes, scheduler):
    """Запланировать отправку напоминания через указанное количество минут."""
    job_id = f"Job_interval_user_{user_id}"

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
    return job_id


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
