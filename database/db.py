import json
import os
from datetime import datetime

import asyncpg
from dotenv import load_dotenv

from logger.logging_settings import logger

# Загружаем переменные из .env
load_dotenv()


async def create_db_pool():
    """Создает пул подключений к базе данных."""
    return await asyncpg.create_pool(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=5432,  # Значение по умолчанию
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
                    currency_data JSONB DEFAULT '[]',                   
                    everyday BOOLEAN DEFAULT FALSE,
                    location JSONB DEFAULT '[]',
                    jobs JSONB DEFAULT '[]',
                    last_course_data TEXT DEFAULT ''
                );
            """)
            logger.info("Table 'users' has been created or already exists.")
            # currency_data TEXT[] DEFAULT '{}',
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


async def update_user_everyday(pool, user_id, everyday):
    """Обновляет статус ежедневной рассылки пользователя в БД."""
    try:
        async with pool.acquire() as connection:
            # Преобразуем значение everyday в булевое значение, если оно не является таковым
            if isinstance(everyday, bool):
                everyday_value = everyday
            elif isinstance(everyday, int):
                # Преобразуем числа 0/1 в False/True
                everyday_value = bool(everyday)
            else:
                logger.error(f"Invalid value for 'everyday': {everyday}. Expected a boolean or integer.")
                return

            query = "UPDATE users SET everyday = $1 WHERE user_id = $2"
            await connection.execute(query, everyday_value, user_id)
            # logger.info(f"Status of daily subscription was updated by user {user_id} to {everyday_value}")
    except Exception as e:
        logger.error(f"Error updating user {user_id} everyday status: {e}")
        raise


async def update_user_currency(pool: asyncpg.Pool, user_id: int, selected_currency):
    """Обновляет данные о валюте пользователя в БД."""
    try:
        async with pool.acquire() as connection:
            # Определяем корректный формат для хранения в jsonb
            if isinstance(selected_currency, list) and all(isinstance(item, dict) for item in selected_currency):
                currency_data = json.dumps(selected_currency, ensure_ascii=False)  # Конвертируем в JSON-строку
            elif isinstance(selected_currency, set) and all(isinstance(item, str) for item in selected_currency):
                currency_data = json.dumps(list(selected_currency),
                                           ensure_ascii=False)  # Преобразуем множество в список и затем в JSON
            else:
                raise ValueError("Неподдерживаемый формат selected_currency")

            # SQL-запрос для обновления jsonb-поля
            query = "UPDATE users SET currency_data = $1 WHERE user_id = $2"
            await connection.execute(query, currency_data, user_id)

            logger.info(f"User {user_id} currency updated successfully.")
    except Exception as e:
        logger.error(f"Error updating user {user_id} currency: {e}")
        raise

async def update_user_jobs(pool: asyncpg.Pool, user_id: int, job_id: str) -> None:
    """Добавляет job_id в массив jobs для указанного user_id."""
    try:
        async with pool.acquire() as connection:
            # Получаем текущий массив jobs
            current_jobs = await connection.fetchval(
                "SELECT jobs FROM users WHERE user_id = $1", user_id
            )

            # Если jobs отсутствует или это строка, создаем новый массив
            if current_jobs is None or isinstance(current_jobs, str):
                current_jobs = []

            # Если current_jobs — это строка, преобразуем её в список
            if isinstance(current_jobs, str):
                try:
                    current_jobs = json.loads(current_jobs)
                except json.JSONDecodeError:
                    current_jobs = []

            # Добавляем новый job_id в массив, если его там нет
            if job_id not in current_jobs:
                current_jobs.append(job_id)

            # Обновляем столбец jobs
            await connection.execute(
                "UPDATE users SET jobs = $1::jsonb WHERE user_id = $2",
                json.dumps(current_jobs, ensure_ascii=False),  # Преобразуем список в JSON-строку
                user_id
            )
    except Exception as e:
        logger.error(f"Error updating jobs for user {user_id}: {e}")
        raise

async def get_user_jobs(pool: asyncpg.Pool, user_id: int):
    """Возвращает задачи из планировщика пользователя."""
    try:
        async with pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT jobs FROM users WHERE user_id = $1", user_id
            )

            if result:
                return json.loads(result)  # Декодируем JSON-строку обратно в Python-объект
            return []  # Если данных нет, возвращаем пустой список

    except Exception as e:
        logger.error(f"Error fetching selected_currency for {user_id} from the database: {e}")
        return []

async def update_last_course_data(pool: asyncpg.Pool, user_id: int, course_data: str) -> None:
    """Обновляет последнее отправленное значение курса валют для указанного user_id."""
    try:
        async with pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET last_course_data = $1 WHERE user_id = $2",
                course_data,
                user_id
            )
            logger.info(f"Last course data updated for user {user_id}.")
    except Exception as e:
        logger.error(f"Error updating last_course_data for user {user_id}: {e}")
        raise

async def get_last_course_data(pool: asyncpg.Pool, user_id: int) -> str:
    """Возвращает последнее отправленное значение курса валют для указанного user_id."""
    try:
        async with pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT last_course_data FROM users WHERE user_id = $1", user_id
            )
            return result if result else ""
    except Exception as e:
        logger.error(f"Error fetching last_course_data for user {user_id}: {e}")
        return ""

async def get_user_by_id(pool, user_id):
    """Возвращает данные пользователя по его ID."""
    try:
        async with pool.acquire() as connection:
            user = await connection.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return user
    except Exception as e:
        logger.error(f"Error fetching user {user_id} from the database: {e}")
        return None


async def get_selected_currency(pool: asyncpg.Pool, user_id: int):
    """Возвращает выбранные валюты пользователя."""
    try:
        async with pool.acquire() as connection:
            result = await connection.fetchval(
                "SELECT currency_data FROM users WHERE user_id = $1", user_id
            )

            if result:
                return json.loads(result)  # Декодируем JSON-строку обратно в Python-объект
            return []  # Если данных нет, возвращаем пустой список

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


async def format_currency_from_db(db_result):
    """Преобразует строку из БД в нужный формат 'name(charCode)'."""
    try:
        # Если db_result - это строка, десериализуем ее
        if isinstance(db_result, str):
            currencies = json.loads(db_result)  # Десериализация JSON строки
        elif isinstance(db_result, list):
            currencies = db_result  # Если уже список, просто используем его
        else:
            raise ValueError("Invalid db_result format")

        formatted_currencies = []

        # Форматируем валюты
        for currency in currencies:
            # Если currency - строка, десериализуем её
            if isinstance(currency, str):
                currency = json.loads(currency)

            if isinstance(currency, dict):  # Убедимся, что элемент - это словарь
                name = currency.get('name')
                char_code = currency.get('charCode')
                if name and char_code:
                    formatted_currencies.append(f"{name} ({char_code})")
            else:
                logger.error(f"Invalid currency format: {currency}")

        # Возвращаем строку, соединенную через запятую
        return ', '.join(formatted_currencies)

    except Exception as e:
        logger.error(f"Error formatting currency from DB: {e}")
        return None
