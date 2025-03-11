import os
import time
from pathlib import Path
import git
from logger.logging_settings import logger
import subprocess

current_dir = os.path.dirname(__file__)  # Получаем путь к текущему файлу (скрипту)
REPO_PATH = os.path.dirname(current_dir)  # Идем в корневую директорию
STATIC_PATH = os.path.join(REPO_PATH, 'static')  # Переход в папку static
GITHUB_REPO_URL = "git@github.com:pavangelika/CurrencyRate.git"  # SSH ссылка на репозиторий
COMMIT_MESSAGE = "Автообновление графиков"

DAYS_TO_KEEP = 1  # Сколько дней храним файлы
now = time.time()


def check_ssh_connection():
    try:
        result = subprocess.run(["ssh", "-T", "git@github.com"], capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
    except Exception as e:
        print(f"Ошибка при проверке SSH: {e}")


check_ssh_connection()


def upload_to_github():
    """
    Загружает файлы в репозиторий GitHub.
    """
    try:
        # Открываем локальный репозиторий
        repo = git.Repo(REPO_PATH)

        # Настройка Git (используем переменные окружения)
        repo.config_writer().set_value("user", "email", os.getenv("GIT_USER_EMAIL")).release()
        repo.config_writer().set_value("user", "name", os.getenv("GIT_USER_NAME")).release()

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
            repo.git.push("origin", "main")  # Пушим на GitHub
            logger.info("Изменения загружены на GitHub")
    except Exception as e:
        logger.error(f"Ошибка при загрузке в GitHub: {e}")
