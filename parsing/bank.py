import os
import json
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from logger.logging_settings import logger

# Получаем корневую директорию проекта (директорию, в которой находится bank.py)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Путь к папке save_files внутри проекта
save_folder = os.path.join(project_root, "save_files")

# Создаем папку save_files, если её нет
if not os.path.exists(save_folder):
    os.makedirs(save_folder)

async def parse_cities():
    """
    Парсит список городов и их ссылок с сайта 1000bankov.ru.
    Возвращает словарь с городами и ссылками.
    """
    async with async_playwright() as p:
        # Запуск браузера
        browser = await p.chromium.launch(headless=False)  # headless=False для отладки  # headless=True для скрытого режима
        page = await browser.new_page()

        # Переход на страницу
        await page.goto('https://1000bankov.ru/kurs/')

        # Клик на элемент для открытия списка городов
        # Ожидание появления элемента и клик
        try:
            # Ждем появления элемента
            await page.wait_for_selector('div.header__geo.geolink', timeout=5000)

            # Клик на элемент
            await page.click('div.header__geo.geolink')

            # Ждем, пока список городов загрузится
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Ошибка при клике на элемент: {e}")
            await browser.close()
            return {}

        await page.wait_for_timeout(2000)  # Ждем, пока список городов загрузится

        # Получаем HTML после клика
        content = await page.content()

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        # Находим все элементы <li> внутри #geo__columns
        city_list = soup.select('#geo__columns li')

        # Создаем словарь с городами и ссылками
        cities_dict = {}
        for li in city_list:
            a_tag = li.find('a')
            if a_tag:
                city_name = a_tag.text.strip()
                city_href = a_tag['href']
                cities_dict[city_name] = city_href

        # Закрываем браузер
        await browser.close()
        return save_cities_to_json(cities_dict)


def save_cities_to_json(cities_dict):
    """
    Сохраняет словарь с городами и ссылками в JSON-файл.

    :param cities_dict: Словарь с городами и ссылками.
    """
    # Путь к JSON-файлу
    json_file_path = os.path.join(save_folder, "cities.json")

    # Сохраняем cities_dict в JSON-файл
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(cities_dict, f, ensure_ascii=False, indent=4)

    logger.info(f"Словарь сохранен в файл: {json_file_path}")

def get_city_link(city_name):
    """
    Возвращает ссылку для указанного города из JSON-файла.

    :param city_name: Название города (например, "Абаза").
    :return: Ссылка на страницу города или None, если город не найден.
    """
    # Путь к JSON-файлу
    json_file_path = os.path.join(save_folder, "cities.json")

    # Чтение JSON-файла
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Файл {json_file_path} не найден.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Ошибка при чтении файла {json_file_path}.")
        return None

    # Поиск ссылки по названию города
    return cities_data.get(city_name)


async def parse_bank_branches(url):
    """
    Парсит названия банков и количество отделений по url города на сайте https://1000bankov.ru/kurs/.
    Возвращает словарь с названиями банков и количеством отделений.
    """
    async with async_playwright() as p:
        # Запуск браузера в headless-режиме
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(url)
        await page.wait_for_timeout(30000)
        # Получаем HTML-код страницы
        content = await page.content()

        # Закрываем браузер
        await browser.close()

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        # Находим все блоки с банками
        bank_blocks = soup.select('div.banks__item')

        # Создаем словарь для хранения результатов
        bank_branches = {}

        # Обрабатываем каждый блок с банком
        for block in bank_blocks:
            # Название банка
            bank_name = block.select_one('div.bank__title').text.strip()

            # Количество отделений
            branches_info = block.select_one('div.bank__info')
            if branches_info:
                branches_text = branches_info.text.strip()
                if "отделений" in branches_text:
                    # Извлекаем число из текста (например, "2 отделения" -> 2)
                    branches_count = int(branches_text.split()[0])
                else:
                    # Если текст не содержит "отделений", считаем, что отделений нет
                    branches_count = 0
            else:
                # Если блока с информацией нет, отделений нет
                branches_count = 0

            # Добавляем данные в словарь
            bank_branches[bank_name] = branches_count

        return bank_branches
