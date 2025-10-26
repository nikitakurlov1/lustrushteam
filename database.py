from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, BigInteger, Float, DateTime, ForeignKey, Text, select, func
from datetime import datetime
from typing import List, Optional
import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default=config.ROLE_WORKER)
    fake_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mini_head_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    current_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default='Новичок')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Relationships
    profits: Mapped[List["Profit"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    mini_head: Mapped[Optional["User"]] = relationship("User", remote_side=[id], foreign_keys=[mini_head_id])
    action_logs: Mapped[List["ActionLog"]] = relationship(back_populates="admin", foreign_keys="ActionLog.admin_id")
    
    def get_status(self, total_profit: float) -> dict:
        """Определяет статус пользователя по сумме профитов"""
        status = config.STATUS_LEVELS[0]
        for threshold, level in sorted(config.STATUS_LEVELS.items(), reverse=True):
            if total_profit >= threshold:
                status = level
                break
        return status
    
    def get_status_by_count(self, profit_count: int) -> str:
        """Определяет статус пользователя по количеству профитов (старая система)"""
        status = config.STATUS_BY_COUNT[0]
        for threshold, level in sorted(config.STATUS_BY_COUNT.items(), reverse=True):
            if profit_count >= threshold:
                status = level
                break
        return status


class Profit(Base):
    __tablename__ = 'profits'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="profits", foreign_keys=[user_id])
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])


class ActionLog(Base):
    __tablename__ = 'action_logs'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    action_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    target_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    admin: Mapped["User"] = relationship(back_populates="action_logs", foreign_keys=[admin_id])


class Poll(Base):
    __tablename__ = 'polls'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    poll_type: Mapped[str] = mapped_column(String(50), default='single')  # single, multi, rating, anonymous, battle
    is_anonymous: Mapped[bool] = mapped_column(default=False)
    target_group: Mapped[str] = mapped_column(String(50), default='all')  # all, team, role
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID команды или роли
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    allow_comments: Mapped[bool] = mapped_column(default=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    options: Mapped[List["PollOption"]] = relationship(back_populates="poll", cascade="all, delete-orphan")
    votes: Mapped[List["PollVote"]] = relationship(back_populates="poll", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = 'poll_options'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey('polls.id'), index=True)
    option_text: Mapped[str] = mapped_column(String(255))
    option_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    poll: Mapped["Poll"] = relationship(back_populates="options")
    votes: Mapped[List["PollVote"]] = relationship(back_populates="option", cascade="all, delete-orphan")


class PollVote(Base):
    __tablename__ = 'poll_votes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey('polls.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey('poll_options.id'), index=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    poll: Mapped["Poll"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship()
    option: Mapped["PollOption"] = relationship(back_populates="votes")


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Получить сессию базы данных"""
    async with async_session_maker() as session:
        yield session
