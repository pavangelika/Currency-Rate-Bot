# user_handlers.py

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config_data import config

from handlers.notifications import schedule_daily_greeting, schedule_interval_greeting, schedule_unsubscribe, \
    schedule_interval_user
from keyboards.buttons import create_inline_kb
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

# Глобальная переменная для планировщика
scheduler = None


def set_scheduler(sched):
    global scheduler
    scheduler = sched


# Этот хэндлер будет срабатывать на команду "/start"
@router.message(Command(commands=["start"]))
async def process_start_handler(message: Message):
    # keyboard = create_inline_kb(1, **LEXICON_BTN)
    keyboard = create_inline_kb(1, 'start_1')
    await message.answer(
        text=LEXICON_TEXT['start'],
        reply_markup=keyboard)
    await save_user_data(message)


@router.message(Command(commands=["today"]))
async def send_today_handler(message: Message):
    try:
        await message.answer(course_today())
    except Exception as e:
        logger.error(e)


@router.message(Command(commands=["everyday"]))
async def send_today_schedule_handler(message: Message):
    user_id = message.from_user.id
    if user_id in user_data:
        try:
            await update_user_data(message, "everyday_true", True)  # "send_today": True
            schedule_daily_greeting(user_id, scheduler)
        except Exception as e:
            logger.error(f"Error in send_today_schedule_handler: {e}")
        else:
            await message.answer(
                text=LEXICON_NOTIFICATION_SEND['everyday_true'])


@router.message(Command(commands=["exchange_rate"]))
async def send_today_schedule_handler(message: Message):
    user_id = message.from_user.id
    if user_data[user_id].get("exchange_rate") == True:
        job_id = f"interval_greeting_{user_id}"
        text = LEXICON_NOTIFICATION_SEND['exchange_rate_false']
        if scheduler.get_job(job_id):
            try:
                schedule_unsubscribe(job_id, scheduler)
            except Exception as e:
                logger.error(e)
            finally:
                await update_user_data(message, "exchange_rate", False)
                await message.answer(text)
                logger.info(f'{user_id} отписан от рассылки {job_id}')
    else:
        try:
            await update_user_data(message, "exchange_rate", True)
            schedule_interval_greeting(user_id, scheduler)
        except Exception as e:
            logger.error(f"Error in send_today_schedule_handler: {e}")
        else:
            await message.answer(
                text=LEXICON_NOTIFICATION_SEND['exchange_rate_true'])


@router.message(Command(commands=["chart"]))
async def send_html_graph(message: Message):
    dollarCod = 'R01235'
    dollar = dinamic_course(dollarCod)
    dollar_data = parse_xml_data(dollar)
    # Генерация графика
    file_path = graf_mobile(dollar_data)

    # Создаем кнопку для Web App
    button_mobile = InlineKeyboardButton(
        text="График на телефоне",  # Текст на кнопке
        web_app=types.WebAppInfo(url=config.GITHUB_PAGES)  # URL к размещенному HTML
    )
    button_pc = InlineKeyboardButton(
        text="График на ПК",  # Текст на кнопке
        callback_data=graf_not_mobile(dollar_data)
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button_mobile], [button_pc]]
    )
    # Отправляем сообщение с кнопкой
    await message.answer("Нажмите на кнопку ниже, чтобы открыть график:", reply_markup=keyboard)


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


@router.message(Command(commands=['user_remind']))
async def process_user_remind(message: Message, state: FSMContext):
    """Шаг 1: Запрос текста напоминания."""
    logger.info(f"Пользователь {message.from_user.id} вызвал /user_remind")

    await message.answer("📌 Введите текст напоминания:")
    await state.set_state(ReminderState.waiting_for_text)

@router.message(ReminderState.waiting_for_text)
async def process_reminder_text(message: Message, state: FSMContext):
    """Шаг 2: Сохраняем текст и запрашиваем время."""
    reminder_text = message.text
    logger.info(f"Пользователь {message.from_user.id} ввёл текст: {reminder_text}")

    await state.update_data(reminder_text=reminder_text)
    await message.answer("⏳ Через сколько минут отправить напоминание?")
    await state.set_state(ReminderState.waiting_for_minutes)

@router.message(ReminderState.waiting_for_minutes)
async def process_reminder_time(message: Message, state: FSMContext):
    """Шаг 3: Сохраняем время и создаём задачу."""
    if not message.text.isdigit():
        await message.answer("❌ Введите число минут цифрами!")
        return

    minutes = int(message.text)
    min_word = get_minutes_word(minutes)  # Получаем правильное склонение

    data = await state.get_data()
    reminder_text = data.get("reminder_text", "Напоминание")

    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} установил напоминание '{reminder_text}' через {minutes} {min_word}.")

    # Добавляем задачу в планировщик
    schedule_interval_user(user_id, reminder_text, minutes, scheduler)

    await message.answer(f"✅ Напоминание '{reminder_text}' запланировано через {minutes} {min_word}!")
    await state.clear()

def get_minutes_word(minutes: int) -> str:
    """Определяет правильное склонение слова 'минута'."""
    if 11 <= minutes % 100 <= 14:
        return "минут"

    last_digit = minutes % 10
    if last_digit == 1:
        return "минуту"
    elif last_digit in [2, 3, 4]:
        return "минуты"
    if minutes == 11 or 12 <= minutes <= 20:
        return "минут"



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
@router.callback_query(lambda c: c.data == 'start_1')
async def process_start_1_button(callback: CallbackQuery):
    await callback.answer(cache_time=60)  # Ответ пользователю
    try:
        # Выполняем действие для start_1 кнопки
        result = course_today()  # Пример: вызываем функцию из service.CbRF

        # Форматируем результат для отображения
        output_text = result

        await callback.message.edit_text(  # Изменяем текст сообщения
            text=output_text,
            reply_markup=None  # Удаляем клавиатуру после нажатия
        )
    except Exception as e:
        await callback.message.edit_text(  # Обработка ошибок
            text=f"Ошибка: {e}"
        )
