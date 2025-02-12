# select_rate.py
import json
import os

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from handlers.selected_currency import update_selected_currency, load_currency_data
from keyboards.buttons import create_inline_kb, keyboard_with_pagination_and_selection
from lexicon.lexicon import CURRENCY, \
    LEXICON_GLOBAL
from logger.logging_settings import logger
from save_files.user_storage import save_user_data, update_user_data_new, user_data
from service.CbRF import course_today

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
    selected_names = State()  # Состояние для хранения выбранных названий

def get_lexicon_data(command: str):
    """Получаем данные из LEXICON_GLOBAL по команде."""
    return next((item for item in LEXICON_GLOBAL if item["command"] == command), None)

@router.message(Command(commands=START_COMMAND))
async def process_start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    start_data = get_lexicon_data(START_COMMAND)
    if start_data:
        keyboard = create_inline_kb(1, start_data["btn"])
        await message.answer(text=start_data["text"], reply_markup=keyboard)
        await save_user_data(message)
    else:
        await message.answer("Ошибка: данные для команды /start не найдены.")



@router.callback_query(lambda c: c.data == get_lexicon_data(START_COMMAND)["btn"])
@router.callback_query(lambda c: c.data == get_lexicon_data("select_rate")["command"])
@router.message(Command(commands=[SELECT_RATE_COMMAND]))
async def handle_currency_selection(event: Message | CallbackQuery, state: FSMContext):
    """
    Обработчик для выбора валюты.
    Поддерживает как команду /select_rate, так и callback от кнопки "Выбор валюты".
    """
    try:
        # Инициализируем состояние
        await state.update_data(selected_buttons=set(), selected_names=set())

        # Создаем клавиатуру
        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,
            selected_buttons=set()  # Начинаем с пустого набора
        )

        # Отправляем сообщение с клавиатурой
        text = "Выберите одну или несколько валют для получения актуальных данных по валютному курсу:"
        if isinstance(event, CallbackQuery):
            await event.answer('')
            await event.message.answer(text, reply_markup=keyboard)
        else:  # isinstance(event, Message)
            await event.answer(text, reply_markup=keyboard)

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
    user_state = await state.get_data()
    selected_buttons = user_state.get("selected_buttons", set())
    selected_names = user_state.get("selected_names", set())

    if not selected_buttons:
        await callback.answer('')
        await callback.message.answer(select_rate_data["notification_false"])
        await update_user_data_new(user_id, "selected_currency", False)
    else:
        logger.info(f'Пользователь {user_id} выбрал валюту {selected_names}')
        await update_user_data_new(user_id, "selected_currency", selected_names)
        await callback.answer('')
        # await callback.message.answer(f"{select_rate_data['notification_true']}\n{chr(10).join(selected_names)}")

        # Создаем клавиатуру с кнопками из LEXICON_GLOBAL
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        # Добавляем кнопки
        buttons_to_add = [
            {"command": "select_rate", "btn": "Изменить валюту"},
            {"command": "today", "btn": "Курс ЦБ сегодня"},
            {"command": "everyday", "btn1": "Подписаться на ежедневную рассылку курса", "btn2": "Отписаться от ежедневной рассылки курса"},
            {"command": "exchange_rate", "btn1": "Подписаться на рассылку об изменении курса", "btn2": "Отписаться от рассылки об изменении курса"},
            {"command": "chart", "btn": "Посмотреть график"},
            {"command": "in_banks", "btn": "Курс валют в банках"},
        ]

        for button_data in buttons_to_add:
            item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
            if item:
                if item["command"] in ["everyday", "exchange_rate"]:
                    # Проверяем значения в user_state
                    user_data_item = user_state.get(item["command"], False)  # По умолчанию False (не подписан)
                    btn_key = "btn2" if user_data_item else "btn1"  # Выбираем кнопку в зависимости от состояния
                    btn_text = item.get(btn_key, button_data.get(btn_key))
                else:
                    btn_text = item.get("btn", button_data.get("btn"))

                if btn_text:
                    keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=item["command"])])

        # Отправляем сообщение с клавиатурой
                # await callback.message.answer("Выберите действие:", reply_markup=keyboard)

        await callback.message.answer(f"{select_rate_data['notification_true']}\n{chr(10).join(selected_names)}", reply_markup=keyboard)

        # Путь к файлу (можно использовать абсолютный путь)
        currency_file_path = os.path.join(os.path.dirname(__file__), '../save_files/currency_code.json')
        # Загрузка данных о валютах
        currency_data = load_currency_data(currency_file_path)
        update_selected_currency(user_data, user_id, currency_data)

        logger.info(f'user_data {user_data}')

@router.message(Command(commands=["today"]))
@router.callback_query(lambda c: c.data == get_lexicon_data("today")["command"])
async def send_today_handler(event: Message | CallbackQuery):
    """
    Обработчик для вывода курса выбранных валют пользователем для текущего дня.
    Поддерживает как команду /today, так и callback от кнопки "Курс ЦБ сегодня".
    """
    try:
        user_id = event.from_user.id
        selected_data = user_data[user_id]["selected_currency"]
        if isinstance(event, CallbackQuery):
            await event.answer('')
            await event.message.answer(course_today(selected_data))
        else:  # isinstance(event, Message)
            await event.answer(course_today(selected_data))
    except Exception as e:
        logger.error(e)

