import os
import time
from pathlib import Path
import git
from logger.logging_settings import logger
import subprocess

current_dir = os.path.dirname(__file__)
REPO_PATH = os.path.dirname(current_dir)
STATIC_PATH = os.path.join(REPO_PATH, 'static')
COMMIT_MESSAGE = "update charts"
DAYS_TO_KEEP = 1  # Хранение файлов до 4 часов
now = time.time()


def upload_to_github():
    """Загружает файлы в GitHub через HTTPS с токеном."""
    try:
        # Получение учетных данных из переменных окружения
        password = os.getenv("GITHUB_TOKEN")
        email = os.getenv("GIT_USER_EMAIL")
        name = os.getenv("GIT_USER_NAME")

        # Проверка наличия всех учетных данных
        if not all([ password, email, name]):
            missing = [var for var in ["GITHUB_TOKEN", "GIT_USER_EMAIL", "GIT_USER_NAME"]
                       if not os.getenv(var)]
            logger.error(f"Не заданы переменные окружения: {', '.join(missing)}")
            return

        # Настройка репозитория
        repo = git.Repo(REPO_PATH)

        # Принудительная установка HTTPS URL
        repo.remotes.origin.set_url(f"https://{name}:{password}@github.com/pavangelika/CurrencyRate.git")

        # Конфигурация пользователя
        with repo.config_writer() as config:
            config.set_value("user", "email", email)
            config.set_value("user", "name", name)
            config.set_value("credential", "helper", "store")

        # Удаление старых файлов
        for file in Path(STATIC_PATH).glob("*.html"):
            if file.is_file() and (now - file.stat().st_mtime) > DAYS_TO_KEEP * 14400:
                file.unlink()
                logger.info(f"Удален файл: {file}")

        # Фиксация и отправка изменений
        repo.git.add(STATIC_PATH)
        if repo.is_dirty():
            repo.git.commit("-m", COMMIT_MESSAGE)
            # Использование стандартного механизма аутентификации
            repo.git.push("origin", "main")
            logger.info("Изменения успешно отправлены")

    except git.exc.GitCommandError as e:
        logger.error(f"Ошибка Git: {e.stderr.strip()}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")


# Проверка окружения перед запуском
if __name__ == "__main__":
    required_vars = ["GIT_USERNAME", "GITHUB_TOKEN", "GIT_USER_EMAIL", "GIT_USER_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
    else:
        upload_to_github()