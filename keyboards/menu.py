from aiogram import Bot
from aiogram.types import BotCommand

from lexicon.lexicon import LEXICON_MENU


async def set_main_menu(bot: Bot):
    """ Функция для настройки кнопки Menu бота """
    main_menu_commands = [
        BotCommand(
            command=item["command"],
            description=item["name"]
        ) for item in LEXICON_MENU
    ]
    await bot.set_my_commands(main_menu_commands)
