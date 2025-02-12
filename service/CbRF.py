import datetime
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests

from logger.logging_settings import logger

def compare_dates(today_str, date_str):
  """
  Сравнивает две даты в формате строки.

  Args:
      today_str: Строка с текущей датой в формате "ДД/ММ/ГГГГ".
      date_str: Строка с датой из XML в формате "ДД.ММ.ГГГГ".

  Returns:
      "today" - если даты совпадают.
      "tomorrow" - если today_str на один день меньше date_str.
      "error" - в противном случае.
  """

  try:
    today = datetime.datetime.strptime(today_str, "%d/%m/%Y").date()
    date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()

    if today == date:
      return "today"
    elif today == date - datetime.timedelta(days=1):
      return "tomorrow"
  except ValueError:
    return "error"  # Ошибка при неверном формате даты



def currency():
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


def course_today(selected_data):
    try:
        today = datetime.date.today().strftime("%d/%m/%Y")  # Формат: ДД/ММ/ГГГГ
        url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={today}"
        target_ids = []  # Список нужных ID
        response = requests.get(url)
        xml_data = response.content
        root = ET.fromstring(xml_data)

        # save_file(xml_data, "course_today")

        for i in selected_data:
            target_ids.append(i['id'])

        date = root.get('Date')

        result_string = f"{today}\n"  # Дата на первой строке
        result_info = f"Курс {date}: "

        what_day = compare_dates(today, date)
        if what_day == "today":
            for valute in root.findall('Valute'):
                if valute.get('ID') in target_ids:
                    name = valute.find('Name').text
                    value = valute.find('Value').text
                    value = value.replace(',', '.')
                    nominal = valute.find('Nominal').text
                    result = float(value) / float(nominal)
                    result_string += f"{name} = {result}\n"
                    result_info += f"{name} = {result} "
            logger.info(result_info)
        if what_day == "tomorrow":
            for valute in root.findall('Valute'):
                if valute.get('ID') in target_ids:
                    name = valute.find('Name').text
                    value = valute.find('Value').text
                    value = value.replace(',', '.')
                    nominal = valute.find('Nominal').text
                    result = float(value) / float(nominal)
                    result_string += f"{name} = {result}\n"
                    result_info += f"{name} = {result} "
            logger.info(result_info)
        return result_string.strip()  # Удаляем конечный символ новой строки
    except Exception as e:
        logger.exception(e)


def dinamic_course(cod):
    today = datetime.date.today().strftime("%d/%m/%Y")  # Формат: ДД/ММ/ГГГГ
    url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1=02/03/2001&date_req2={today}&VAL_NM_RQ={cod}"
    response = requests.get(url)
    xml_data = response.content
    logger.info(f'Success. Obtained exchange rate dynamics for currencies: {cod}')
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
        value = float(record.find('Value').text.replace(',', '.'))  # 6
        data.setdefault(year, {})[date_str] = value  # 7
    return data  # 8


def graf_each_year(dollar_data):
    current_year = datetime.date.today().year
    years = list(range(2001, current_year + 1))

    data_by_year = {year: dollar_data.get(year, {}) for year in years}

    # Создаем график для каждого года
    for year, data in data_by_year.items():
        if data:
            # Преобразование данных для DataFrame
            data_for_df = [{'Дата': date_str, 'Курс': value} for date_str, value in data.items()]

            # Создаем DataFrame
            df = pd.DataFrame(data_for_df)

            # Преобразование строковых дат в datetime
            df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y')

            # Сортировка данных по дате
            df = df.sort_values(by='Дата')

            # Создаем график
            fig = go.Figure()

            # Добавление линии
            fig.add_trace(go.Scatter(
                x=df['Дата'],
                y=df['Курс'],
                mode='lines',
                hoverinfo='x+y',
                line=dict(width=2)
            ))

            # Настройка оформления
            fig.update_layout(
                title=f'Курс доллара в {year} году',
                xaxis_title='Дата',
                yaxis_title='Курс',
                xaxis=dict(
                    tickformat='%d.%m',
                    dtick='M1',
                    tickangle=45
                ),
                hovermode='x'
            )

            # Отображение графика
            fig.show()
        else:
            print(f"Данные за {year} год не найдены.")


