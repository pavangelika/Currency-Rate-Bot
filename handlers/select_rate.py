# select_rate.py
from typing import re

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config_data import config

from handlers.notifications import schedule_daily_greeting, schedule_interval_greeting, schedule_unsubscribe, \
    schedule_interval_user
from keyboards.buttons import create_inline_kb, keyboard_with_pagination_and_selection
from lexicon.lexicon import LEXICON_TEXT, LEXICON_NOTIFICATION_SEND, create_buttons_from_json_file, CURRENCY
from logging_settings import logger
from save_files.user_storage import save_user_data, update_user_data, user_data
from service.CbRF import course_today, dinamic_course, parse_xml_data, graf_mobile, graf_not_mobile

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State



class ReminderState(StatesGroup):
    waiting_for_minutes = State()
    waiting_for_text = State()


# Инициализируем роутер уровня модуля
router = Router()

@router.message(Command(commands=["select_rate"]))
async def select_rate_handler(message: Message):
    try:
        keyboard = keyboard_with_pagination_and_selection(
            width=1,
            **CURRENCY,
            last_btn="✅ Сохранить",
            page=1,  # Можно передать текущую страницу
        )
        await message.answer("Выберите курс валют:", reply_markup=keyboard)
    except Exception as e:
        logger.error(e)



# Храним состояние выбранных кнопок
selected_buttons = set()
@router.callback_query(F.data.startswith("toggle_"))
async def handle_toggle(callback: CallbackQuery):
    # Извлекаем callback_data
    button = callback.data[7:]
    logger.info(button)

    for c in CURRENCY:
        if c == button:
            select_name = CURRENCY[c]
            logger.info(select_name)


    # # Переключаем состояние кнопки
    # if button in selected_buttons:
    #     selected_buttons.remove(button)
    # else:
    #     selected_buttons.add(button)
    #
    # logger.info(selected_buttons)

    # # Обновляем клавиатуру
    # new_keyboard = keyboard_with_pagination_and_selection(
    #     width=1,
    #     **CURRENCY,
    #     last_btn="✅ Сохранить",
    #     page=1,  # Можно передать текущую страницу
    #     selected_buttons=selected_buttons
    # )
    # await callback.message.edit_reply_markup(reply_markup=new_keyboard)

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
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

@router.callback_query(F.data == "last_btn")
async def handle_last_btn(callback: CallbackQuery):
    # Возвращаем список выбранных кнопок
    await callback.answer(f"Вы выбрали: {', '.join(selected_buttons)}", show_alert=True)