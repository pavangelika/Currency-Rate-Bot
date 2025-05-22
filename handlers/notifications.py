# notifications.py
import datetime
import os
import re  # Добавьте эту строку
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
    aiorun(send_greeting(user_id, selected_data))

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


async def send_greeting(user_id, selected_data):
    """Отправляет курсы валют пользователю с учетом всех выбранных валют."""
    db_pool = await create_db_pool()
    try:
        logger.info(f"Обработка пользователя {user_id}, выбрано валют: {len(selected_data)}")

        day = datetime.date.today().strftime("%d/%m/%Y")
        logger.debug(f"Актуальная дата: {day}")

        # Получаем текущие курсы
        course_data = course_today(selected_data, day)
        logger.debug(f"RAW данные курсов:\n{course_data}")

        if course_data == f"Данные на {day} не опубликованы":
            logger.warning("Данные не опубликованы, отправка отменена")
            return

        # Получаем последние данные из БД
        last_course_data = await get_last_course_data(db_pool, user_id)
        logger.debug(f"Данные из БД:\n{last_course_data or 'Нет данных'}")

        has_changes = False
        currency_changes = []

        # Обрабатываем каждую валюту
        for currency in selected_data:
            currency_name = currency['name']
            logger.info(f"Анализ валюты: {currency_name}")

            # Генерируем паттерн поиска
            pattern = re.compile(
                fr"{re.escape(currency_name)}\s*=\s*(\d+[,.]\d+)",
                re.IGNORECASE
            )

            # Парсим текущий курс
            current_match = pattern.search(course_data)
            if not current_match:
                logger.error(f"Курс {currency_name} не найден!")
                continue

            current = float(current_match.group(1).replace(',', '.'))

            # Парсим предыдущий курс
            last = None
            if last_course_data:
                last_match = pattern.search(last_course_data)
                if last_match:
                    last = float(last_match.group(1).replace(',', '.'))

            # Анализ изменений
            logger.debug(f"{currency_name}: текущий {current} | предыдущий {last}")

            if last is None or current != last:
                logger.info(f"Обнаружено изменение курса {currency_name}")
                has_changes = True
                currency_changes.append(f"{currency_name}: {last or 'нет данных'} → {current}")

        # Логика отправки сообщения
        if has_changes:
            logger.info(f"Изменения обнаружены в {len(currency_changes)} валютах")
            await bot.send_message(user_id, course_data)
            await update_last_course_data(db_pool, user_id, course_data)
            logger.info("Данные обновлены и отправлены пользователю")

            # Детальный лог изменений
            changes_log = "\n".join(currency_changes)
            logger.debug(f"Детали изменений:\n{changes_log}")
        else:
            logger.info("Изменений не обнаружено")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}", exc_info=True)
        logger.error(f"Контекст: user={user_id}, data={selected_data}")

    finally:
        await db_pool.close()
        logger.info("Соединение с БД закрыто")

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


def schedule_interval_greeting(user_id, scheduler, selected_data):  # Добавили scheduler в параметры
    """Запланировать отправку 'Привет!' каждые 30 секунд."""
    job_id = f"job_interval_{user_id}"
    if scheduler.get_job(job_id):
        logger.info(f"Task {job_id} already exists. Skipping addition")
        return
    else:
        try:
            scheduler.add_job(sync_send_greeting, IntervalTrigger(minutes=1), args=[user_id, selected_data, datetime.date.today().strftime("%d/%m/%Y")], id=job_id)
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
