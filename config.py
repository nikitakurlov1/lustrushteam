import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///bot_database.db')

# Роли
ROLE_HEAD = 'Head'
ROLE_MINI_HEAD = 'Mini Head'
ROLE_WORKER = 'Worker'

# Статусы по сумме профитов (в рублях)
STATUS_LEVELS = {
    0: {'name': 'Новичок', 'emoji': '🐣', 'color': 'Серый'},
    10000: {'name': 'Опытный', 'emoji': '💼', 'color': 'Синий'},
    100000: {'name': 'Профи', 'emoji': '💎', 'color': 'Золотой'},
    500000: {'name': 'Элита', 'emoji': '🦾', 'color': 'Фиолетовый'}
}

# Старая система по количеству профитов (для обратной совместимости)
STATUS_BY_COUNT = {
    0: 'Новичок',
    10: 'Начинающий',
    25: 'Опытный',
    50: 'Профессионал',
    100: 'Эксперт',
    200: 'Мастер',
    500: 'Легенда'
}

# Ссылки на материалы
ETORO_BOT_LINK = '@eToroTrade_Robot'
MANUAL_LINK = 'https://telegra.ph/Rukovodstvo-po-rabote-s-eToro-Trading-Bot-10-26'
