from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from database import Poll, PollOption, PollVote, User, async_session_maker
from telegram import Bot
import config


class VotingSystem:
    
    @staticmethod
    async def create_poll(
        creator_id: int,
        title: str,
        description: Optional[str],
        options: List[str],
        poll_type: str = 'single',
        is_anonymous: bool = False,
        target_group: str = 'all',
        target_id: Optional[int] = None,
        end_days: int = 3,
        allow_comments: bool = False,
        reward_points: int = 0
    ) -> Poll:
        """Создать новое голосование"""
        async with async_session_maker() as session:
            # Создаем голосование
            poll = Poll(
                creator_id=creator_id,
                title=title,
                description=description,
                poll_type=poll_type,
                is_anonymous=is_anonymous,
                target_group=target_group,
                target_id=target_id,
                end_at=datetime.utcnow() + timedelta(days=end_days),
                allow_comments=allow_comments,
                reward_points=reward_points
            )
            session.add(poll)
            await session.flush()
            
            # Создаем варианты ответов
            for idx, option_text in enumerate(options, 1):
                option = PollOption(
                    poll_id=poll.id,
                    option_text=option_text,
                    option_order=idx
                )
                session.add(option)
            
            await session.commit()
            await session.refresh(poll)
            
            return poll
    
    @staticmethod
    async def get_poll(poll_id: int) -> Optional[Poll]:
        """Получить голосование по ID"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Poll).where(Poll.id == poll_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active_polls(user_id: Optional[int] = None, target_group: Optional[str] = None) -> List[Poll]:
        """Получить активные голосования"""
        async with async_session_maker() as session:
            query = select(Poll).where(
                and_(
                    Poll.is_active == True,
                    or_(Poll.end_at.is_(None), Poll.end_at > datetime.utcnow())
                )
            ).order_by(desc(Poll.created_at))
            
            if target_group:
                query = query.where(Poll.target_group == target_group)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def get_poll_options(poll_id: int) -> List[PollOption]:
        """Получить варианты ответов"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(PollOption).where(PollOption.poll_id == poll_id)
                .order_by(PollOption.option_order)
            )
            return result.scalars().all()
    
    @staticmethod
    async def vote(poll_id: int, user_id: int, option_id: int, comment: Optional[str] = None) -> bool:
        """Проголосовать"""
        async with async_session_maker() as session:
            # Проверяем, не голосовал ли уже
            existing_vote = await session.execute(
                select(PollVote).where(
                    and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id)
                )
            )
            if existing_vote.scalar_one_or_none():
                return False  # Уже голосовал
            
            # Создаем голос
            vote = PollVote(
                poll_id=poll_id,
                user_id=user_id,
                option_id=option_id,
                comment=comment
            )
            session.add(vote)
            await session.commit()
            
            return True
    
    @staticmethod
    async def get_user_vote(poll_id: int, user_id: int) -> Optional[PollVote]:
        """Получить голос пользователя"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(PollVote).where(
                    and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id)
                )
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_poll_results(poll_id: int) -> Dict:
        """Получить результаты голосования"""
        async with async_session_maker() as session:
            # Получаем голосование
            poll_result = await session.execute(
                select(Poll).where(Poll.id == poll_id)
            )
            poll = poll_result.scalar_one_or_none()
            
            if not poll:
                return {}
            
            # Получаем варианты
            options_result = await session.execute(
                select(PollOption).where(PollOption.poll_id == poll_id)
                .order_by(PollOption.option_order)
            )
            options = options_result.scalars().all()
            
            # Подсчитываем голоса
            total_votes = 0
            results = []
            
            for option in options:
                votes_count = await session.execute(
                    select(func.count(PollVote.id)).where(PollVote.option_id == option.id)
                )
                count = votes_count.scalar() or 0
                total_votes += count
                
                results.append({
                    'option_id': option.id,
                    'option_text': option.option_text,
                    'votes': count
                })
            
            # Рассчитываем проценты
            for result in results:
                if total_votes > 0:
                    result['percentage'] = (result['votes'] / total_votes) * 100
                else:
                    result['percentage'] = 0
            
            return {
                'poll': poll,
                'results': results,
                'total_votes': total_votes
            }
    
    @staticmethod
    async def get_poll_voters(poll_id: int, option_id: Optional[int] = None) -> List[Tuple[User, PollVote]]:
        """Получить список проголосовавших"""
        async with async_session_maker() as session:
            query = select(User, PollVote).join(
                PollVote, User.id == PollVote.user_id
            ).where(PollVote.poll_id == poll_id)
            
            if option_id:
                query = query.where(PollVote.option_id == option_id)
            
            result = await session.execute(query)
            return result.all()
    
    @staticmethod
    async def close_poll(poll_id: int) -> bool:
        """Закрыть голосование"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Poll).where(Poll.id == poll_id)
            )
            poll = result.scalar_one_or_none()
            
            if poll:
                poll.is_active = False
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def delete_poll(poll_id: int) -> bool:
        """Удалить голосование"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Poll).where(Poll.id == poll_id)
            )
            poll = result.scalar_one_or_none()
            
            if poll:
                await session.delete(poll)
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def get_user_polls_stats(user_id: int) -> Dict:
        """Получить статистику участия пользователя в голосованиях"""
        async with async_session_maker() as session:
            # Количество голосований, в которых участвовал
            participated_result = await session.execute(
                select(func.count(func.distinct(PollVote.poll_id)))
                .where(PollVote.user_id == user_id)
            )
            participated = participated_result.scalar() or 0
            
            # Всего активных голосований
            total_result = await session.execute(
                select(func.count(Poll.id)).where(Poll.is_active == True)
            )
            total = total_result.scalar() or 0
            
            # Процент активности
            activity = (participated / total * 100) if total > 0 else 0
            
            return {
                'participated': participated,
                'total_active': total,
                'activity_percent': activity
            }
    
    @staticmethod
    async def get_top_voters(limit: int = 10) -> List[Tuple[User, int]]:
        """Получить топ самых активных голосующих"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(
                    User,
                    func.count(func.distinct(PollVote.poll_id)).label('poll_count')
                ).join(PollVote, User.id == PollVote.user_id)
                .group_by(User.id)
                .order_by(desc('poll_count'))
                .limit(limit)
            )
            return result.all()
    
    @staticmethod
    def format_poll_message(poll: Poll, options: List[PollOption], user_vote: Optional[PollVote] = None) -> str:
        """Форматировать сообщение с голосованием"""
        text = f"🗳 Голосование: {poll.title}\n\n"
        
        if poll.description:
            text += f"{poll.description}\n\n"
        
        text += f"📅 Дата начала: {poll.created_at.strftime('%d.%m.%Y')}\n"
        
        if poll.end_at:
            text += f"📅 Завершение: {poll.end_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        # Тип голосования
        type_emoji = {
            'single': '🗳',
            'multi': '🧮',
            'rating': '🔢',
            'anonymous': '🧠',
            'battle': '⚔️'
        }.get(poll.poll_type, '🗳')
        
        text += f"{type_emoji} Тип: {poll.poll_type}\n"
        
        if poll.is_anonymous:
            text += "🔒 Анонимное голосование\n"
        
        text += "\nВарианты:\n"
        
        for idx, option in enumerate(options, 1):
            emoji = f"{idx}️⃣"
            text += f"{emoji} {option.option_text}\n"
        
        text += "\n"
        
        if user_vote:
            voted_option = next((opt for opt in options if opt.id == user_vote.option_id), None)
            if voted_option:
                text += f"✅ Вы проголосовали за: \"{voted_option.option_text}\"\n"
                text += "🔒 Изменить нельзя\n"
        else:
            text += "🗳 Ваш выбор: — (ещё не голосовали)\n"
        
        if poll.reward_points > 0:
            text += f"\n💰 Награда за участие: +{poll.reward_points} к рейтингу"
        
        return text
    
    @staticmethod
    def format_results_message(results_data: Dict, show_voters: bool = False) -> str:
        """Форматировать сообщение с результатами"""
        poll = results_data['poll']
        results = results_data['results']
        total_votes = results_data['total_votes']
        
        text = f"📊 Результаты голосования:\n\"{poll.title}\"\n\n"
        
        for idx, result in enumerate(results, 1):
            emoji = f"{idx}️⃣"
            votes = result['votes']
            percentage = result['percentage']
            
            # Прогресс-бар
            filled = int(percentage / 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            text += f"{emoji} {result['option_text']}\n"
            text += f"   {bar} {votes} голосов ({percentage:.1f}%)\n\n"
        
        text += f"🧑‍💻 Всего проголосовало: {total_votes}"
        
        if poll.end_at:
            if datetime.utcnow() > poll.end_at:
                text += "\n\n✅ Голосование завершено"
            else:
                remaining = poll.end_at - datetime.utcnow()
                hours = int(remaining.total_seconds() / 3600)
                text += f"\n\n⏰ Осталось: {hours} часов"
        
        return text
    
    @staticmethod
    async def notify_new_poll(bot: Bot, poll: Poll, target_users: List[int]):
        """Отправить уведомления о новом голосовании"""
        from utils import send_notification
        
        creator = await VotingSystem.get_poll_creator(poll.creator_id)
        creator_name = creator.username if creator else "Admin"
        
        message = f"📢 Новое голосование от @{creator_name}\n\n"
        message += f"\"{poll.title}\"\n\n"
        
        if poll.end_at:
            message += f"Голосуйте до {poll.end_at.strftime('%d.%m')}!\n"
        
        message += f"\nИспользуйте /polls для просмотра"
        
        for user_id in target_users:
            await send_notification(bot, user_id, message)
    
    @staticmethod
    async def get_poll_creator(creator_id: int) -> Optional[User]:
        """Получить создателя голосования"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == creator_id)
            )
            return result.scalar_one_or_none()
