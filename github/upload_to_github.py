import os
import git
import shutil
from config_data import config


# Конфигурация
# Получаем путь к текущему файлу (скрипту)
current_dir = os.path.dirname(__file__)
# Поднимаемся на уровень вверх (получаем CurrencyRate)
REPO_PATH = os.path.dirname(current_dir)
# Добавляем 'static'
STATIC_PATH = os.path.join(REPO_PATH, 'static')
print(STATIC_PATH)
# REPO_PATH = "/path/to/your/local/repo"  # Укажи путь к локальному репозиторию
# STATIC_PATH = os.path.join(REPO_PATH, "static")  # Путь к папке с графиками
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
            print("Изменения загружены на GitHub")
        else:
            print("Нет новых изменений")

    except Exception as e:
        print(f"Ошибка при загрузке в GitHub: {e}")


# Вызываем функцию
upload_to_github()
