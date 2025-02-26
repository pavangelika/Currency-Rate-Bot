import os
from datetime import datetime

import asyncpg
import asyncio
from config_data import config

from logger.logging_settings import logger


async def create_db_pool():
    return await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", config.POSTGRES_USER),  # Используем переменные окружения
        password=os.getenv("POSTGRES_PASSWORD", config.POSTGRES_PASSWORD),
        database=os.getenv("POSTGRES_DB", config.POSTGRES_DB),
        host=os.getenv("POSTGRES_HOST", config.POSTGRES_HOST),  # Имя сервиса PostgreSQL
        port=int(os.getenv("POSTGRES_PORT", config.POSTGRES_PORT)),
    )

# Функция для создания таблицы, если она не существует
async def create_table(pool):
    try:
        async with pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    is_bot BOOLEAN NOT NULL,
                    is_premium BOOLEAN NOT NULL,
                    date_start TIMESTAMP NOT NULL,
                    timezone TEXT NOT NULL
                );
            """)
            logger.info("Table 'users' has been created or already exists.")
    except Exception as e:
        logger.error(f"Error creating table 'users': {e}")

async def add_user_to_db(pool, user_data):
    try:
        async with pool.acquire() as connection:
            # Преобразование ключей
            formatted_data = {
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "username": user_data["username"],
                "chat_id": user_data["chat_id"],
                "is_bot": user_data["is_bot"],
                "is_premium": user_data["is_premium"] if user_data["is_premium"] is not None else False,  # Установим False, если None
                "date_start": datetime.strptime(user_data["date_start"], "%d/%m/%Y %H:%M"),  # Конвертация даты
                "timezone": user_data["timezone"]
            }

            print("Formatted user data:", formatted_data)  # Лог отладочного вывода

            await connection.execute("""
                INSERT INTO users (user_id, name, username, chat_id, is_bot, is_premium, date_start, timezone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id) DO NOTHING
            """,
            formatted_data["user_id"],
            formatted_data["name"],
            formatted_data["username"],
            formatted_data["chat_id"],
            formatted_data["is_bot"],
            formatted_data["is_premium"],
            formatted_data["date_start"],
            formatted_data["timezone"]
            )
            logger.info(f"User {formatted_data['user_id']} added to the database.")
    except Exception as e:
        logger.error(f"Error adding user to the database: {e}")

# Функция для обновления данных пользователя
async def update_user_in_db(pool, user_id, updated_data):
    try:
        async with pool.acquire() as connection:
            # Обновление информации о пользователе
            set_clause = ", ".join([f"{key} = ${index + 2}" for index, key in enumerate(updated_data.keys())])
            query = f"UPDATE users SET {set_clause} WHERE user_id = $1"
            await connection.execute(query, user_id, *updated_data.values())
            logger.info(f"User {user_id} data updated.")
    except Exception as e:
        logger.error(f"Error updating user {user_id} in the database: {e}")

# Функция для получения пользователя по ID
async def get_user_by_id(pool, user_id):
    try:
        async with pool.acquire() as connection:
            user = await connection.fetchrow("""
                SELECT * FROM users WHERE user_id = $1
            """, user_id)
            return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from the database: {e}")
        return None