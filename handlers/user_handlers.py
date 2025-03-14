# user_handlers.py
import asyncio
import datetime
import json
import os

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message
from aiogram.types.web_app_info import WebAppInfo

from database.db import create_db_pool, create_table, get_everyday, get_selected_currency, \
    format_currency_from_db, update_user_everyday, add_user_to_db, update_user_currency, update_user_jobs, get_user_jobs
from github.check_url import check_file_available
from github.downloading import send_loading_message
from handlers.notifications import schedule_daily_greeting, schedule_unsubscribe, schedule_interval_greeting
from handlers.selected_currency import update_selected_currency, load_currency_data
from keyboards.buttons import create_inline_kb, keyboard_with_pagination_and_selection
from lexicon.lexicon import CURRENCY, \
    LEXICON_GLOBAL, LEXICON_IN_MESSAGE
from logger.logging_settings import logger
from parsing.bank import get_city_link
from service.CbRF import course_today, dinamic_course, parse_xml_data, categorize_currencies, graf_mobile
from service.geocoding import get_city_by_coordinates
from states.state import UserState
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Инициализируем роутер уровня модуля
router = Router()

scheduler: AsyncIOScheduler = None  # Явно указываем тип
def set_scheduler(sched:AsyncIOScheduler):
    global scheduler
    scheduler = sched


# Инициализируем пул подключений к базе данных
db_pool = None


async def init_db():
    global db_pool
    db_pool = await create_db_pool()
    await create_table(db_pool)


def get_lexicon_data(command: str):
    """Получаем данные из LEXICON_GLOBAL по команде."""
    return next((item for item in LEXICON_GLOBAL if item["command"] == command), None)


@router.message(Command(commands="start"), StateFilter(default_state))
async def process_start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    start_data = get_lexicon_data("start")
    if start_data:
        keyboard = create_inline_kb(1, start_data["btn"])
        await message.answer(text=start_data["text"], reply_markup=keyboard)
        # Создаем словарь с данными пользователя
        user_data = {
            "user_id": message.from_user.id,
            "name": message.from_user.first_name,
            "username": message.from_user.username,
            "chat_id": message.chat.id,
            "is_bot": message.from_user.is_bot,
            "date_start": message.date.strftime("%d/%m/%Y %H:%M"),
            "timezone": message.date.tzname() or "UTC",  # Если tzname() возвращает None, используем "UTC"
        }

        # Сохраняем данные в FSMContext
        state = await state.update_data({message.from_user.id: user_data})
        logger.info(f"state_start: {state}")

        # Добавляем пользователя в базу данных
        try:
            await add_user_to_db(db_pool, user_data)
        except Exception as e:
            logger.error(e)
    else:
        await message.answer("Errors: no data found for the /start command")

