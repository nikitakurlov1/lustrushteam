from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from voting import VotingSystem
from db_operations import DatabaseOperations
from utils import format_number
import config

# Состояния для создания голосования
POLL_TITLE, POLL_DESC, POLL_TYPE, POLL_OPTIONS, POLL_DURATION, POLL_TARGET = range(6)


async def polls_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню голосований"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
        return
    
    # Получаем активные голосования
    active_polls = await VotingSystem.get_active_polls()
    
    text = "🗳 **Голосования**\n\n"
    text += f"📢 Активных голосований: {len(active_polls)}\n\n"
    
    keyboard = []
    
    if active_polls:
        keyboard.append([InlineKeyboardButton("📢 Активные голосования", callback_data="polls_active")])
    
    keyboard.append([InlineKeyboardButton("📜 Завершённые", callback_data="polls_completed")])
    
    # Кнопка создания для Head и Mini Head
    if db_user.role in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        keyboard.append([InlineKeyboardButton("➕ Создать голосование", callback_data="poll_create")])
        keyboard.append([InlineKeyboardButton("⚙️ Управление", callback_data="polls_manage")])
    
    # Статистика участия
    stats = await VotingSystem.get_user_polls_stats(db_user.id)
    text += f"📊 Ваша активность: {stats['participated']} из {stats['total_active']} ({stats['activity_percent']:.0f}%)"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def show_active_polls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные голосования"""
    query = update.callback_query
    await query.answer()
    
    active_polls = await VotingSystem.get_active_polls()
    
    if not active_polls:
        await query.edit_message_text(
            "📢 Нет активных голосований",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="polls_menu")
            ]])
        )
        return
    
    text = "📢 Активные голосования:\n\n"
    
    keyboard = []
    for poll in active_polls[:10]:  # Показываем первые 10
        creator = await VotingSystem.get_poll_creator(poll.creator_id)
        creator_name = creator.username if creator else "Admin"
        
        text += f"🗳 {poll.title}\n"
        text += f"   От: @{creator_name}\n"
        if poll.end_at:
            text += f"   До: {poll.end_at.strftime('%d.%m.%Y')}\n"
        text += "\n"
        
        keyboard.append([InlineKeyboardButton(
            f"🗳 {poll.title[:30]}...",
            callback_data=f"poll_view_{poll.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="polls_menu")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def view_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр конкретного голосования"""
    query = update.callback_query
    await query.answer()
    
    poll_id = int(query.data.split("_")[-1])
    
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    poll = await VotingSystem.get_poll(poll_id)
    if not poll:
        await query.edit_message_text("❌ Голосование не найдено")
        return
    
    options = await VotingSystem.get_poll_options(poll_id)
    user_vote = await VotingSystem.get_user_vote(poll_id, db_user.id)
    
    text = VotingSystem.format_poll_message(poll, options, user_vote)
    
    keyboard = []
    
    # Если еще не голосовал, показываем кнопки для голосования
    if not user_vote and poll.is_active:
        for option in options:
            keyboard.append([InlineKeyboardButton(
                f"{option.option_order}️⃣ {option.option_text}",
                callback_data=f"vote_{poll_id}_{option.id}"
            )])
    
    # Кнопка результатов
    keyboard.append([InlineKeyboardButton("📊 Результаты", callback_data=f"poll_results_{poll_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="polls_active")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосования"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    poll_id = int(parts[1])
    option_id = int(parts[2])
    
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    # Голосуем
    success = await VotingSystem.vote(poll_id, db_user.id, option_id)
    
    if success:
        poll = await VotingSystem.get_poll(poll_id)
        option = await VotingSystem.get_poll_options(poll_id)
        voted_option = next((opt for opt in option if opt.id == option_id), None)
        
        await query.answer("✅ Ваш голос учтен!", show_alert=True)
        
        # Обновляем сообщение
        user_vote = await VotingSystem.get_user_vote(poll_id, db_user.id)
        text = VotingSystem.format_poll_message(poll, option, user_vote)
        
        keyboard = [
            [InlineKeyboardButton("📊 Результаты", callback_data=f"poll_results_{poll_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="polls_active")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.answer("❌ Вы уже голосовали!", show_alert=True)


async def show_poll_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты голосования"""
    query = update.callback_query
    await query.answer()
    
    poll_id = int(query.data.split("_")[-1])
    
    results_data = await VotingSystem.get_poll_results(poll_id)
    
    if not results_data:
        await query.edit_message_text("❌ Голосование не найдено")
        return
    
    text = VotingSystem.format_results_message(results_data)
    
    keyboard = [
        [InlineKeyboardButton("🗳 К голосованию", callback_data=f"poll_view_{poll_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="polls_active")]
    ]
    
    # Для создателя или Head - кнопка просмотра голосовавших
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    poll = results_data['poll']
    if db_user.role == config.ROLE_HEAD or db_user.id == poll.creator_id:
        if not poll.is_anonymous:
            keyboard.insert(0, [InlineKeyboardButton("👥 Кто голосовал", callback_data=f"poll_voters_{poll_id}")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def create_poll_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания голосования"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if db_user.role not in [config.ROLE_HEAD, config.ROLE_MINI_HEAD]:
        await query.answer("❌ У вас нет прав для создания голосований", show_alert=True)
        return
    
    await query.edit_message_text(
        "➕ **Создание голосования**\n\n"
        "Шаг 1/5: Введите название голосования:",
        parse_mode='Markdown'
    )
    
    return POLL_TITLE


async def top_voters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Топ самых активных голосующих"""
    top = await VotingSystem.get_top_voters(limit=10)
    
    if not top:
        await update.message.reply_text("📊 Пока нет данных о голосованиях")
        return
    
    text = "🔥 Топ голосующих:\n\n"
    
    for idx, (user, count) in enumerate(top, 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        text += f"{emoji} @{user.username or user.telegram_id} — {count} голосований\n"
    
    await update.message.reply_text(text)


async def my_polls_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика участия пользователя"""
    user = update.effective_user
    db_user = await DatabaseOperations.get_user_by_telegram_id(user.id)
    
    if not db_user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    stats = await VotingSystem.get_user_polls_stats(db_user.id)
    
    text = "📊 Ваша статистика голосований:\n\n"
    text += f"✅ Участвовали в: {stats['participated']} голосованиях\n"
    text += f"📢 Всего активных: {stats['total_active']}\n"
    text += f"📈 Средняя активность: {stats['activity_percent']:.0f}%\n"
    
    if stats['activity_percent'] == 100:
        text += "\n🏆 Отличная активность! Вы участвуете во всех голосованиях!"
    elif stats['activity_percent'] >= 80:
        text += "\n💪 Хорошая активность! Продолжайте в том же духе!"
    elif stats['activity_percent'] >= 50:
        text += "\n📊 Неплохо, но можно лучше!"
    else:
        text += "\n⚠️ Низкая активность. Участвуйте в голосованиях!"
    
    await update.message.reply_text(text)
