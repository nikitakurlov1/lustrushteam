import os
from pathlib import Path

# Путь к медиа файлам
MEDIA_DIR = Path(__file__).parent
LOGO_PATH = MEDIA_DIR / "image.png"

def get_logo_path():
    """Получить путь к логотипу"""
    if LOGO_PATH.exists():
        return str(LOGO_PATH)
    return None

def get_logo_file():
    """Получить файл логотипа для отправки"""
    logo_path = get_logo_path()
    if logo_path:
        return open(logo_path, 'rb')
    return None
