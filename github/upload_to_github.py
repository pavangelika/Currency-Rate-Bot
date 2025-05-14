import os
import time
from pathlib import Path
import git
from logger.logging_settings import logger
import subprocess

current_dir = os.path.dirname(__file__)  # Получаем путь к текущему файлу (скрипту)
REPO_PATH = os.path.dirname(current_dir)  # Идем в корневую директорию
STATIC_PATH = os.path.join(REPO_PATH, 'static')  # Переход в папку static
GITHUB_REPO_URL = "https://github.com/pavangelika/CurrencyRate.git"  # HTTPS ссылка
COMMIT_MESSAGE = "update charts"

DAYS_TO_KEEP = 1  # Сколько дней храним файлы
now = time.time()

def upload_to_github():
    """
    Загружает файлы в репозиторий GitHub.
    """
    try:
        # Открываем локальный репозиторий
        repo = git.Repo(REPO_PATH)

        # Убедитесь, что URL origin — HTTPS
        if "git@" in repo.remotes.origin.url:
            repo.remotes.origin.set_url("https://github.com/pavangelika/CurrencyRate.git")

        # Настройка учетных данных
        username = os.getenv("GIT_USERNAME")  # Логин GitHub
        password = os.getenv("GITHUB_TOKEN")  # Personal Access Token

        with repo.config_writer() as config:
            config.set_value("user", "email", os.getenv("GIT_USER_EMAIL"))
            config.set_value("user", "name", os.getenv("GIT_USER_NAME"))
            config.set_value("credential", "helper", "store")  # Кэшировать учетные данные

        for file in Path(STATIC_PATH).glob("*.html"):
            file_mtime = file.stat().st_mtime
            file_age = now - file_mtime
            # logger.info(f"Файл: {file}, время изменения: {file_mtime}, возраст: {file_age} секунд")
            # if file.is_file() and file_age > DAYS_TO_KEEP * 86400:
            if file.is_file() and file_age > DAYS_TO_KEEP * 14400: #удаляем файлы старше 4 часов
                file.unlink()
                logger.info(f"Удален старый файл: {file}")

        # Проверяем наличие изменений
        repo.git.add(STATIC_PATH)  # Добавляем только папку с графиками
        if repo.is_dirty():
            repo.git.commit("-m", COMMIT_MESSAGE)
            # Пушим с явным указанием учетных данных
            repo.git.push(
                "origin",
                "main",
                env={
                    "GIT_USERNAME": username,
                    "GIT_PASSWORD": password
                }
            )
            logger.info("Изменения загружены через HTTPS")
    except Exception as e:
        logger.error(f"Ошибка при загрузке в GitHub: {e}")
