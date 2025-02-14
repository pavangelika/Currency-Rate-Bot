# user_handlers.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

# Инициализируем роутер уровня модуля
router = Router()

# @router.message(Command(commands=["chart"]))
# async def send_html_graph(message: Message):
#     dollarCod = 'R01235'
#     dollar = dinamic_course(dollarCod)
#     dollar_data = parse_xml_data(dollar)
#     # Генерация графика
#     file_path = graf_mobile(dollar_data)
#
#     # Создаем кнопку для Web App
#     button_mobile = InlineKeyboardButton(
#         text="График на телефоне",  # Текст на кнопке
#         web_app=types.WebAppInfo(url=config.GITHUB_PAGES)  # URL к размещенному HTML
#     )
#     button_pc = InlineKeyboardButton(
#         text="График на ПК",  # Текст на кнопке
#         callback_data=graf_not_mobile(dollar_data)
#     )
#
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[[button_mobile], [button_pc]]
#     )
#     # Отправляем сообщение с кнопкой
#     await message.answer("Нажмите на кнопку ниже, чтобы открыть график:", reply_markup=keyboard)


# @router.message(Command(commands=["chart"]))
# async def send_chart(message: Message):
#         # Создаем кнопку
#     dollarCod = 'R01235'
#     dollar = dinamic_course(dollarCod)
#     dollar_data = parse_xml_data(dollar)
#     await message.answer(graf(dollar_data))


# Этот хэндлер будет срабатывать на команду "/help"
@router.message(Command(commands=['help']))
async def process_help_command(message: Message):
    await message.answer(
        'Тут пока ничего нет'
    )



# Этот хэндлер будет срабатывать на любые ваши текстовые сообщения,
# кроме команд "/start" и "/help"
# @router.message()
# async def send_echo(message: Message):
#     await message.answer(message.message_id.)


# # Этот хэндлер будет срабатывать на тип контента "photo"
# @router.message(F.content_type == ContentType.PHOTO)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали фото')
#
#
# # Этот хэндлер будет срабатывать на тип контента "photo"
# @router.message(F.content_type == ContentType.VOICE)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали звук')
#
#
# # Этот хэндлер будет срабатывать на тип контента "photo"
# @router.message(F.content_type == ContentType.VIDEO)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали видео')

# Обработчик нажатий на инлайн-кнопки

