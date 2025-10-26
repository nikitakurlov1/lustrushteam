from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List
import config


def get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup:
    """Главное меню в зависимости от роли"""
    keyboard = [
        [KeyboardButton("👤 Профиль"), KeyboardButton("📚 Материалы")],
        [KeyboardButton("📜 История профитов")]
    ]
    
    if role in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        keyboard.append([KeyboardButton("👥 Моя команда"), KeyboardButton("📊 Статистика")])
        keyboard.append([KeyboardButton("⚙️ Управление")])
    
    if role == config.ROLE_HEAD:
        keyboard.append([KeyboardButton("🔧 Админ панель")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ панели"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить профит", callback_data="admin_add_profit")],
        [InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Глобальная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🏆 Топ пользователей", callback_data="admin_top")],
        [InlineKeyboardButton("📝 Логи действий", callback_data="admin_logs")],
        [InlineKeyboardButton("📥 Экспорт отчета", callback_data="admin_export")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_user_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями"""
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить роль", callback_data="manage_change_role")],
        [InlineKeyboardButton("👤 Назначить мини-хеда", callback_data="manage_assign_mini_head")],
        [InlineKeyboardButton("🏷 Установить FakeTag", callback_data="manage_set_fake_tag")],
        [InlineKeyboardButton("❌ Деактивировать", callback_data="manage_deactivate")],
        [InlineKeyboardButton("📋 Список пользователей", callback_data="manage_list_users")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_statistics_period_keyboard(prefix: str = "stats") -> InlineKeyboardMarkup:
    """Клавиатура выбора периода статистики"""
    keyboard = [
        [
            InlineKeyboardButton("📅 День", callback_data=f"{prefix}_day"),
            InlineKeyboardButton("📅 Неделя", callback_data=f"{prefix}_week")
        ],
        [
            InlineKeyboardButton("📅 Месяц", callback_data=f"{prefix}_month"),
            InlineKeyboardButton("📅 Все время", callback_data=f"{prefix}_all")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    keyboard = [
        [InlineKeyboardButton("👔 Head", callback_data="role_Head")],
        [InlineKeyboardButton("👨‍💼 Mini Head", callback_data="role_Mini Head")],
        [InlineKeyboardButton("👷 Worker", callback_data="role_Worker")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_mini_head_selection_keyboard(mini_heads: List) -> InlineKeyboardMarkup:
    """Клавиатура выбора мини-хеда"""
    keyboard = []
    
    for mini_head in mini_heads:
        name = mini_head.username or f"ID: {mini_head.telegram_id}"
        keyboard.append([InlineKeyboardButton(
            f"👨‍💼 {name}",
            callback_data=f"select_mini_head_{mini_head.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_users")])
    return InlineKeyboardMarkup(keyboard)


def get_user_list_keyboard(users: List, action: str = "view") -> InlineKeyboardMarkup:
    """Клавиатура списка пользователей"""
    keyboard = []
    
    for user in users[:20]:  # Ограничиваем 20 пользователями
        name = user.username or f"ID: {user.telegram_id}"
        role_emoji = "👔" if user.role == config.ROLE_HEAD else "👨‍💼" if user.role == config.ROLE_MINI_HEAD else "👷"
        keyboard.append([InlineKeyboardButton(
            f"{role_emoji} {name} ({user.role})",
            callback_data=f"{action}_user_{user.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_users")])
    return InlineKeyboardMarkup(keyboard)


def get_back_button(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]])


def get_confirm_keyboard(action: str, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{user_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="admin_users")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_materials_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура материалов"""
    keyboard = [
        [InlineKeyboardButton("🤖 eToro Trading Bot", url=f"https://t.me/{config.ETORO_BOT_LINK.replace('@', '')}")],
        [InlineKeyboardButton("📖 Руководство по боту", url=config.MANUAL_LINK)],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)
