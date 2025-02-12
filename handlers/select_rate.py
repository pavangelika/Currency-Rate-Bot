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

# Константы
START_COMMAND = "start"
SELECT_RATE_COMMAND = "select_rate"
TOGGLE_PREFIX = "toggle_"
PAGE_PREFIX = "page_"
LAST_BTN = "last_btn"

# Состояния FSM
class UserState(StatesGroup):
    selected_buttons = State()  # Состояние для хранения выбранных кнопок
    selected_names = State()   # Состояние для хранения выбранных названий

def get_lexicon_data(command: str):
    """Получаем данные из LEXICON_GLOBAL по команде."""
    return next((item for item in LEXICON_GLOBAL if item["command"] == command), None)

@router.message(Command(commands=START_COMMAND))
async def process_start_handler(message: Message):
    """Обработчик команды /start."""
    start_data = next((item for item in LEXICON_GLOBAL if item["command"] == START_COMMAND), None)
    if start_data:
        keyboard = create_inline_kb(1, start_data["btn"])
        await message.answer(text=start_data["text"], reply_markup=keyboard)
        await save_user_data(message)
    else:
        await message.answer("Ошибка: данные для команды /start не найдены.")


@router.callback_query(lambda c: c.data == next((item["btn"] for item in LEXICON_GLOBAL if item["command"] == START_COMMAND), None))
# @router.callback_query(lambda c: c.data == get_lexicon_data(START_COMMAND)["btn"])
async def handle_start_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для команды /start."""
    try:
        # Инициализируем состояние
        await state.update_data(selected_buttons=set(), selected_names=set())

        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,
            selected_buttons = set()  # Начинаем с пустого набора
        )
        await callback.answer('')
        await callback.message.answer(
            "Выберите одну или несколько валют для получения актуальных данных по валютному курсу:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(e)

@router.message(Command(commands=SELECT_RATE_COMMAND))
async def select_rate_handler(message: Message, state: FSMContext):
    """Обработчик команды /select_rate."""
    try:
        # Инициализируем состояние
        await state.update_data(selected_buttons=set(), selected_names=set())

        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,
            selected_buttons=set() # Начинаем с пустого набора
        )
        await message.answer(
            "Выберите одну или несколько валют для получения актуальных данных по валютному курсу:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(e)

@router.callback_query(F.data.startswith(TOGGLE_PREFIX) | F.data.startswith(PAGE_PREFIX))
async def handle_toggle_and_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработчик переключения состояния кнопок и пагинации."""
    user_id = callback.from_user.id
    data = callback.data

    # Получаем текущее состояние
    user_data = await state.get_data()
    selected_buttons = user_data.get("selected_buttons", set())
    selected_names = user_data.get("selected_names", set())

    if data.startswith(TOGGLE_PREFIX):
        # Обработка переключения кнопки
        button = data[len(TOGGLE_PREFIX):-2]
        current_page = int(data.split("_")[3])

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

    elif data.startswith(PAGE_PREFIX):
        # Обработка пагинации
        current_page = int(data.split("_")[1])

    # Обновляем состояние
    await state.update_data(selected_buttons=selected_buttons, selected_names=selected_names)

    # Обновляем клавиатуру
    keyboard = keyboard_with_pagination_and_selection(
        width=1,
        **CURRENCY,
        last_btn="✅ Сохранить",
        page=current_page,
        selected_buttons=selected_buttons
    )
    try:
        await callback.answer('')
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logger.error(e)

@router.callback_query(F.data == LAST_BTN)
async def handle_last_btn(callback: CallbackQuery, state: FSMContext):
    """Обработчик последней кнопки."""
    user_id = callback.from_user.id
    select_rate_data = next((item for item in LEXICON_GLOBAL if item["command"] == SELECT_RATE_COMMAND), None)

    # Получаем текущее состояние
    user_data = await state.get_data()
    selected_buttons = user_data.get("selected_buttons", set())
    selected_names = user_data.get("selected_names", set())

    if not selected_buttons:
        await callback.answer('')
        await callback.message.answer(select_rate_data["notification_false"])
        await update_user_data_new(user_id, "selected_currency", False)
    else:
        logger.info(f'Пользователь {user_id} выбрал валюту {selected_names}')
        await callback.answer('')
        await callback.message.answer(f"{select_rate_data['notification_true']} \n  {'\n '.join(selected_names)}")
        await update_user_data_new(user_id, "selected_currency", selected_names)

