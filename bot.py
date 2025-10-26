import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from database import init_db
from handlers import (
    start_command,
    secret_admin_command,
    profile_command,
    materials_command,
    my_team_command,
    statistics_command,
    management_command,
    admin_panel_command,
    profit_history_command,
    export_report_command,
    smart_analytics_command,
    live_dashboard_command,
    heads_stats_command,
    inactive_users_command,
    profit_chart_command,
    team_comparison_chart_command,
    quick_stats_command,
    button_callback,
    handle_text_message
)
from voting_handlers import (
    polls_menu_command,
    show_active_polls,
    view_poll,
    vote_handler,
    show_poll_results,
    top_voters_command,
    my_polls_stats_command
)
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")


async def post_init(application: Application):
    """Инициализация после запуска бота"""
    await init_db()
    logger.info("База данных инициализирована")


def main():
    """Главная функция запуска бота"""
    
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env и добавьте токен бота.")
        return
    
    # Создаем приложение
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("adminzxcv1236", secret_admin_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("materials", materials_command))
    application.add_handler(CommandHandler("team", my_team_command))
    application.add_handler(CommandHandler("stats", statistics_command))
    application.add_handler(CommandHandler("manage", management_command))
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(CommandHandler("history", profit_history_command))
    application.add_handler(CommandHandler("export", export_report_command))
    
    # Расширенная аналитика
    application.add_handler(CommandHandler("analytics", smart_analytics_command))
    application.add_handler(CommandHandler("live", live_dashboard_command))
    application.add_handler(CommandHandler("heads", heads_stats_command))
    application.add_handler(CommandHandler("inactive", inactive_users_command))
    application.add_handler(CommandHandler("chart", profit_chart_command))
    application.add_handler(CommandHandler("compare", team_comparison_chart_command))
    application.add_handler(CommandHandler("quick", quick_stats_command))
    
    # Система голосований
    application.add_handler(CommandHandler("polls", polls_menu_command))
    application.add_handler(CommandHandler("topvoters", top_voters_command))
    application.add_handler(CommandHandler("mystats", my_polls_stats_command))
    
    # Обработчик callback кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    main()
