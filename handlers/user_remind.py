# user_handlers.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from handlers.notifications import schedule_interval_user
from logger.logging_settings import logger

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
