import json
import os

from playwright.async_api import async_playwright

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
    Парсит список городов и их ссылок с сайта 1000bankov.ru без использования BeautifulSoup.
    Возвращает словарь с городами и ссылками.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            await page.goto('https://1000bankov.ru/kurs/')

            # Кликаем по элементу, чтобы открыть список городов
            await page.wait_for_selector('div.header__geo.geolink', timeout=5000)
            await page.click('div.header__geo.geolink')

            # Ожидаем загрузки списка городов
            await page.wait_for_timeout(2000)

            # Извлекаем все <li> внутри #geo__columns
            city_elements = await page.query_selector_all('#geo__columns li a')

            cities_dict = {}
            for city in city_elements:
                city_name = await city.inner_text()
                city_href = await city.get_attribute('href')
                if city_name and city_href:
                    cities_dict[city_name.strip()] = city_href

            return save_cities_to_json(cities_dict)

        except Exception as e:
            logger.error(f"Ошибка при парсинге городов: {e}")
            return {}

        finally:
            await browser.close()


def save_cities_to_json(cities_dict):
    """
    Сохраняет словарь с городами и ссылками в JSON-файл.
    """
    json_file_path = os.path.join(save_folder, "cities.json")

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(cities_dict, f, ensure_ascii=False, indent=4)

    logger.info(f"Словарь сохранен в файл: {json_file_path}")


def get_city_link(city_name):
    """
    Возвращает ссылку для указанного города из JSON-файла.
    """
    json_file_path = os.path.join(save_folder, "cities.json")

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка при чтении файла {json_file_path}: {e}")
        return None

    return cities_data.get(city_name)


async def parse_bank_branches(url):
    """
    Парсит названия банков и количество отделений по url города на сайте 1000bankov.ru.
    Возвращает словарь с названиями банков и количеством отделений.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Переход на страницу с ожиданием полной загрузки
            await page.goto(url, wait_until='networkidle', timeout=90000)
            logger.info("Страница загружена")

            # Ожидание появления блоков с банками
            await page.wait_for_selector('div.banks__item', state='visible')
            logger.info("Блоки с банками найдены")

            # Извлекаем все блоки с банками
            bank_blocks = await page.query_selector_all('div.banks__item')
            logger.info(f"Найдено {len(bank_blocks)} банков")

            bank_branches = {}

            for block in bank_blocks:
                try:
                    # Название банка
                    bank_name_element = await block.query_selector('div.bank__title')
                    if bank_name_element:
                        bank_name = await bank_name_element.inner_text()
                        logger.info(f"Название банка: {bank_name}")
                    else:
                        logger.warning("Элемент с названием банка не найден")
                        continue

                    # Количество отделений
                    branches_info = await block.query_selector('div.bank__info')
                    if branches_info:
                        branches_text = await branches_info.inner_text()
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

                except Exception as e:
                    logger.error(f"Ошибка при обработке банка: {e}")
                    continue

            logger.info("Парсинг завершен, возвращаем данные")
            return bank_branches

        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы: {e}")
            return {}

        finally:
            logger.info("Закрываем браузер")
            await browser.close()
