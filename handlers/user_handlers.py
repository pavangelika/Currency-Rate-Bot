# user_handlers.py
import datetime
import os
import time

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import Message
from aiogram.types.web_app_info import WebAppInfo
from config_data import config
from states.state import UserState
from handlers.notifications import schedule_daily_greeting, schedule_interval_greeting, schedule_unsubscribe
from handlers.selected_currency import update_selected_currency, load_currency_data
from keyboards.buttons import create_inline_kb, keyboard_with_pagination_and_selection
from lexicon.lexicon import CURRENCY, \
    LEXICON_GLOBAL, LEXICON_IN_MESSAGE
from logger.logging_settings import logger
from service.CbRF import course_today, dinamic_course, parse_xml_data, categorize_currencies, graf_mobile, \
    graf_not_mobile

# Инициализируем роутер уровня модуля
router = Router()

# Глобальная переменная для планировщика
scheduler = None

def set_scheduler(sched):
    global scheduler
    scheduler = sched


users = {}  # Глобальный словарь пользователей

async def update_user_dict(state: FSMContext):
    global users
    data = await state.get_data()
    if isinstance(data, dict):  # Проверяем, что данные из state — словарь
        users.update(data)  # Обновляем глобальный словарь

def get_lexicon_data(command: str):
    """Получаем данные из LEXICON_GLOBAL по команде."""
    return next((item for item in LEXICON_GLOBAL if item["command"] == command), None)

@router.message(Command(commands="start"), StateFilter(default_state))
async def process_start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    start_data = get_lexicon_data("start")
    if start_data:
        keyboard = create_inline_kb(1, start_data["btn"])
        await message.answer(text=start_data["text"], reply_markup=keyboard)
        # Создаем словарь с данными пользователя
        user_data = {
            "id": message.from_user.id,
            "name": message.from_user.first_name,
            "username": message.from_user.username,
            "chat_id": message.chat.id,
            "bot": message.from_user.is_bot,
            "premium": message.from_user.is_premium,
            "date_start": message.date.strftime("%d/%m/%Y %H:%M"),
            "timezone": message.date.tzname() or "UTC",  # Если tzname() возвращает None, используем "UTC"
        }

        # Сохраняем данные в FSMContext
        await state.update_data({message.from_user.id: user_data})

        # Логируем данные пользователя
        await state.get_data()
        await update_user_dict(state)
        logger.info(f"User {message.from_user.id} has been added")
        logger.info(f"Users has been updated: {users}")
    else:
        await message.answer("Errors: no data found for the /start command")


@router.callback_query(F.data == get_lexicon_data("start")["btn"])
@router.callback_query(F.data == get_lexicon_data("select_rate")["command"])
@router.message(Command(commands=["select_rate"]))
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


@router.callback_query(F.data.startswith("toggle_") | F.data.startswith("page_"))
async def handle_toggle_and_pagination(callback: CallbackQuery, state: FSMContext):
    """Обработчик переключения состояния кнопок и пагинации."""
    data = callback.data

    # Получаем текущее состояние
    user_data = await state.get_data()
    selected_buttons = user_data.get("selected_buttons", set())
    selected_names = user_data.get("selected_names", set())

    if data.startswith("toggle_"):
        # Обработка переключения кнопки
        button = data[len("toggle_"):-2]
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

    elif data.startswith("page_"):
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


@router.callback_query(F.data == "last_btn")
async def handle_last_btn(callback: CallbackQuery, state: FSMContext):
    """Обработчик последней кнопки."""
    user_id = callback.from_user.id
    select_rate_data = next((item for item in LEXICON_GLOBAL if item["command"] == "select_rate"), None)

    # Получаем текущее состояние
    user_dict = await state.get_data()
    selected_buttons = user_dict.get("selected_buttons", set())
    selected_names = user_dict.get("selected_names", set())

    if not selected_buttons:
        await callback.answer('')
        await callback.message.answer(select_rate_data["notification_false"])
    else:
        logger.info(f'User {user_id} has been selected currency: {selected_names}')
        user_dict[user_id]["selected_currency"] = selected_names
        await callback.answer('')

        # Создаем клавиатуру с кнопками из LEXICON_GLOBAL
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for button_data in LEXICON_IN_MESSAGE:
            item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
            if item:
                if item["command"] in ["everyday"]:
                    # Проверяем значения в user_state
                    btn_key = "btn2" if user_dict[user_id].get(
                        "everyday") == True else "btn1"  # Выбираем кнопку в зависимости от состояния
                    btn_text = item.get(btn_key, button_data.get(btn_key))
                else:
                    btn_text = item.get("btn", button_data.get("btn"))

                if btn_text:
                    keyboard.inline_keyboard.append(
                        [InlineKeyboardButton(text=btn_text, callback_data=item["command"])])

        # Отправляем сообщение с клавиатурой
        await callback.message.answer(f"{select_rate_data['notification_true']}\n{chr(10).join(selected_names)}",
                                      reply_markup=keyboard)

        # Путь к файлу (можно использовать абсолютный путь)
        currency_file_path = os.path.join(os.path.dirname(__file__), '../save_files/currency_code.json')

        # Загрузка данных о валютах
        currency_data = load_currency_data(currency_file_path)
        update_selected_currency(user_dict, user_id, currency_data)  # Обновляем user_dict