def graf_mobile(dollar_data):
    # Создаем пустой DataFrame для объединения данных
    all_data = pd.DataFrame()

    # Перебираем данные по годам и объединяем их в один DataFrame
    for year, data in dollar_data.items():
        if data:
            # Преобразование данных для DataFrame
            data_for_df = [{'Дата': date_str, 'Курс': value, 'Год': year} for date_str, value in data.items()]

            # Создаем временный DataFrame и добавляем его к общему
            temp_df = pd.DataFrame(data_for_df)
            all_data = pd.concat([all_data, temp_df], ignore_index=True)

    # Преобразование строковых дат в datetime
    all_data['Дата'] = pd.to_datetime(all_data['Дата'], format='%d.%m.%Y')

    # Сортировка данных по дате
    all_data = all_data.sort_values(by='Дата')

    # Создаем график
    fig = go.Figure()

    # Перебираем уникальные годы и добавляем данные для каждого года на график
    for year in all_data['Год'].unique():
        year_data = all_data[all_data['Год'] == year]
        fig.add_trace(go.Scatter(
            x=year_data['Дата'],
            y=year_data['Курс'],
            mode='lines',
            name=f'Курс в {year}',
            hoverinfo='x+y'
        ))

    # Настройка оформления
    fig.update_layout(
        title='Курс доллара по годам',
        xaxis_title='Дата',
        yaxis_title='Курс',
        xaxis=dict(
            tickformat='%d.%m.%y',
            tickangle=45
        ),
        hovermode='x'
    )

    # Сохранение графика в HTML-файл
    file_path = "index.html"
    fig.write_html(file_path)
    return file_path


def graf_not_mobile(dollar_data):
    # Создаем пустой DataFrame для объединения данных
    all_data = pd.DataFrame()

    # Перебираем данные по годам и объединяем их в один DataFrame
    for year, data in dollar_data.items():
        if data:
            # Преобразование данных для DataFrame
            data_for_df = [{'Дата': date_str, 'Курс': value, 'Год': year} for date_str, value in data.items()]

            # Создаем временный DataFrame и добавляем его к общему
            temp_df = pd.DataFrame(data_for_df)
            all_data = pd.concat([all_data, temp_df], ignore_index=True)

    # Преобразование строковых дат в datetime
    all_data['Дата'] = pd.to_datetime(all_data['Дата'], format='%d.%m.%Y')

    # Сортировка данных по дате
    all_data = all_data.sort_values(by='Дата')

    # Создаем график
    fig = go.Figure()

    # Перебираем уникальные годы и добавляем данные для каждого года на график
    for year in all_data['Год'].unique():
        year_data = all_data[all_data['Год'] == year]
        fig.add_trace(go.Scatter(
            x=year_data['Дата'],
            y=year_data['Курс'],
            mode='lines',
            name=f'Курс в {year}',
            hoverinfo='x+y'
        ))

    # Настройка оформления
    fig.update_layout(
        title='Курс доллара по годам',
        xaxis_title='Дата',
        yaxis_title='Курс',
        xaxis=dict(
            tickformat='%d.%m.%y',
            tickangle=45
        ),
        hovermode='x'
    )
    return fig.show()


def analys_courses():
    course_today()

    dollarCod = 'R01235'
    euroCod = 'R01239'

    dollar = dinamic_course(dollarCod)
    euro = dinamic_course(euroCod)

    save_file(dollar, "dollar")
    save_file(euro, "euro")

    dollar_data = parse_xml_data(dollar)
    euro_data = parse_xml_data(euro)

    graf(dollar_data)
