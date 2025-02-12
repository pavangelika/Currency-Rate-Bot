import logging
import os
from typing import Optional

def create_handler(handler_class, level: int, formatter: logging.Formatter, filename: Optional[str] = None, mode: str = 'a', encoding: str = 'utf-8', filters=None):
    """
    Создает и настраивает обработчик для логирования.

    :param handler_class: Класс обработчика (например, logging.StreamHandler или logging.FileHandler).
    :param level: Уровень логирования.
    :param formatter: Форматтер для обработчика.
    :param filename: Имя файла (для FileHandler).
    :param mode: Режим открытия файла (для FileHandler).
    :param encoding: Кодировка файла (для FileHandler).
    :param filters: Список фильтров для обработчика.
    :return: Настроенный обработчик.
    """
    if handler_class == logging.FileHandler:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))  # Создаем директорию, если ее нет
        handler = handler_class(filename, mode, encoding)
    else:
        handler = handler_class()

    handler.setLevel(level)
    handler.setFormatter(formatter)
    if filters:
        for filter in filters:
            handler.addFilter(filter)
    return handler

def setup_logging(log_file: str = "log/mylog.log", error_log_file: str = "log/error.log", log_level: int = logging.INFO):
    """Настраивает логирование с выводом в консоль и записью в файл."""

    # Базовый форматтер
    log_formatter = logging.Formatter(
        '[%(asctime)s] #%(levelname)-8s %(filename)s:%(lineno)d - %(message)s'
    )

    # Создаем логгер
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Обработчик для консоли
    console_handler = create_handler(logging.StreamHandler, log_level, log_formatter)
    logger.addHandler(console_handler)

    # Обработчик для основного файла логирования
    file_handler = create_handler(logging.FileHandler, log_level, log_formatter, log_file, 'w')
    logger.addHandler(file_handler)

    # Обработчик для файла ошибок
    error_filter = lambda record: record.levelno == logging.ERROR  # Фильтр для ошибок
    error_handler = create_handler(logging.FileHandler, logging.ERROR, log_formatter, error_log_file, filters=[error_filter])
    logger.addHandler(error_handler)

    return logger

# Инициализация логгера
logger = setup_logging()