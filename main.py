#main.py
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from handlers import user_handlers
from handlers.notifications import load_jobs_from_db
from handlers.user_handlers import init_db, db_pool
from keyboards.menu import set_main_menu
from logger.logging_settings import logger
from service.CbRF import currency

# Загружаем переменные из .env
load_dotenv()

async def main():
    # Инициализация базы данных
    await init_db()

    # Инициализируем MemoryStorage для хранения данных пользователей
    storage = MemoryStorage()

    # Инициализируем бота и диспетчер с хранилищем
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=storage)

    # Настройки для APScheduler
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
    }

    executors = {
        'default': ThreadPoolExecutor(20)
    }

    job_defaults = {
        'coalesce': True,  # Объединять пропущенные задачи
        'max_instances': 3  # Максимальное количество экземпляров задачи
    }

    # Создание планировщика
    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='Europe/Moscow'
    )

    # Настраиваем кнопку Menu
    await set_main_menu(bot)

    # Регистрируем роутеры в диспетчере
    dp.include_router(user_handlers.router)

    # Передаем планировщик в обработчики
    user_handlers.set_scheduler(scheduler)

    # Загрузка задач из базы данных
    await load_jobs_from_db(scheduler, db_pool)

    # Настраиваем логирование
    logger.info('Starting bot')
    currencies = currency()
    scheduler.start()

    try:
        # Пропускаем накопившиеся апдейты и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except asyncio.CancelledError:
        logger.info('Polling was cancelled')
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
    finally:
        # Закрываем сессию бота
        await bot.session.close()
        logger.info('Bot shutdown')
        scheduler.shutdown()  # Выключаем планировщик

if __name__ == '__main__':
    asyncio.run(main())