@router.message(Command(commands=["currency"]))
async def my_currency(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    currency_file_path = os.path.join(os.path.dirname(__file__), '../save_files/currency_code.json')
    currency_data = load_currency_data(currency_file_path)

    # Получаем данные из базы данных
    db_result = await get_selected_currency(db_pool, user_id)
    # logger.info(f"db_result: {db_result}")

    # Форматируем результат
    formatted_result = await format_currency_from_db(db_result)
    # logger.info(f"formatted_result: {formatted_result}")

    # Проверка, что formatted_result является строкой
    if not formatted_result:
        logger.error("Formatted result is empty or None!")
        formatted_result = "Не удалось получить данные о валютах."

    # Создаем клавиатуру с кнопками из LEXICON_GLOBAL
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for button_data in LEXICON_IN_MESSAGE:
        item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
        if item:
            if item["command"] in ["everyday"]:
                everyday = await get_everyday(db_pool, user_id)
                btn_key = "btn2" if everyday == True else "btn1"  # Выбираем кнопку в зависимости от состояния
                btn_text = item.get(btn_key, button_data.get(btn_key))
            else:
                btn_text = item.get("btn", button_data.get("btn"))

            if btn_text:
                keyboard.inline_keyboard.append(
                    [InlineKeyboardButton(text=btn_text, callback_data=item["command"])])

    select_rate_data = next((item for item in LEXICON_GLOBAL if item["command"] == "select_rate"), None)

    # Обрабатываем список валют, добавляя их на новую строку
    formatted_result = "\n".join(formatted_result.split(", "))  # Разбиваем на строки по запятой и пробелу

    # Отправляем сообщение с клавиатурой
    await message.answer(f"{select_rate_data['notification_true']}\n{formatted_result}", reply_markup=keyboard)

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
        await state.clear()
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
    state = await state.get_data()
    selected_buttons = state.get("selected_buttons", set())
    selected_names = state.get("selected_names", set())

    if not selected_buttons:
        await callback.answer('')
        await callback.message.answer(select_rate_data["notification_false"])
    else:
        logger.info(f'User {user_id} has been selected currency: {selected_names}')
        await update_user_currency(db_pool, user_id, selected_names)
        await callback.answer('')

        # Создаем клавиатуру с кнопками из LEXICON_GLOBAL
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for button_data in LEXICON_IN_MESSAGE:
            item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
            if item:
                if item["command"] in ["everyday"]:
                    everyday = await get_everyday(db_pool, user_id)
                    btn_key = "btn2" if everyday == True else "btn1"  # Выбираем кнопку в зависимости от состояния
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
        # logger.info(f"state {state}")

        db_result = await get_selected_currency(db_pool, user_id)
        # logger.info(f"db_result {db_result}")
        updated_currencies = update_selected_currency(db_result, user_id, currency_data)  # Обновляем user_dict

        # Добавляем пользователя в базу данных
        try:
            await update_user_currency(db_pool, user_id, selected_currency=updated_currencies)
            db_result = await get_selected_currency(db_pool, user_id)
            formatted_result = await format_currency_from_db(db_result)
        except Exception as e:
            logger.error(e)


@router.message(Command(commands=["today"]))
@router.callback_query(lambda c: c.data == get_lexicon_data("today")["command"])
async def send_today_handler(event: Message | CallbackQuery, state: FSMContext):
    """
    Обработчик для вывода курса выбранных валют пользователем для текущего дня.
    Поддерживает как команду /today, так и callback от кнопки "Курс ЦБ сегодня".
    """
    try:
        await state.clear()
        user_id = event.from_user.id
        selected_data = await get_selected_currency(db_pool, user_id)
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
async def everyday_handlers(message: Message, state: FSMContext):
    # Создаем клавиатуру с кнопками из LEXICON_GLOBAL
    await state.clear()
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for button_data in LEXICON_IN_MESSAGE:
        item = next((item for item in LEXICON_GLOBAL if item["command"] == button_data["command"]), None)
        if item:
            if item["command"] in ["everyday"]:
                everyday = await get_everyday(db_pool, user_id)
                btn_key = "btn2" if everyday else "btn1"  # Выбираем кнопку в зависимости от состояния
                btn_answer = "Вы подписаны на ежедневную рассылку курса валют" if everyday else "Вы отписаны от ежедневной рассылки курса валют"
                btn_text = item.get(btn_key, button_data.get(btn_key))

                # Создаем кнопку и добавляем ее в клавиатуру
                button = InlineKeyboardButton(text=btn_text, callback_data=item["command"])
                keyboard.inline_keyboard.append([button])  # Добавляем кнопку в клавиатуру

                # Отправляем сообщение с клавиатурой
                await message.answer(text=btn_answer, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == get_lexicon_data("everyday")["command"])
async def send_today_schedule_handler(event: CallbackQuery, state: FSMContext):
    # Получаем user_id и сообщение из callback_query
    user_id = event.from_user.id
    message = event.message  # Используем message из callback_query

    # Проверяем, подписан ли пользователь на рассылку
    subscription = await get_everyday(db_pool, user_id)

    if subscription:
        text = get_lexicon_data("everyday")['notification_false']
        # Получаем список задач пользователя
        jobs = await get_user_jobs(db_pool, user_id)

        # Отменяем каждую задачу из списка
        for job_id in jobs:
            if scheduler.get_job(job_id):
                try:
                    scheduler.remove_job(job_id)  # Удаляем задачу из планировщика
                    logger.info(f"Jobs from DB == {jobs}")
                except Exception as e:
                    logger.error(e)
            else:
                logger.info(f'Scheduler has not found task "{job_id}"')

        # Обновляем статус подписки на False
        await update_user_everyday(db_pool, user_id, False)
        await update_user_jobs(db_pool, user_id, job_id=None)  # Очищаем список задач

        # Подтверждаем обработку callback_query
        await event.answer()

        # Отправляем сообщение об отключении рассылки
        await message.answer(text=get_lexicon_data("everyday")['notification_false'])

    else:
        # Если пользователь не подписан, подписываем его
        try:
            await update_user_everyday(db_pool, user_id, True)
            subscription = await get_everyday(db_pool, user_id)

            # Получаем выбранные валюты и текущую дату
            selected_data = await get_selected_currency(db_pool, user_id)
            today = datetime.date.today().strftime("%d/%m/%Y")
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d/%m/%Y")

            # Подтверждаем обработку callback_query
            await event.answer()

            # Запланируем рассылку
            job_id = schedule_interval_greeting(user_id, scheduler, selected_data, today, db_pool)
            await update_user_jobs(db_pool, user_id, job_id)  # Добавляем job_id в список задач
            jobs = await get_user_jobs(db_pool, user_id)
            logger.info(f"Jobs from DB == {jobs}")
            logger.info(f"User {user_id} jobs == {scheduler.get_job(job_id)}")

            # Отправляем сообщение о включении рассылки
            await message.answer(text=get_lexicon_data("everyday")['notification_true'])

        except Exception as e:
            logger.error(f"Error in send_today_schedule_handler: {e}")


@router.message(F.content_type.in_({ContentType.PHOTO, ContentType.DOCUMENT, ContentType.VOICE, ContentType.VIDEO}))
async def process_sorry(message: Message):
    if message.photo:
        await message.reply(text='Извини, 🥺 я не умею обрабатывать фото.')
    elif message.document:
        await message.reply(text='Извини, 🥺 я не умею обрабатывать документы.')
    elif message.voice:
        await message.reply(text='Извини, 🥺 я не умею слушать звуковые сообщения.')
    elif message.video:
        await message.reply(text='Извини, 🥺 я не умею обрабатывать видео.')


@router.message(Command(commands=["chart"]))
@router.callback_query(F.data.in_([get_lexicon_data("chart")["command"], "change_years"]))
async def request_year(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    # Получаем user_id в зависимости от типа event
    if isinstance(event, CallbackQuery):
        await event.answer('')
        message = event.message  # Для callback_query используем message из event
    else:
        message = event  # Для message используем сам event

    await message.answer("Введите диапазон лет (например, 2022-2025 или 2025):")
    await state.set_state(UserState.years)


@router.callback_query(F.data == "in_banks")
@router.message(Command(commands=["in_banks"]))
async def in_banks(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer('')
        message = event.message  # Для callback_query используем message из event
    else:
        message = event  # Для message используем сам event
    await message.answer(
        "Для показа курса валют отправьте вашу локацию в этот чат")
    await state.set_state(UserState.location)


@router.message(UserState.location)
async def get_link_city(message: Message, state: FSMContext):
    # Проверяем, есть ли текст в сообщении
    if message.text and (message.text.startswith("/") or message.text.lower() in ["отмена", "cancel"]):
        await state.clear()
        return

    # Проверяем, есть ли геолокация в сообщении
    if not message.location:
        await message.answer("Пожалуйста, отправьте вашу геолокацию.")
        return

    user_id = message.from_user.id
    latitude = message.location.latitude
    longitude = message.location.longitude
    location = await get_city_by_coordinates(latitude, longitude)
    city = location.get("city", "Неизвестный город")

    # Формируем словарь с местоположением
    location_data = {
        "latitude": latitude,
        "longitude": longitude,
        "city": location.get("city", "Неизвестный город"),
        "region": location.get("principalSubdivision", "Неизвестный регион"),
        "regionCode": location.get("principalSubdivisionCode", "Неизвестный код региона"),
        "countryName": location.get("countryName", "Неизвестная страна"),
        "countryCode": location.get("countryCode", "Неизвестный код страны"),
        "continent": location.get("continent", "Неизвестный континент"),
        "continentCode": location.get("continentCode", "Неизвестный код континента")
    }

    # Сохраняем в PostgreSQL
    async with db_pool.acquire() as connection:
        await connection.execute(
            "UPDATE users SET location = $1 WHERE user_id = $2",
            json.dumps(location_data, ensure_ascii=False),  # Преобразуем в JSON-строку
            user_id
        )

    logger.info(f"Локация пользователя {user_id} обновлена: {location_data}")

    if city != "Неизвестный город":
        city_link = get_city_link(city)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=f'Курс валют в банках города {city}', url=city_link)]
                             ])
        await message.answer("Перейдите по ссылке и сравнивайте курсы валют в вашем городе за секунды ",
                             reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='Курс валют в банках', url='https://1000bankov.ru/kurs/')]
                             ])
        await message.answer("Перейдите по ссылке и сравнивайте курсы валют в вашем городе за секунды ",
                             reply_markup=keyboard)


