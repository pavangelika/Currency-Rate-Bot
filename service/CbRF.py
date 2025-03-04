import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from github.upload_to_github import upload_to_github
from logger.logging_settings import logger


def currency():
    """ Сохранение текущих кодов валют с сайта ЦБ РФ в currency_code.json """
    today = datetime.date.today().strftime("%d/%m/%Y")  # Формат: ДД/ММ/ГГГГ
    url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={today}"
    response = requests.get(url)
    xml_data = response.content
    root = ET.fromstring(xml_data)
    currencies = []

    for valute in root.findall('Valute'):
        currency_id = valute.get("ID")  # Изменено имя переменной
        name = valute.find('Name').text
        charCode = valute.find('CharCode').text
        currencies.append({"id": currency_id, "name": name, "charCode": charCode})

    try:
        logger.info('Success. Exchange rate codes saved to file: "currency_code.json"')
        with open("save_files/currency_code.json", "w", encoding="utf-8") as f:
            json.dump(currencies, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.exception(e)

    return currencies

def course_today(selected_data, day):
    """ Получение курса валют из списка выбранных валют и заданного дня """
    try:
        url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={day}"
        target_ids = []  # Список нужных ID
        response = requests.get(url)
        xml_data = response.content
        root = ET.fromstring(xml_data)

        target_ids = []  # Список нужных ID

        # Проверяем, в каком формате данные: список словарей или множества
        if isinstance(selected_data, list):
            for item in selected_data:
                if isinstance(item, dict) and "id" in item:
                    target_ids.append(item["id"])
                else:
                    logger.error(f"Некорректный формат данных валюты: {item}")

        elif isinstance(selected_data, set):  # Если это множество строк валют
            target_ids = list(selected_data)  # Конвертируем в список

        else:
            logger.error(f"Некорректный формат selected_data: {type(selected_data)}")
            return "Ошибка обработки данных."

        date = root.get('Date')
        today = day.replace("/", ".")

        if today == date:
            result_string = f"{day}\n"  # Дата на первой строке
            for valute in root.findall('Valute'):
                if valute.get('ID') in target_ids:
                    name = valute.find('Name').text
                    value = valute.find('Value').text
                    value = value.replace(',', '.')
                    nominal = valute.find('Nominal').text
                    result = float(value) / float(nominal)
                    result_string += f"{name} = {result}\n"
        elif today > date:
            result_string = f"Данные на {day} не опубликованы"
        return result_string
    except Exception as e:
        logger.exception(e)



def dinamic_course(cod):
    today = datetime.date.today().strftime("%d/%m/%Y")  # Формат: ДД/ММ/ГГГГ
    url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=02/03/2001&date_req2={today}&VAL_NM_RQ={cod}"
    response = requests.get(url)
    xml_data = response.content
    return xml_data


def save_file(data_xml, filename):
    try:
        # Определяем путь к корневой директории проекта
        project_root = Path(__file__).resolve().parent.parent

        # Формируем полный путь к файлу
        file_path = project_root / f'save_files/{filename}.xml'

        # Записываем содержимое в файл
        with open(file_path, 'wb') as f:
            f.write(data_xml)
            logger.info(f'Success. Fale saved to path: {file_path}')
    except Exception as e:
        # Выводим сообщение об ошибке, если запись не удалась
        print(f'Ошибка при сохранении файла: {e}')


def parse_xml_data(xml_data):
    """Парсит XML данные и возвращает словарь {год: {дата: значение курса}}."""
    root = ET.fromstring(xml_data)  # 1
    data = {}  # 2
    for record in root.findall('Record'):  # 3
        date_str = record.get('Date')  # 4
        year = int(date_str.split('.')[2])  # 5
        try:
          value = float(record.find('Value').text.replace(',', '.')) / float(record.find('Nominal').text) # 6
        except Exception as e:
          print(e)
        data.setdefault(year, {})[date_str] = value  # 7
    return data  # 8

# selected_data_list = []
# for sd in selected_data:
#     result = dinamic_course(sd['id'])
#     name = sd['charCode']
#     with open(f'{name}.xml', 'wb') as f:
#       f.write(result)
#     result_data = parse_xml_data(result)
#     selected_data_list.append({"name":name, "value":result_data})

import datetime
import requests
import xml.etree.ElementTree as ET

def categorize_currencies(currencies):
    """
    Разбивает валюты на группы на основе их значений.

    Args:
        currencies: Список словарей с данными о валютах.

    Returns:
        Список словарей с добавленной информацией о группах.
    """
    categorized_currencies = []

    for currency in currencies:
        name = currency['name']
        value_data = currency['value']

        # Получаем все значения курсов в одном списке
        all_values = [value for year in value_data.values() for value in year.values()]

        # Находим минимальное значение курса
        min_value = min(all_values) if all_values else 0

        # Определяем группу на основе минимального значения
        if min_value < 10:
            group = 1
        elif 0 <= min_value < 50:
            group = 2
        elif 50 <= min_value < 100:
            group = 3
        elif 100 <= min_value < 150:
            group = 4
        else:
            group = (min_value // 50) + 1  # Группировка по 50

        # Добавляем информацию о группе в словарь
        categorized_currencies.append({
            'name': name,
            'group': group,
            'value': value_data
        })

    return categorized_currencies



def graf_not_mobile(currencies, start_year, end_year):
    """
    Строит графики курсов валют за указанный период, группируя по указанным группам.

    Args:
        currencies: Список валют с данными о курсах и группах.
        start_year: Год начала периода.
        end_year: Год конца периода.
    """
   # Подготовка данных для графиков по группам
    grouped_data = {}
    for currency in currencies:
        name = currency['name']
        value_data = currency['value']
        group = currency['group']

        # Собираем данные для каждого года в пределах указанного диапазона
        for year in range(start_year, end_year + 1):
            year_data = value_data.get(year, {})
            if year_data:
                if group not in grouped_data:
                    grouped_data[group] = {'names': set(), 'data': []}  # Используем множество
                grouped_data[group]['names'].add(name)  # Добавляем имя валюты в множество
                grouped_data[group]['data'].append({'name': name, 'year': year, 'data': year_data})

    # Создаем график для каждой группы
    for group, data_group in grouped_data.items():
        fig = go.Figure()
        names_str = ', '.join(data_group['names'])  # Строка с уникальными именами валют

        for data_entry in data_group['data']:
            name = data_entry['name']
            year = data_entry['year']
            year_data = data_entry['data']

            # Преобразуем данные в DataFrame для удобства
            temp_df = pd.DataFrame(year_data.items(), columns=['Дата', 'Курс'])
            temp_df['Дата'] = pd.to_datetime(temp_df['Дата'], format='%d.%m.%Y')

            # Добавляем линию в график
            fig.add_trace(go.Scatter(
                x=temp_df['Дата'],
                y=temp_df['Курс'],
                mode='lines',
                name=f'{name} - {year}',
                hoverinfo='y+text',
                text=f'{name}'  # Отображение имени валюты при наведении
            ))

        # Настройка внешнего вида графика
        fig.update_layout(
            title=f'{names_str}: Курсы валют с {start_year} по {end_year} год',  # Уникальные имена валют
            xaxis_title='Дата',
            yaxis_title='Курс',
            xaxis=dict(
                tickformat='%d.%m.%y',
                tickangle=45
            ),
            hovermode='x',
            showlegend=False
        )

        # Показ графика
        fig.show()

# def graf_mobile(currencies, start_year, end_year):
#     """
#     Строит графики курсов валют за указанный период, группируя по указанным группам.
#
#     Args:
#         currencies: Список валют с данными о курсах и группах.
#         start_year: Год начала периода.
#         end_year: Год конца периода.
#     """
#     # Подготовка данных для графиков по группам
#     grouped_data = {}
#     for currency in currencies:
#         name = currency['name']
#         value_data = currency['value']
#         group = currency['group']
#
#         # Собираем данные для каждого года в пределах указанного диапазона
#         for year in range(start_year, end_year + 1):
#             year_data = value_data.get(year, {})
#             if year_data:
#                 if group not in grouped_data:
#                     grouped_data[group] = {'names': set(), 'data': []}  # Используем множество
#                 grouped_data[group]['names'].add(name)  # Добавляем имя валюты в множество
#                 grouped_data[group]['data'].append({'name': name, 'year': year, 'data': year_data})
#
#     # Создаем график для каждой группы
#     for group, data_group in grouped_data.items():
#         fig = go.Figure()
#         names_str = ', '.join(data_group['names'])  # Строка с уникальными именами валют
#
#         for data_entry in data_group['data']:
#             name = data_entry['name']
#             year = data_entry['year']
#             year_data = data_entry['data']
#
#             # Преобразуем данные в DataFrame для удобства
#             temp_df = pd.DataFrame(year_data.items(), columns=['Дата', 'Курс'])
#             temp_df['Дата'] = pd.to_datetime(temp_df['Дата'], format='%d.%m.%Y')
#
#             # Добавляем линию в график
#             fig.add_trace(go.Scatter(
#                 x=temp_df['Дата'],
#                 y=temp_df['Курс'],
#                 mode='lines',
#                 name=f'{name} - {year}',
#                 hoverinfo='y+text',
#                 text=f'{name}'  # Отображение имени валюты при наведении
#             ))
#
#         # Настройка внешнего вида графика
#         fig.update_layout(
#             title=f'{names_str}: Курсы валют с {start_year} по {end_year} год',  # Уникальные имена валют
#             xaxis_title='Дата',
#             yaxis_title='Курс',
#             xaxis=dict(
#                 tickformat='%d.%m.%y',
#                 tickangle=45
#             ),
#             hovermode='x',
#             showlegend=False
#         )
#
#     # Сохранение графика в HTML-файл
#     file_path = "index.html"
#     fig.write_html(file_path)
#     return file_path  # Возвращаем путь к файлу


SAVE_PATH = "static"  # Локальная папка для хранения файлов


def graf_mobile(currencies, start_year, end_year, user_id):
    """
    Строит графики курсов валют за указанный период для конкретного пользователя.

    Args:
        currencies: Список валют с данными о курсах.
        start_year: Год начала периода.
        end_year: Год конца периода.
        user_id: ID пользователя для уникальной ссылки.

    Returns:
        str: Ссылка на график.
    """
    grouped_data = {}

    # Группировка данных
    for currency in currencies:
        name = currency['name']
        value_data = currency['value']
        group = currency['group']

        for year in range(start_year, end_year + 1):
            year_data = value_data.get(year, {})
            if year_data:
                if group not in grouped_data:
                    grouped_data[group] = {'names': set(), 'data': []}
                grouped_data[group]['names'].add(name)
                grouped_data[group]['data'].append({'name': name, 'year': year, 'data': year_data})

    # Генерация графиков
    for group, data_group in grouped_data.items():
        fig = go.Figure()
        names_str = ', '.join(data_group['names'])

        for data_entry in data_group['data']:
            name = data_entry['name']
            year = data_entry['year']
            year_data = data_entry['data']

            temp_df = pd.DataFrame(year_data.items(), columns=['Дата', 'Курс'])
            temp_df['Дата'] = pd.to_datetime(temp_df['Дата'], format='%d.%m.%Y')

            fig.add_trace(go.Scatter(
                x=temp_df['Дата'],
                y=temp_df['Курс'],
                mode='lines',
                name=f'{name} - {year}',
                hoverinfo='y+text',
                text=f'{name}'
            ))

        fig.update_layout(
            title=f'{names_str}: Курсы валют с {start_year} по {end_year} год',
            xaxis_title='Дата',
            yaxis_title='Курс',
            xaxis=dict(
                tickformat='%d.%m.%y',
                tickangle=45
            ),
            hovermode='x',
            showlegend=False
        )

        # Генерация пути
        user_folder = os.path.join(SAVE_PATH, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        names = names_str.replace(", ", "_")
        # file_name = f"{names}_{start_year}_{end_year}.html"
        file_name = f"{names}.html"

        file_path = os.path.join(user_folder, file_name)

        fig.write_html(file_path)  # Сохраняем HTML

        # Генерируем ссылку
        file_url = f"{os.getenv("GITHUB_PAGES")}static/{user_id}/{file_name}"
        upload_to_github()
        return file_url