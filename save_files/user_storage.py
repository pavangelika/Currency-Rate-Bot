from aiogram.types import Message

from logging_settings import logger

user_data = {}  # Глобальный словарь для хранения данных пользователей


async def save_user_data(message: Message):
    """Сохраняет данные пользователя в словарь."""
    user_id = message.from_user.id
    user_data[user_id] = {
        "id": user_id,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username,
        "language_code": message.from_user.language_code,
        "is_bot": message.from_user.is_bot,
        "chat_id": message.chat.id
    }
    logger.info(f"Данные пользователя {user_id} сохранены: {user_data[user_id]}")


async def get_user_data(user_id):
    """Возвращает данные пользователя по user_id."""
    return user_data.get(user_id)


async def update_user_data(message, key, value):
    """Обновляет данные пользователя (или добавляет, если нет)."""
    # Если пользователь уже существует, просто обновляем его данные
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id].update({
            key: value  # Добавляем или обновляем ключ
        })
    else:
        # Если пользователя нет в словаре, создаем новый словарь
        user_data[user_id] = {
            "id": user_id,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "username": message.from_user.username,
            "language_code": message.from_user.language_code,
            "is_bot": message.from_user.is_bot,
            "chat_id": message.chat.id,
            "send_today": True  # Добавляем новый ключ
        }
    logger.info(f"Данные пользователя {user_id} обновлены: {user_data[user_id]}")


async def update_user_data_new(user_id, key, value):
    """Обновляет данные пользователя (или добавляет, если нет)."""
    # Если пользователь уже существует, просто обновляем его данные
    # try:
    if user_id in user_data:
        user_data[user_id].update({
            key: value  # Добавляем или обновляем ключ
        })
    logger.info(f"Данные пользователя {user_id} обновлены: {user_data[user_id]}")
# except Exception as e:
#     logger.error(e)
