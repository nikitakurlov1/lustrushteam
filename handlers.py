from telegram import Update, InputFile
from telegram.ext import ContextTypes, ConversationHandler
from db_operations import DatabaseOperations
from keyboards import *
from utils import send_notification, format_number, format_date, get_status_emoji
from reports import ReportGenerator
from analytics import AdvancedAnalytics
from database import User, async_session_maker
from sqlalchemy import select
from media import get_logo_file
import config
from datetime import datetime
import os


# Состояния для ConversationHandler
WAITING_PROFIT_USER, WAITING_PROFIT_AMOUNT, WAITING_FAKE_TAG_USER, WAITING_FAKE_TAG = range(4)
WAITING_ROLE_USER, WAITING_ASSIGN_USER, WAITING_DEACTIVATE_USER = range(4, 7)


async def secret_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Секретная команда для получения прав Head"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_or_create_user(user.id, user.username)
    
    # Назначаем роль Head
    if db_user.role != config.ROLE_HEAD:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user.id)
            )
            user_obj = result.scalar_one_or_none()
            if user_obj:
                user_obj.role = config.ROLE_HEAD
                await session.commit()
                
                # Отправляем логотип
                logo = get_logo_file()
                if logo:
                    await update.message.reply_photo(
                        photo=logo,
                        caption="👑 **LUST RUSH TEAM** 👑\n\n✅ Вы получили права Head!",
                        parse_mode='Markdown'
                    )
                    logo.close()
                
                await update.message.reply_text(
                    "🔧 Используйте /admin для доступа к админ панели\n"
                    "👑 Теперь у вас полный доступ к системе",
                    reply_markup=get_main_menu_keyboard(config.ROLE_HEAD)
                )
    else:
        await update.message.reply_text(
            "✅ У вас уже есть права Head!\n\n"
            "🔧 Используйте /admin для доступа к админ панели",
            reply_markup=get_main_menu_keyboard(config.ROLE_HEAD)
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Отправляем логотип
    logo = get_logo_file()
    if logo:
        await update.message.reply_photo(
            photo=logo,
            caption="🔥 **LUST RUSH TEAM** 🔥\n\nДобро пожаловать в команду!",
            parse_mode='Markdown'
        )
        logo.close()
    
    # Получаем или создаем пользователя
    db_user = await DatabaseOperations.get_or_create_user(user.id, user.username)
    
    # Если новый пользователь (Worker), предлагаем выбрать мини-хеда
    if db_user.role == config.ROLE_WORKER and not db_user.mini_head_id:
        mini_heads = await DatabaseOperations.get_all_users(role=config.ROLE_MINI_HEAD)
        
        if mini_heads:
            text = "👋 Добро пожаловать в LUST RUSH TEAM!\n\n"
            text += "Выберите вашего наставника (Mini Head):"
            
            await update.message.reply_text(
                text,
                reply_markup=get_mini_head_selection_keyboard(mini_heads)
            )
        else:
            await update.message.reply_text(
                "👋 Добро пожаловать!\n\n"
                "⌚️ Время начинать FULL WORK",
                reply_markup=get_main_menu_keyboard(db_user.role)
            )
    else:
        await update.message.reply_text(
            f"👋 С возвращением, {user.first_name}!\n\n"
            "⌚️ Время начинать FULL WORK",
            reply_markup=get_main_menu_keyboard(db_user.role)
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    # Получаем статистику
    stats = await DatabaseOperations.get_user_statistics(db_user.id)
    rank = await DatabaseOperations.get_user_rank(db_user.id)
    status_data = db_user.get_status(stats['total'])
    status = status_data['name']
    status_emoji = status_data['emoji']
    
    # Формируем сообщение
    text = "👤 Профиль\n"
    text += f"🆔 Айди: {db_user.telegram_id}\n"
    text += f"🧑🏾‍💻 Ник: @{db_user.username or 'не указан'}\n"
    text += f"📊 Профиты: {format_number(stats['total'])} ₽\n"
    text += f"💱 Кол-во профитов: {stats['count']}\n"
    text += f"{status_emoji} Статус: {status}\n\n"
    
    # Наставник
    if db_user.mini_head_id:
        mini_head = await DatabaseOperations.get_user_by_id(db_user.mini_head_id)
        if mini_head:
            text += f"👨‍🏫 Наставник: @{mini_head.username or mini_head.telegram_id}\n\n"
    else:
        text += "👨‍🏫 Наставник: отсутствует\n\n"
    
    # FakeTag
    if db_user.fake_tag:
        text += f"🤥 Ваш FakeTag: {db_user.fake_tag}\n\n"
    
    # Статистика по периодам
    text += f"💸 Общая сумма профитов: {format_number(stats['total'])} ₽\n"
    text += f"╭• За день: {format_number(stats['day'])} ₽\n"
    text += f"├• За неделю: {format_number(stats['week'])} ₽\n"
    text += f"╰• За месяц: {format_number(stats['month'])} ₽\n\n"
    
    # Дополнительная статистика
    text += f"🏆 Максимальный занос: {format_number(stats['max_profit'])} ₽\n"
    text += f"📊 Средний занос: {format_number(stats['avg_profit'])} ₽\n"
    
    if rank > 0:
        text += f"🥇 Вы на {rank} месте в общем рейтинге!"
    
    await update.message.reply_text(text)


async def materials_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать материалы"""
    text = "📚 Материалы для работы\n\n"
    text += "Здесь вы найдете все необходимые материалы и инструкции для работы:\n\n"
    text += f"🤖 Бот для торговли: {config.ETORO_BOT_LINK}\n"
    text += f"📖 Подробное руководство по работе с ботом"
    
    await update.message.reply_text(
        text,
        reply_markup=get_materials_keyboard()
    )


async def my_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать команду (для Mini Head и Head)"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await update.message.reply_text("❌ У вас нет доступа к этой функции")
        return
    
    # Получаем команду
    team = await DatabaseOperations.get_mini_head_team(db_user.id)
    
    if not team:
        await update.message.reply_text("👥 У вас пока нет команды")
        return
    
    # Получаем статистику команды
    team_stats = await DatabaseOperations.get_team_statistics(db_user.id)
    
    text = f"👥 Моя команда ({team_stats['members']} чел.)\n\n"
    text += f"💰 Общий профит команды: {int(team_stats['total']):,} ₽\n"
    text += f"📊 Количество профитов: {team_stats['count']}\n\n"
    text += "Участники:\n"
    
    for member in team:
        stats = await DatabaseOperations.get_user_statistics(member.id)
        status = member.get_status(stats['count'])
        text += f"\n👤 @{member.username or member.telegram_id}\n"
        text += f"   💎 {status} | 💰 {int(stats['total']):,} ₽ | 📊 {stats['count']} профитов\n"
    
    await update.message.reply_text(text)


async def statistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику (для Mini Head и Head)"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await update.message.reply_text("❌ У вас нет доступа к этой функции")
        return
    
    text = "📊 Выберите период для просмотра статистики:"
    
    await update.message.reply_text(
        text,
        reply_markup=get_statistics_period_keyboard("team_stats")
    )


async def management_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление (для Mini Head и Head)"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await update.message.reply_text("❌ У вас нет доступа к этой функции")
        return
    
    text = "⚙️ Управление\n\n"
    text += "Выберите действие:"
    
    await update.message.reply_text(
        text,
        reply_markup=get_user_management_keyboard()
    )


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель (только для Head)"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role != config.ROLE_HEAD:
        await update.message.reply_text("❌ У вас нет доступа к админ панели")
        return
    
    text = "🔧 Админ панель\n\n"
    text += "Добро пожаловать в панель управления!\n"
    text += "Здесь вы можете управлять всей системой."
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_panel_keyboard()
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await query.edit_message_text("❌ Пользователь не найден. Используйте /start")
        return
    
    data = query.data
    
    # Обработка голосований
    if data.startswith("polls_"):
        from voting_handlers import show_active_polls
        if data == "polls_active":
            await show_active_polls(update, context)
            return
        elif data == "polls_menu":
            await polls_menu_command(update, context)
            return
    
    if data.startswith("poll_view_"):
        from voting_handlers import view_poll
        await view_poll(update, context)
        return
    
    if data.startswith("vote_"):
        from voting_handlers import vote_handler
        await vote_handler(update, context)
        return
    
    if data.startswith("poll_results_"):
        from voting_handlers import show_poll_results
        await show_poll_results(update, context)
        return
    
    # Выбор мини-хеда при регистрации
    if data.startswith("select_mini_head_"):
        mini_head_id = int(data.split("_")[-1])
        await DatabaseOperations.assign_mini_head(db_user.id, mini_head_id, mini_head_id)
        
        await query.edit_message_text(
            "✅ Наставник назначен!\n\n⌚️ Время начинать FULL WORK",
            reply_markup=None
        )
        
        await query.message.reply_text(
            "Используйте меню ниже для навигации:",
            reply_markup=get_main_menu_keyboard(db_user.role)
        )
        return
    
    # Админ панель
    if data == "admin_panel":
        if db_user.role != config.ROLE_HEAD:
            await query.edit_message_text("❌ У вас нет доступа")
            return
        
        text = "🔧 Админ панель\n\n"
        text += "Выберите действие:"
        await query.edit_message_text(text, reply_markup=get_admin_panel_keyboard())
        return
    
    # Добавление профита
    if data == "admin_add_profit":
        if db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
            await query.edit_message_text("❌ У вас нет доступа")
            return
        
        context.user_data['action'] = 'add_profit'
        await query.edit_message_text(
            "➕ Добавление профита\n\n"
            "Отправьте Telegram ID пользователя:",
            reply_markup=get_back_button("admin_panel")
        )
        return ConversationHandler.END
    
    # Управление пользователями
    if data == "admin_users":
        if db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
            await query.edit_message_text("❌ У вас нет доступа")
            return
        
        await query.edit_message_text(
            "👥 Управление пользователями\n\nВыберите действие:",
            reply_markup=get_user_management_keyboard()
        )
        return
    
    # Глобальная статистика
    if data == "admin_stats":
        if db_user.role != config.ROLE_HEAD:
            await query.edit_message_text("❌ У вас нет доступа")
            return
        
        await query.edit_message_text(
            "📊 Выберите период:",
            reply_markup=get_statistics_period_keyboard("global_stats")
        )
        return
    
    # Статистика по периодам
    if data.startswith("global_stats_"):
        period = data.split("_")[-1]
        stats = await DatabaseOperations.get_global_statistics(period)
        
        period_name = {
            'day': 'день',
            'week': 'неделю',
            'month': 'месяц',
            'all': 'все время'
        }.get(period, 'все время')
        
        text = f"📊 Глобальная статистика за {period_name}\n\n"
        text += f"💰 Общий профит: {int(stats['total']):,} ₽\n"
        text += f"📈 Количество профитов: {stats['count']}\n"
        text += f"👥 Активных пользователей: {stats['active_users']}\n"
        text += f"👤 Всего пользователей: {stats['total_users']}"
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button("admin_panel")
        )
        return
    
    # Статистика команды
    if data.startswith("team_stats_"):
        period = data.split("_")[-1]
        stats = await DatabaseOperations.get_team_statistics(db_user.id, period)
        
        period_name = {
            'day': 'день',
            'week': 'неделю',
            'month': 'месяц',
            'all': 'все время'
        }.get(period, 'все время')
        
        text = f"📊 Статистика команды за {period_name}\n\n"
        text += f"👥 Участников: {stats['members']}\n"
        text += f"💰 Общий профит: {int(stats['total']):,} ₽\n"
        text += f"📈 Количество профитов: {stats['count']}"
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button("back_to_main")
        )
        return
    
    # Топ пользователей
    if data == "admin_top":
        top_users = await DatabaseOperations.get_top_users(10)
        
        text = "🏆 Топ-10 пользователей\n\n"
        
        for idx, (user_obj, total) in enumerate(top_users, 1):
            emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            text += f"{emoji} @{user_obj.username or user_obj.telegram_id}\n"
            text += f"   💰 {int(total):,} ₽\n\n"
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button("admin_panel")
        )
        return
    
    # Логи действий
    if data == "admin_logs":
        logs = await DatabaseOperations.get_action_logs(limit=20)
        
        text = "📝 Последние действия\n\n"
        
        for log in logs:
            admin = await DatabaseOperations.get_user_by_id(log.admin_id)
            admin_name = admin.username if admin else "Unknown"
            time_str = log.created_at.strftime("%d.%m.%Y %H:%M")
            text += f"⏰ {time_str}\n"
            text += f"👤 @{admin_name}\n"
            text += f"📋 {log.description}\n\n"
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button("admin_panel")
        )
        return
    
    # Экспорт отчета
    if data == "admin_export":
        await query.answer("Генерирую отчет...")
        await export_report_command(update, context)
        return
    
    # Список пользователей
    if data == "manage_list_users":
        users = await DatabaseOperations.get_all_users()
        
        text = f"👥 Всего пользователей: {len(users)}\n\n"
        text += "Выберите пользователя для просмотра:"
        
        await query.edit_message_text(
            text,
            reply_markup=get_user_list_keyboard(users, "view")
        )
        return
    
    # Просмотр пользователя
    if data.startswith("view_user_"):
        user_id = int(data.split("_")[-1])
        target_user = await DatabaseOperations.get_user_by_id(user_id)
        
        if not target_user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        stats = await DatabaseOperations.get_user_statistics(target_user.id)
        
        text = f"👤 Информация о пользователе\n\n"
        text += f"🆔 ID: {target_user.telegram_id}\n"
        text += f"👤 Username: @{target_user.username or 'не указан'}\n"
        text += f"👔 Роль: {target_user.role}\n"
        text += f"💰 Профит: {int(stats['total']):,} ₽\n"
        text += f"📊 Профитов: {stats['count']}\n"
        
        if target_user.fake_tag:
            text += f"🏷 FakeTag: {target_user.fake_tag}\n"
        
        if target_user.mini_head_id:
            mini_head = await DatabaseOperations.get_user_by_id(target_user.mini_head_id)
            if mini_head:
                text += f"👨‍🏫 Наставник: @{mini_head.username or mini_head.telegram_id}\n"
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button("manage_list_users")
        )
        return
    
    # Назад в главное меню
    if data == "back_to_main":
        await query.message.delete()
        return
    
    await query.answer("⚠️ Функция в разработке")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Используйте /start для начала работы")
        return
    
    # Обработка действий
    if 'action' in context.user_data:
        action = context.user_data['action']
        
        # Добавление профита - шаг 1: получен ID пользователя
        if action == 'add_profit' and 'profit_user_id' not in context.user_data:
            try:
                target_telegram_id = int(text)
                target_user = await DatabaseOperations.get_user_by_telegram_id(target_telegram_id)
                
                if not target_user:
                    await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
                    return
                
                context.user_data['profit_user_id'] = target_user.id
                await update.message.reply_text(
                    f"✅ Пользователь найден: @{target_user.username or target_user.telegram_id}\n\n"
                    "Теперь отправьте сумму профита (в рублях):"
                )
                return
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID. Отправьте числовой ID:")
                return
        
        # Добавление профита - шаг 2: получена сумма
        if action == 'add_profit' and 'profit_user_id' in context.user_data:
            try:
                amount = float(text.replace(',', '.').replace(' ', ''))
                
                if amount <= 0:
                    await update.message.reply_text("❌ Сумма должна быть положительной. Попробуйте снова:")
                    return
                
                target_user_id = context.user_data['profit_user_id']
                await DatabaseOperations.add_profit(target_user_id, amount, db_user.id, bot=context.bot)
                
                target_user = await DatabaseOperations.get_user_by_id(target_user_id)
                
                # Отправляем уведомление пользователю
                notification_text = f"🎉 Поздравляем!\n\n"
                notification_text += f"Вам начислен профит: {format_number(amount)} ₽\n"
                notification_text += f"От: @{db_user.username or 'администратора'}"
                
                await send_notification(context.bot, target_user.telegram_id, notification_text)
                
                # Проверяем апгрейд статуса
                new_status = await DatabaseOperations.check_and_update_status(target_user_id, context.bot)
                
                await update.message.reply_text(
                    f"✅ Профит {format_number(amount)} ₽ успешно добавлен пользователю "
                    f"@{target_user.username or target_user.telegram_id}\n\n"
                    f"📨 Уведомление отправлено",
                    reply_markup=get_main_menu_keyboard(db_user.role)
                )
                
                # Очищаем контекст
                context.user_data.clear()
                return
            except ValueError:
                await update.message.reply_text("❌ Неверный формат суммы. Отправьте число:")
                return
    
    # Обработка кнопок меню
    if text == "👤 Профиль":
        await profile_command(update, context)
    elif text == "📚 Материалы":
        await materials_command(update, context)
    elif text == "👥 Моя команда":
        await my_team_command(update, context)
    elif text == "📊 Статистика":
        await statistics_command(update, context)
    elif text == "⚙️ Управление":
        await management_command(update, context)
    elif text == "🔧 Админ панель":
        await admin_panel_command(update, context)
    elif text == "📜 История профитов":
        await profit_history_command(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации",
            reply_markup=get_main_menu_keyboard(db_user.role)
        )


async def profit_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю профитов пользователя"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    # Получаем последние профиты
    profits = await DatabaseOperations.get_user_profits(db_user.id, limit=15)
    
    if not profits:
        await update.message.reply_text("📜 У вас пока нет профитов")
        return
    
    text = "📜 История профитов (последние 15)\n\n"
    
    for profit in profits:
        created_by = await DatabaseOperations.get_user_by_id(profit.created_by_id)
        text += f"💰 {format_number(profit.amount)} ₽\n"
        text += f"📅 {format_date(profit.created_at)}\n"
        text += f"👤 От: @{created_by.username if created_by else 'Unknown'}\n"
        if profit.description:
            text += f"📝 {profit.description}\n"
        text += "\n"
    
    await update.message.reply_text(text)


async def export_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт отчета в Excel"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    await update.message.reply_text("📊 Генерирую отчет... Пожалуйста, подождите.")
    
    try:
        # Head может экспортировать глобальный отчет
        if db_user.role == config.ROLE_HEAD:
            filepath = await ReportGenerator.generate_global_report()
            caption = "📊 Глобальный отчет по всей системе"
        
        # Mini Head может экспортировать отчет по своей команде
        elif db_user.role == config.ROLE_MINI_HEAD:
            filepath = await ReportGenerator.generate_team_report(db_user.id)
            caption = "👥 Отчет по вашей команде"
        
        # Worker может экспортировать свой личный отчет
        else:
            filepath = await ReportGenerator.generate_user_report(db_user.id)
            caption = "👤 Ваш личный отчет"
        
        # Отправляем файл
        with open(filepath, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=os.path.basename(filepath),
                caption=caption
            )
        
        # Удаляем файл после отправки
        os.remove(filepath)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации отчета: {str(e)}")


async def smart_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать умную аналитику"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    if db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await update.message.reply_text("❌ У вас нет доступа к этой функции")
        return
    
    await update.message.reply_text("📊 Анализирую данные...")
    
    try:
        if db_user.role == config.ROLE_MINI_HEAD:
            # Аналитика для команды Mini Head
            analytics = await AdvancedAnalytics.get_smart_analytics(mini_head_id=db_user.id)
            team_name = f"команды @{db_user.username or db_user.telegram_id}"
        else:
            # Глобальная аналитика для Head
            analytics = await AdvancedAnalytics.get_smart_analytics()
            team_name = "всей системы"
        
        text = AdvancedAnalytics.format_analytics_message(analytics, team_name)
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении аналитики: {str(e)}")


async def live_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Live Dashboard для Head"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role != config.ROLE_HEAD:
        await update.message.reply_text("❌ Эта функция доступна только для Head")
        return
    
    try:
        dashboard = await AdvancedAnalytics.get_live_dashboard()
        text = AdvancedAnalytics.format_live_dashboard(dashboard)
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def heads_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика по всем Mini Heads"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role != config.ROLE_HEAD:
        await update.message.reply_text("❌ Эта функция доступна только для Head")
        return
    
    try:
        heads_stats = await AdvancedAnalytics.get_heads_stats()
        
        if not heads_stats:
            await update.message.reply_text("📊 Пока нет Mini Heads")
            return
        
        text = "📊 Отчёт по Mini Head'ам:\n\n"
        
        for idx, stat in enumerate(heads_stats, 1):
            text += f"{idx}. @{stat['username']} — {format_number(stat['profit'])} ₽ "
            text += f"({stat['members']} участников)\n"
        
        # Лидер недели
        if heads_stats:
            leader = heads_stats[0]
            text += f"\n🏆 Лидер недели: @{leader['username']}"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def inactive_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка неактивных пользователей"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await update.message.reply_text("❌ У вас нет доступа к этой функции")
        return
    
    try:
        inactive = await AdvancedAnalytics.check_inactive_users(days=3)
        
        if not inactive:
            await update.message.reply_text("✅ Все пользователи активны!")
            return
        
        text = "⚠️ Неактивные пользователи:\n\n"
        
        for user_obj, mentor, days in inactive[:10]:  # Показываем первых 10
            text += f"👤 @{user_obj.username or user_obj.telegram_id}\n"
            text += f"⏰ Неактивен: {days} дней\n"
            if mentor:
                text += f"👨‍🏫 Наставник: @{mentor.username or mentor.telegram_id}\n"
            text += "\n"
        
        if len(inactive) > 10:
            text += f"... и ещё {len(inactive) - 10} пользователей"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def profit_chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить график профитов"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    await update.message.reply_text("📈 Генерирую график...")
    
    try:
        chart = await AdvancedAnalytics.generate_profit_chart(user_id=db_user.id, period_days=30)
        
        await update.message.reply_photo(
            photo=chart,
            caption="📈 График ваших профитов за последние 30 дней"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации графика: {str(e)}")


async def team_comparison_chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """График сравнения команд"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user or db_user.role != config.ROLE_HEAD:
        await update.message.reply_text("❌ Эта функция доступна только для Head")
        return
    
    await update.message.reply_text("📊 Генерирую график...")
    
    try:
        chart = await AdvancedAnalytics.generate_team_comparison_chart()
        
        await update.message.reply_photo(
            photo=chart,
            caption="📊 Сравнение команд Mini Heads за месяц"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации графика: {str(e)}")


async def quick_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрая статистика"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    stats = await DatabaseOperations.get_user_statistics(db_user.id)
    
    text = "📊 Быстрая статистика:\n\n"
    text += f"За день: {format_number(stats['day'])} ₽\n"
    text += f"За неделю: {format_number(stats['week'])} ₽\n"
    text += f"За месяц: {format_number(stats['month'])} ₽\n"
    text += f"Всего: {format_number(stats['total'])} ₽\n\n"
    
    # Тренд (упрощенно)
    if stats['month'] > 0 and stats['week'] > 0:
        weekly_avg = stats['week'] / 7
        monthly_avg = stats['month'] / 30
        if monthly_avg > 0:
            trend = ((weekly_avg - monthly_avg) / monthly_avg) * 100
            trend_emoji = "📈" if trend > 0 else "📉"
            text += f"{trend_emoji} Тренд: {trend:+.1f}% к среднему"
    
    await update.message.reply_text(text)
