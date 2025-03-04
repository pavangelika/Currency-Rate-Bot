import os
import git
import shutil

from logger.logging_settings import logger

current_dir = os.path.dirname(__file__)  #Получаем путь к текущему файлу (скрипту)
REPO_PATH = os.path.dirname(current_dir)  #Идем в корневую директорию
STATIC_PATH = os.path.join(REPO_PATH, 'static') #Переход в папку static
GITHUB_REPO_URL = "git@github.com:pavangelika/CurrencyRate.git"  # SSH или HTTPS ссылка на репозиторий
COMMIT_MESSAGE = "Автообновление графиков"


def upload_to_github():
    """
    Загружает файлы в репозиторий GitHub.
    """
    try:
        # Открываем локальный репозиторий
        repo = git.Repo(REPO_PATH)

        # Проверяем наличие изменений
        repo.git.add(STATIC_PATH)  # Добавляем только папку с графиками
        if repo.is_dirty():
            repo.git.commit("-m", COMMIT_MESSAGE)
            repo.git.push("origin", "main")  # Пушим на GitHub
            logger.info("Изменения загружены на GitHub")
    except Exception as e:
        logger.error(f"Ошибка при загрузке в GitHub: {e}")


