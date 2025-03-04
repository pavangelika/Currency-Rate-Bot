import aiohttp
import asyncio

async def check_file_available(url, retries=10, delay=5):
    """
    Проверяет доступность файла по URL. Если файл не найден (404),
    делает повторные попытки с задержкой.

    Args:
        url (str): URL файла.
        retries (int): Количество повторных попыток (по умолчанию 10).
        delay (int): Задержка между попытками в секундах (по умолчанию 5).

    Returns:
        bool: True, если файл доступен, False после всех попыток.
    """
    async with aiohttp.ClientSession() as session:
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return True  # Файл найден
            except Exception as e:
                print(f"Ошибка запроса: {e}")

            print(f"Попытка {attempt + 1}/{retries}: Файл не найден, ждем {delay} сек...")
            await asyncio.sleep(delay)

    return False  # Файл не найден после всех попыток