# удалить лишние данные с ключами
    await state.clear()
    logger.info(f"Users has been updated: {users}")
    logger.info(f'User_dict{user_dict}')


@router.message(Command(commands=["today"]))
@router.callback_query(lambda c: c.data == get_lexicon_data("today")["command"])
async def send_today_handler(event: Message | CallbackQuery, state: FSMContext):
    """
    Обработчик для вывода курса выбранных валют пользователем для текущего дня.
    Поддерживает как команду /today, так и callback от кнопки "Курс ЦБ сегодня".
    """
    try:
        user_id = event.from_user.id
        # user_dict = await state.get_data()
        selected_data = users[user_id]["selected_currency"]
        today = datetime.date.today().strftime("%d/%m/%Y")  # Формат: ДД/ММ/ГГГГ
        if isinstance(event, CallbackQuery):
            await event.answer('')
            await event.message.answer(course_today(selected_data, today))
        else:  # isinstance(event, Message)
            await event.answer(course_today(selected_data, today))
        logger.info(f"User {user_id} has selected the '/today' command'")
    except Exception as e:
        logger.error(e)

@router.message(Command(commands=["everyday"]))
@router.callback_query(lambda c: c.data == get_lexicon_data("everyday")["command"])
async def send_today_schedule_handler(event: Message | CallbackQuery, state: FSMContext):
    # Получаем user_id в зависимости от типа event
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message  # Для callback_query используем message из event
    else:
        user_id = event.from_user.id
        message = event  # Для message используем сам event

    # user_dict = await state.get_data()

    # Проверяем, подписан ли пользователь на рассылку
    if users[user_id].get("everyday"):
        job_id = f"daily_greeting_{user_id}"
        text = get_lexicon_data("everyday")['notification_false']

        # Если задача существует, отменяем её
        if scheduler.get_job(job_id):
            try:
                schedule_unsubscribe(job_id, scheduler)
            except Exception as e:
                logger.error(e)
            finally:
                users[user_id]["everyday"] = False
                # await update_user_data_new(user_id, "everyday", False)
                await event.answer('')
                await message.answer(text)
                logger.info(f'Scheduler has been deleted {job_id}')
    else:
        # Если пользователь не подписан, подписываем его
        try:
            users[user_id]["everyday"] = True
            # await update_user_data_new(user_id, "everyday", True)
            selected_data = users[user_id]["selected_currency"]
            today = datetime.date.today().strftime("%d/%m/%Y")
            if isinstance(event, CallbackQuery):
                await event.answer('')
            schedule_daily_greeting(user_id, scheduler, selected_data, today)
            logger.info(f"User {user_id} has subscribed to the daily newsletter")
        except Exception as e:
            logger.error(f"Error in send_today_schedule_handler: {e}")
        else:
            await message.answer(text=get_lexicon_data("everyday")['notification_true'])
    logger.info(f"Users has been updated: {users}")


@router.message(Command(commands=["chart"]))
@router.callback_query(F.data == get_lexicon_data("chart")["command"])
async def send_html_graph(event: Message | CallbackQuery, state: FSMContext):
    # Получаем user_id в зависимости от типа event
    if isinstance(event, CallbackQuery):
        await event.answer('')
        message = event.message  # Для callback_query используем message из event
    else:
        message = event  # Для message используем сам event

    await message.answer("Введите диапазон лет (например, 2022-2025 или 2025):")
    await state.set_state(UserState.years)


