from telegram import Bot
from datetime import datetime
from typing import Optional
import config


async def send_notification(bot: Bot, user_telegram_id: int, message: str):
    """Отправить уведомление пользователю"""
    try:
        await bot.send_message(chat_id=user_telegram_id, text=message)
        return True
    except Exception as e:
        print(f"Ошибка отправки уведомления пользователю {user_telegram_id}: {e}")
        return False


def format_number(number: float) -> str:
    """Форматирование числа с разделителями"""
    return f"{int(number):,}".replace(',', ' ')


def format_date(date: datetime) -> str:
    """Форматирование даты"""
    return date.strftime("%d.%m.%Y %H:%M")


def get_role_emoji(role: str) -> str:
    """Получить эмодзи для роли"""
    if role == config.ROLE_HEAD:
        return "👑"
    elif role == config.ROLE_MINI_HEAD:
        return "💼"
    else:
        return "👷"


def get_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса"""
    status_emojis = {
        'Новичок': '🌱',
        'Начинающий': '📈',
        'Опытный': '💎',
        'Профессионал': '⭐',
        'Эксперт': '🏆',
        'Мастер': '👑',
        'Легенда': '🔥'
    }
    return status_emojis.get(status, '💎')


def check_role_access(user_role: str, required_role: str) -> bool:
    """Проверить доступ по роли"""
    role_hierarchy = {
        config.ROLE_HEAD: 3,
        config.ROLE_MINI_HEAD: 2,
        config.ROLE_WORKER: 1
    }
    
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
