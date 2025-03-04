import asyncio
from aiogram.types import Message


async def send_loading_message(message: Message):
    """
    Отправляет пользователю сообщение с анимацией "бегающих точек" (Подождите, рисуем графики...)
    """
    text = "Подождите, рисуем графики"
    msg = await message.answer(text)  # Отправляем начальное сообщение

    for _ in range(10):  # 10 секунд анимации
        for dots in [".", "..", "...", ""]:
            await asyncio.sleep(0.4)  # Ждем 1 секунду
            await msg.edit_text(f"{text}{dots}")  # Обновляем текст