@router.message(UserState.years)
async def end_year(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_dict = await state.get_data()
    user_input = message.text.strip()  # Убираем лишние пробелы

    # Если пользователь ввёл команду (начинается с "/"), очищаем состояние и выходим
    # if user_input.startswith("/"):
    #     await state.clear()
    #     logger.info(f'User {user_id} input command {user_input}')
    #     logger.info(f"users {users}")
    #     logger.info(f'user_dict {user_dict}')
    #     return

    # Проверяем, это диапазон лет или один год
    if '-' in user_input:
        years = user_input.split('-')
        if len(years) != 2:
            await message.answer("Некорректный ввод. Введите диапазон лет в формате '2022-2025'.")
            return
        try:
            start, end = map(int, years)
        except ValueError:
            await message.answer("Некорректный ввод. Используйте числа, например '2022-2025'.")
            return
    else:
        try:
            start = end = int(user_input)
        except ValueError:
            await message.answer("Некорректный ввод. Введите год в формате '2025'.")
            return

    # Проверяем, что начальный год <= конечного
    if start > end:
        await message.answer("Начальный год должен быть меньше или равен конечному году.")
        return

    # Сохраняем данные в state
    await state.update_data(start=start, end=end)

    # Проверяем, есть ли у пользователя выбранные валюты
    if user_id not in users or "selected_currency" not in users[user_id]:
        await message.answer("Ошибка: у вас нет выбранных валют.")
        return

    selected_data = users[user_id]["selected_currency"]
    selected_data_list = []
    for sd in selected_data:
        result = dinamic_course(sd['id'])
        name = sd['charCode']
        result_data = parse_xml_data(result)
        selected_data_list.append({"name": name, "value": result_data})

    group_for_graf = categorize_currencies(selected_data_list)
    index = graf_mobile(group_for_graf, start, end)
    logger.info(f"File index.html updated: {os.path.exists(index)}")

    # Создаем кнопки
    button_mobile = InlineKeyboardButton(
        text="График на телефоне",
        web_app=WebAppInfo(url=f"{config.GITHUB_PAGES}?v={int(time.time())}")
    )
    button_pc = InlineKeyboardButton(
        text="График на ПК",
        callback_data="pc_graph"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button_mobile], [button_pc]]
    )

    # Отправляем сообщение
    await message.answer("Нажмите на кнопку ниже, чтобы открыть график:", reply_markup=keyboard)



@router.callback_query(F.data == "pc_graph")
async def btn_graf_not_mobile(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    data = await state.get_data()
    # user_dict = await state.get_data()
    start = data.get("start")
    end = data.get("end")

    if start is None or end is None:
        await callback.message.answer("Введите еще раз диапазон лет (например, 2022-2025 или 2025):")
        await state.set_state(UserState.years)
        return

    user_id = callback.from_user.id
    selected_data = users[user_id]["selected_currency"]

    selected_data_list = []
    for sd in selected_data:
        result = dinamic_course(sd['id'])
        name = sd['charCode']
        result_data = parse_xml_data(result)
        selected_data_list.append({"name": name, "value": result_data})

    group_for_graf = categorize_currencies(selected_data_list)
    graf_not_mobile(group_for_graf, start, end)
    await state.clear()


@router.message(Command(commands=["menu"]) or F.data == "/menu" or F.data == "menu")
async def menu(message: Message, state: FSMContext):
    user_id = message.from_user.id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for button_data in LEXICON_IN_MESSAGE:
        item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
        if item:
            if item["command"] in ["everyday"]:
                # Проверяем значения в user_state
                btn_key = "btn2" if users[user_id].get(
                    "everyday") == True else "btn1"  # Выбираем кнопку в зависимости от состояния
                btn_text = item.get(btn_key, button_data.get(btn_key))
            else:
                btn_text = item.get("btn", button_data.get("btn"))

            if btn_text:
                keyboard.inline_keyboard.append(
                    [InlineKeyboardButton(text=btn_text, callback_data=item["command"])])

    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(F.data == "in_banks")
async def in_banks(callback: CallbackQuery, state: FSMContext):
    main = InlineKeyboardMarkup(inline_keyboard=[  # Заместо keyboard, теперь inline_keyboard
        [InlineKeyboardButton(text='Курс валют в банках', url='https://1000bankov.ru/kurs/')],
        # [InlineKeyboardButton(text='Следить за курсом продажи', callback_data='look_for_sale')],
        # [InlineKeyboardButton(text='Следить за курсом покупки', callback_data='look_for_buy')]
    ])

    await callback.answer("")

    await callback.message.answer('️Сравните курсы валют в вашем городе за секунды! \n'                                  
                                  'Купите валюту выгодно! \n'
                                  'Продайте валюту по лучшей цене! \n', reply_markup=main)


    # await callback.message.answer("Для показа курс валют в банках вашего города требуется узнать ваш город:", reply_markup=keyboard)


# Этот хэндлер будет срабатывать на любые ваши текстовые сообщения,
# кроме команд "/start" и "/help"
# @router.message()
# async def send_echo(message: Message):
#     await message.answer("Я не понимаю, воспользуйтесь меню команд")

# @router.message(F.content_type == ContentType.PHOTO)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали фото')
#
# @router.message(F.content_type == ContentType.VOICE)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали звук')
#
# @router.message(F.content_type == ContentType.VIDEO)
# async def process_send_photo(message: Message):
#     await message.reply(text='Вы прислали видео')


