# main.py
import asyncio
from aiogram import Bot, Dispatcher
from config_data import config
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import user_handlers, user_remind
from keyboards.menu import set_main_menu
from logger.logging_settings import logger
from service.CbRF import currency
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def main():
    # Инициализируем MemoryStorage для хранения данных пользователей
    storage = MemoryStorage()

    # Инициализируем бота и диспетчер с хранилищем
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Инициализируем планировщик
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')

    # Настраиваем кнопку Menu
    await set_main_menu(bot)

    # Регистрируем роутеры в диспетчере
    dp.include_router(user_remind.router)
    dp.include_router(user_handlers.router)

    # Передаем планировщик в обработчики
    user_remind.set_scheduler(scheduler)
    user_handlers.set_scheduler(scheduler)

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
    finally:
        # Закрываем сессию бота
        await bot.session.close()
        logger.info('Bot shutdown')
        scheduler.shutdown()  # Выключаем планировщик

if __name__ == '__main__':
    asyncio.run(main())