@router.message(UserState.years)
async def process_year(message: Message, state: FSMContext):
    """Обрабатывает введенный диапазон лет и выводит клавиатуру."""
    user_id = message.from_user.id
    user_dict = await state.get_data()
    user_input = message.text.strip()
    current_year = datetime.date.today().year  # Получаем текущий год

    # Если пользователь ввел команду (начинается с "/"), очищаем состояние и выходим
    if user_input.startswith("/") or user_input in ["отмена", "cancel"]:
        await state.clear()
        return

    # Определяем, введен один год или диапазон
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

    # Проверяем корректность диапазона лет
    if start > end:
        await message.answer("Ошибка. Начальный год не может быть больше конечного.")
        return

    if end > current_year:
        await message.answer(f"Ошибка. Конечный год не может быть больше {current_year}.")
        return

    if start<2001:
        await message.answer(f"Ошибка. Данные до 2001 года не предоставляются.")
        return

    # Сохраняем данные в state
    await state.update_data(start=start, end=end)

    # Генерация данных для графика
    selected_data = await get_selected_currency(db_pool, user_id)

    if selected_data is None:
        await message.answer("Ошибка: у вас нет выбранных валют.")
        return

    selected_data_list = []
    for sd in selected_data:
        result = dinamic_course(sd['id'])
        name = sd['charCode']
        result_data = parse_xml_data(result)
        selected_data_list.append({"name": name, "value": result_data})

    group_for_graf = categorize_currencies(selected_data_list)
    url = graf_mobile(group_for_graf, start, end)
    logger.info(f'Сформирован график {url}')

    # Отправляем анимационное сообщение пользователю
    loading_task = asyncio.create_task(send_loading_message(message))

    # Проверяем доступность файла
    if await check_file_available(url):
        await loading_task  # Дожидаемся окончания анимации

        # Отправляем кнопки после загрузки
        button_mobile = InlineKeyboardButton(
            text="График на телефоне",
            web_app=WebAppInfo(url=url)
        )

        button_pc = InlineKeyboardButton(
            text="График на ПК",
            url=url
        )

        button_change_years = InlineKeyboardButton(
            text="Выбрать другой диапозон лет",
            callback_data="change_years"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [button_mobile],
            [button_pc],
            [button_change_years]
        ])

        await message.answer("График готов! Нажмите на кнопку ниже:", reply_markup=keyboard)
        logger.info(f"График {url} показан пользователю {user_id}")
    else:
        await loading_task  # Дожидаемся окончания анимации
        await message.answer("График пока недоступен. Попробуйте позже.")
        logger.info(f"График {url} недоступен для пользователя {user_id}")
    # Очищаем состояние после успешного выполнения
    await state.clear()
