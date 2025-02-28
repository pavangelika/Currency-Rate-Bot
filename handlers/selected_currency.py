# Функция для извлечения кода валюты из строки
import json
from logger.logging_settings import logger


def extract_currency_code(currency_str):
    """
    Извлекает код валюты из строки вида "Доллар США (USD)" -> "USD".
    """
    if '(' in currency_str and ')' in currency_str:
        return currency_str.split('(')[-1].rstrip(')')
    return None

def update_selected_currency(user_data, user_id, currency_data):
    """
    Заменяет selected_currency на список объектов из currency.json,
    где charCode совпадает с кодами из selected_currency.
    """
    if user_id not in user_data:
        raise KeyError(f"User ID {user_id} not found in user_data.")

    selected_currency = user_data[user_id].get('selected_currency', set())
    updated_currencies = []

    for currency_str in selected_currency:
        code = extract_currency_code(currency_str)  # Предполагаем, что функция существует
        if code:
            # Ищем валюту в currency_data по charCode
            matched_currency = next((item for item in currency_data if item["charCode"] == code), None)
            if matched_currency:
                updated_currencies.append(matched_currency)  # Исправлено

    # Обновляем selected_currency
    user_data[user_id]['selected_currency'] = updated_currencies



def load_currency_data(file_path):
    """
    Загружает данные о валютах из JSON-файла.
    Если файл не найден, возвращает пустой список и логирует ошибку.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден.")
        return []
    except json.JSONDecodeError:
        logger.error(f"Файл {file_path} содержит некорректный JSON.")
        return []
