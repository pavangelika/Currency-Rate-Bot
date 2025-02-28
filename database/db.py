import os
from datetime import datetime

import asyncpg
from config_data import config

from logger.logging_settings import logger


async def create_db_pool():
    """Создает пул подключений к базе данных."""
    return await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", config.POSTGRES_USER),
        password=os.getenv("POSTGRES_PASSWORD", config.POSTGRES_PASSWORD),
        database=os.getenv("POSTGRES_DB", config.POSTGRES_DB),
        host=os.getenv("POSTGRES_HOST", config.POSTGRES_HOST),
        port=int(os.getenv("POSTGRES_PORT", config.POSTGRES_PORT)),
    )


async def create_table(pool):
    """Создает таблицу 'users', если она не существует."""
    try:
        async with pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    is_bot BOOLEAN NOT NULL,
                    is_premium BOOLEAN DEFAULT FALSE,
                    date_start TIMESTAMP NOT NULL,
                    timezone TEXT NOT NULL,
                    currency_data TEXT[] DEFAULT '{}',
                    everyday BOOLEAN DEFAULT FALSE,
                    location TEXT[] DEFAULT '{}'
                );
            """)
            logger.info("Table 'users' has been created or already exists.")
    except Exception as e:
        logger.error(f"Error creating table 'users': {e}")
        raise  # Повторно выбрасываем исключение для обработки на более высоком уровне


async def add_user_to_db(pool, user_data):
    """Добавляет пользователя в базу данных."""
    try:
        async with pool.acquire() as connection:
            formatted_data = {
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "username": user_data["username"],
                "chat_id": user_data["chat_id"],
                "is_bot": user_data["is_bot"],
                "date_start": datetime.strptime(user_data["date_start"], "%d/%m/%Y %H:%M"),
                "timezone": user_data["timezone"]
            }

            logger.debug(f"Formatted user data: {formatted_data}")  # Лог отладочного вывода

            await connection.execute("""
                INSERT INTO users (user_id, name, username, chat_id, is_bot, date_start, timezone)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (user_id) DO NOTHING
            """, *formatted_data.values())
            logger.info(f"User {formatted_data['user_id']} added to the database.")
    except Exception as e:
        logger.error(f"Error adding user to the database: {e}")
        raise



async def update_user(pool, user_id, selected_currency=None, everyday=None):
    """Обновляет данные пользователя."""
    try:
        async with pool.acquire() as connection:
            update_fields = []
            update_values = []

            if selected_currency is not None:
                # Преобразуем множество в список и передаём как массив PostgreSQL (TEXT[])
                currency_list = list(selected_currency)  # {'USD', 'EUR'} -> ['USD', 'EUR']
                update_fields.append(f"currency_data = ${len(update_values) + 1}::TEXT[]")
                update_values.append(currency_list)

            if everyday is not None:
                update_fields.append(f"everyday = ${len(update_values) + 1}")
                update_values.append(everyday)

            if update_fields:
                update_values.append(user_id)
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ${len(update_values)}"
                await connection.execute(query, *update_values)
                logger.info(f"User {user_id} updated successfully.")
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise




async def get_user_by_id(pool, user_id):
    """Возвращает данные пользователя по его ID."""
    try:
        async with pool.acquire() as connection:
            user = await connection.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from the database: {e}")
        return None


async def get_selected_currency(pool, user_id):
    """Возвращает выбранные валюты пользователя."""
    try:
        async with pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT currency_data FROM users WHERE user_id = $1", user_id
            )
            return result if result else []  # PostgreSQL TEXT[] уже возвращает список
    except Exception as e:
        logger.error(f"Error fetching selected_currency for {user_id} from the database: {e}")
        return []



async def get_everyday(pool, user_id):
    """Возвращает настройку 'everyday' пользователя."""
    try:
        async with pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT everyday FROM users WHERE user_id = $1", user_id
            )
            return result
    except Exception as e:
        logger.error(f"Error fetching everyday for {user_id} from the database: {e}")
        return None