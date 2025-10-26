from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from database import User, Profit, ActionLog, async_session_maker
import config
from telegram import Bot


class DatabaseOperations:
    
    @staticmethod
    async def get_or_create_user(telegram_id: int, username: Optional[str] = None) -> User:
        """Получить или создать пользователя"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    role=config.ROLE_WORKER
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            return user
    
    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user_role(user_id: int, new_role: str, admin_id: int) -> bool:
        """Обновить роль пользователя"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                old_role = user.role
                user.role = new_role
                
                # Логирование действия
                log = ActionLog(
                    admin_id=admin_id,
                    action_type='role_change',
                    description=f'Изменена роль пользователя {user.username or user.telegram_id} с {old_role} на {new_role}',
                    target_user_id=user.telegram_id
                )
                session.add(log)
                
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def assign_mini_head(worker_id: int, mini_head_id: int, admin_id: int) -> bool:
        """Назначить мини-хеда работнику"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == worker_id)
            )
            worker = result.scalar_one_or_none()
            
            if worker:
                worker.mini_head_id = mini_head_id
                
                # Логирование
                log = ActionLog(
                    admin_id=admin_id,
                    action_type='assign_mini_head',
                    description=f'Назначен мини-хед для пользователя {worker.username or worker.telegram_id}',
                    target_user_id=worker.telegram_id
                )
                session.add(log)
                
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def check_and_update_status(user_id: int, bot: Optional[Bot] = None) -> Optional[str]:
        """Проверить и обновить статус пользователя, вернуть новый статус если изменился"""
        async with async_session_maker() as session:
            # Получаем пользователя
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Получаем общую сумму профитов
            result = await session.execute(
                select(func.sum(Profit.amount)).where(Profit.user_id == user_id)
            )
            total_profit = result.scalar() or 0
            
            # Определяем новый статус
            new_status_data = user.get_status(total_profit)
            new_status = new_status_data['name']
            
            # Если статус изменился
            if user.current_status != new_status:
                old_status = user.current_status
                user.current_status = new_status
                await session.commit()
                
                # Отправляем уведомление с логотипом
                if bot:
                    from media import get_logo_file
                    emoji = new_status_data['emoji']
                    
                    # Отправляем логотип
                    logo = get_logo_file()
                    if logo:
                        caption = f"🎉 **LUST RUSH TEAM** 🎉\n\n"
                        caption += f"Поздравляем!\n"
                        caption += f"Вы достигли уровня {emoji} **{new_status}**!\n"
                        caption += f"Продолжайте в том же духе 💪\n\n"
                        caption += f"Ваш общий профит: {int(total_profit):,} ₽"
                        
                        await bot.send_photo(
                            chat_id=user.telegram_id,
                            photo=logo,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                        logo.close()
                
                return new_status
            
            return None
    
    @staticmethod
    async def add_profit(user_id: int, amount: float, admin_id: int, description: Optional[str] = None, bot: Optional[Bot] = None) -> Profit:
        """Добавить профит пользователю"""
        async with async_session_maker() as session:
            profit = Profit(
                user_id=user_id,
                amount=amount,
                description=description,
                created_by_id=admin_id
            )
            session.add(profit)
            
            # Логирование
            user = await DatabaseOperations.get_user_by_id(user_id)
            log = ActionLog(
                admin_id=admin_id,
                action_type='add_profit',
                description=f'Добавлен профит {amount} ₽ для пользователя {user.username if user else user_id}',
                target_user_id=user.telegram_id if user else None
            )
            session.add(log)
            
            await session.commit()
            await session.refresh(profit)
            return profit
    
    @staticmethod
    async def delete_profit(profit_id: int, admin_id: int) -> bool:
        """Удалить профит"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Profit).where(Profit.id == profit_id)
            )
            profit = result.scalar_one_or_none()
            
            if profit:
                user = await DatabaseOperations.get_user_by_id(profit.user_id)
                
                log = ActionLog(
                    admin_id=admin_id,
                    action_type='delete_profit',
                    description=f'Удален профит {profit.amount} ₽ у пользователя {user.username if user else profit.user_id}',
                    target_user_id=user.telegram_id if user else None
                )
                session.add(log)
                
                await session.delete(profit)
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def get_user_profits(user_id: int, limit: int = 20) -> List[Profit]:
        """Получить последние профиты пользователя"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Profit).where(Profit.user_id == user_id)
                .order_by(desc(Profit.created_at))
                .limit(limit)
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_user_statistics(user_id: int) -> Dict:
        """Получить статистику пользователя"""
        async with async_session_maker() as session:
            # Общая статистика
            result = await session.execute(
                select(
                    func.sum(Profit.amount).label('total'),
                    func.count(Profit.id).label('count'),
                    func.max(Profit.amount).label('max_profit'),
                    func.avg(Profit.amount).label('avg_profit')
                ).where(Profit.user_id == user_id)
            )
            stats = result.one()
            
            # За день
            day_ago = datetime.utcnow() - timedelta(days=1)
            result = await session.execute(
                select(func.sum(Profit.amount)).where(
                    and_(Profit.user_id == user_id, Profit.created_at >= day_ago)
                )
            )
            day_profit = result.scalar() or 0
            
            # За неделю
            week_ago = datetime.utcnow() - timedelta(days=7)
            result = await session.execute(
                select(func.sum(Profit.amount)).where(
                    and_(Profit.user_id == user_id, Profit.created_at >= week_ago)
                )
            )
            week_profit = result.scalar() or 0
            
            # За месяц
            month_ago = datetime.utcnow() - timedelta(days=30)
            result = await session.execute(
                select(func.sum(Profit.amount)).where(
                    and_(Profit.user_id == user_id, Profit.created_at >= month_ago)
                )
            )
            month_profit = result.scalar() or 0
            
            return {
                'total': stats.total or 0,
                'count': stats.count or 0,
                'max_profit': stats.max_profit or 0,
                'avg_profit': stats.avg_profit or 0,
                'day': day_profit,
                'week': week_profit,
                'month': month_profit
            }
    
    @staticmethod
    async def get_user_rank(user_id: int) -> int:
        """Получить место пользователя в рейтинге"""
        async with async_session_maker() as session:
            # Получаем сумму профитов для всех пользователей
            result = await session.execute(
                select(
                    Profit.user_id,
                    func.sum(Profit.amount).label('total')
                ).group_by(Profit.user_id).order_by(desc('total'))
            )
            rankings = result.all()
            
            for idx, (uid, _) in enumerate(rankings, 1):
                if uid == user_id:
                    return idx
            return 0
    
    @staticmethod
    async def get_all_users(role: Optional[str] = None) -> List[User]:
        """Получить всех пользователей, опционально по роли"""
        async with async_session_maker() as session:
            query = select(User).where(User.is_active == True)
            if role:
                query = query.where(User.role == role)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def get_mini_head_team(mini_head_id: int) -> List[User]:
        """Получить команду мини-хеда"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(
                    and_(User.mini_head_id == mini_head_id, User.is_active == True)
                )
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_team_statistics(mini_head_id: int, period: str = 'all') -> Dict:
        """Получить статистику команды мини-хеда"""
        async with async_session_maker() as session:
            # Получаем всех членов команды
            team_result = await session.execute(
                select(User.id).where(User.mini_head_id == mini_head_id)
            )
            team_ids = [row[0] for row in team_result.all()]
            
            if not team_ids:
                return {'total': 0, 'count': 0, 'members': 0}
            
            # Определяем период
            query = select(
                func.sum(Profit.amount).label('total'),
                func.count(Profit.id).label('count')
            ).where(Profit.user_id.in_(team_ids))
            
            if period == 'day':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=1))
            elif period == 'week':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=7))
            elif period == 'month':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=30))
            
            result = await session.execute(query)
            stats = result.one()
            
            return {
                'total': stats.total or 0,
                'count': stats.count or 0,
                'members': len(team_ids)
            }
    
    @staticmethod
    async def get_global_statistics(period: str = 'all') -> Dict:
        """Получить глобальную статистику"""
        async with async_session_maker() as session:
            query = select(
                func.sum(Profit.amount).label('total'),
                func.count(Profit.id).label('count'),
                func.count(func.distinct(Profit.user_id)).label('active_users')
            )
            
            if period == 'day':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=1))
            elif period == 'week':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=7))
            elif period == 'month':
                query = query.where(Profit.created_at >= datetime.utcnow() - timedelta(days=30))
            
            result = await session.execute(query)
            stats = result.one()
            
            # Общее количество пользователей
            total_users_result = await session.execute(
                select(func.count(User.id)).where(User.is_active == True)
            )
            total_users = total_users_result.scalar()
            
            return {
                'total': stats.total or 0,
                'count': stats.count or 0,
                'active_users': stats.active_users or 0,
                'total_users': total_users or 0
            }
    
    @staticmethod
    async def get_top_users(limit: int = 10) -> List[Tuple[User, float]]:
        """Получить топ пользователей по профитам"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(
                    User,
                    func.sum(Profit.amount).label('total')
                ).join(Profit).group_by(User.id).order_by(desc('total')).limit(limit)
            )
            return result.all()
    
    @staticmethod
    async def get_action_logs(admin_id: Optional[int] = None, limit: int = 50) -> List[ActionLog]:
        """Получить логи действий"""
        async with async_session_maker() as session:
            query = select(ActionLog).order_by(desc(ActionLog.created_at)).limit(limit)
            
            if admin_id:
                query = query.where(ActionLog.admin_id == admin_id)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def deactivate_user(user_id: int, admin_id: int) -> bool:
        """Деактивировать пользователя"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.is_active = False
                
                log = ActionLog(
                    admin_id=admin_id,
                    action_type='deactivate_user',
                    description=f'Деактивирован пользователь {user.username or user.telegram_id}',
                    target_user_id=user.telegram_id
                )
                session.add(log)
                
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def set_fake_tag(user_id: int, fake_tag: str, admin_id: int) -> bool:
        """Установить FakeTag пользователю"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.fake_tag = fake_tag
                
                log = ActionLog(
                    admin_id=admin_id,
                    action_type='set_fake_tag',
                    description=f'Установлен FakeTag {fake_tag} для пользователя {user.username or user.telegram_id}',
                    target_user_id=user.telegram_id
                )
                session.add(log)
                
                await session.commit()
                return True
            return False
