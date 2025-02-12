from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from logging_settings import logger

from lexicon.lexicon import LEXICON_BTN




def create_inline_kb(width: int,
                     *args: str,
                     **kwargs: str) -> InlineKeyboardMarkup:
    """ Функция для генерации инлайн-клавиатур <на лету>"""
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=LEXICON_BTN[button] if button in LEXICON_BTN else button,
                callback_data=button))
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=button))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()

def keyboard_with_pagination_and_selection(width: int,
                            *args: str,
                            last_btn: str | None = None,
                            page: int = 1,
                            items_per_page: int = 11,
                            selected_buttons: set[str] = None,
                            **kwargs: str) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с пагинацией.

    :param width: Количество кнопок в строке.
    :param args: Кнопки, которые будут добавлены в клавиатуру.
    :param last_btn: Текст для последней кнопки (например, "Готово").
    :param page: Текущая страница пагинации.
    :param items_per_page: Количество кнопок на одной странице.
    :param kwargs: Дополнительные кнопки (текст и callback_data).
    :return: Объект InlineKeyboardMarkup.
    """
    if selected_buttons is None:
        selected_buttons = set()

    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []

    # Объединяем все кнопки из args и kwargs
    all_buttons = list(args) + list(kwargs.keys())

    # Вычисляем общее количество страниц
    total_pages = (len(all_buttons) + items_per_page - 1) // items_per_page

    # Определяем диапазон кнопок для текущей страницы
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    paginated_buttons = all_buttons[start_index:end_index]

    # Добавляем кнопки на текущую страницу
    for button in paginated_buttons:
        # Определяем текст кнопки
        text = kwargs.get(button, LEXICON_BTN.get(button, button))
        # Добавляем отметку, если кнопка выбрана
        if button in selected_buttons:
            text = f"✅ {text}"
        buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=f"toggle_{button}_{page}"  # Добавляем префикс для обработки
        ))

    # Добавляем кнопки пагинации
    pagination_buttons = []

    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"page_{page - 1}"
        ))
    else:
        # Если это первая страница, блокируем кнопку "Назад"
        pagination_buttons.append(InlineKeyboardButton(
            text="✖️",
            callback_data="no_action"  # Заглушка, ничего не делает
        ))

    # Кнопка с номером текущей страницы
    pagination_buttons.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="no_action"  # Заглушка, ничего не делает
    ))

    if page < total_pages:
        pagination_buttons.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"page_{page + 1}"
        ))
    else:
        # Если это последняя страница, блокируем кнопку "Вперед"
        pagination_buttons.append(InlineKeyboardButton(
            text="✖️",
            callback_data="no_action"  # Заглушка, ничего не делает
        ))

    # Добавляем основные кнопки
    kb_builder.row(*buttons, width=width)

    # Добавляем кнопки пагинации
    kb_builder.row(*pagination_buttons)

    # Добавляем последнюю кнопку, если она передана
    if last_btn:
        kb_builder.row(InlineKeyboardButton(
            text=last_btn,
            callback_data='last_btn'
        ))

    # Возвращаем клавиатуру
    return kb_builder.as_markup()






