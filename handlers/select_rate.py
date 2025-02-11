# select_rate.py
import json
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config_data import config

from handlers.notifications import schedule_daily_greeting, schedule_interval_greeting, schedule_unsubscribe, \
    schedule_interval_user
from keyboards.buttons import create_inline_kb, keyboard_with_pagination_and_selection
from lexicon.lexicon import LEXICON_NOTIFICATION_SEND, create_buttons_from_json_file, CURRENCY, \
    LEXICON_GLOBAL
from logging_settings import logger
from save_files.user_storage import save_user_data, update_user_data, user_data, update_user_data_new
from service.CbRF import course_today, dinamic_course, parse_xml_data, graf_mobile, graf_not_mobile

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


# Инициализируем роутер уровня модуля
router = Router()

# Храним состояние выбранных кнопок
selected_buttons = set()
selected_names = set()




# Этот хэндлер будет срабатывать на команду "/start"
@router.message(Command(commands=["start"]))
async def process_start_handler(message: Message):
    # Ищем в LEXICON_GLOBAL нужный словарь по "command": "/start"
    start_data = next((item for item in LEXICON_GLOBAL if item["command"] == "/start"), None)

    if start_data:
        keyboard = create_inline_kb(1, start_data["btn"])  # Подставляем "btn" из словаря
        await message.answer(
            text=start_data["text"],  # Подставляем "text" из словаря
            reply_markup=keyboard
        )
        await save_user_data(message)
    else:
        await message.answer("Ошибка: данные для команды /start не найдены.")



@router.callback_query(lambda c: c.data == next((item["btn"] for item in LEXICON_GLOBAL if item["command"] == "/start"), None))
async def handle_toggle(callback: CallbackQuery):
    try:
        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,  # Можно передать текущую страницу
        )
        await callback.answer('')
        await callback.message.answer("Выберите одну или несколько валют для получения актуальных данных по валютному курсу:",
                             reply_markup=keyboard)
    except Exception as e:
        logger.error(e)


@router.message(Command(commands=["select_rate"]))
async def select_rate_handler(message: Message):
    try:
        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,  # Можно передать текущую страницу
        )
        await message.answer("Выберите одну или несколько валют для получения актуальных данных по валютному курсу:", reply_markup=keyboard)
    except Exception as e:
        logger.error(e)




@router.callback_query(F.data.startswith("toggle_"))
async def handle_toggle(callback: CallbackQuery):
    # Извлекаем callback_data
    user_id = callback.from_user.id
    button = callback.data[7:-2]
    current_page = int(callback.data.split("_")[3])

    # # Переключаем состояние кнопки
    if button in selected_buttons:
        selected_buttons.remove(button)
    else:
        selected_buttons.add(button)

    for c in CURRENCY:
        if c == button:
            select_name = CURRENCY[c]
            if select_name in selected_names:
                selected_names.remove(select_name)
            else:
                selected_names.add(select_name)



    # Обновляем клавиатуру
    new_keyboard = keyboard_with_pagination_and_selection(
        width=1,
        **CURRENCY,        last_btn="✅ Сохранить",
        page=current_page,  # Можно передать текущую страницу
        selected_buttons=selected_buttons
    )
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

@router.callback_query(F.data.startswith("page_"))
async def handle_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])  # Извлекаем номер страницы
    # Создаем новую клавиатуру с обновленной страницей
    new_keyboard = keyboard_with_pagination_and_selection(
        width=1,
        **CURRENCY,
        last_btn="✅ Сохранить",
        page=page,
        selected_buttons=selected_buttons
    )
    # Редактируем сообщение с новой клавиатурой
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

@router.callback_query(F.data == "last_btn")
async def handle_last_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    select_rate_data = next((item for item in LEXICON_GLOBAL if item["command"] == "/select_rate"), None)
    # Возвращаем список выбранных кнопок
    if len(selected_buttons) == 0:
        # await callback.answer(select_rate_data["notification_false"], show_alert=True)
        await callback.answer('')
        await callback.message.answer(select_rate_data["notification_false"])
        await update_user_data_new(user_id, "selected_currency", False)
    else:
        logger.info(f'Пользователь {user_id} выбрал валюту {selected_names}')
        # await callback.answer(f"{select_rate_data["notification_true"]} \n  {'\n '.join(selected_names)}", show_alert=True)
        await callback.answer('')
        await callback.message.answer(f"{select_rate_data["notification_true"]} \n  {'\n '.join(selected_names)}")
        await update_user_data_new(user_id, "selected_currency", selected_names)

