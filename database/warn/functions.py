from sqlalchemy import select, delete
from database.warn.connection import get_session
from database.warn.models import Warn
import datetime

class Database:

    async def get_warns(self, user_id: int):
        """Получает все предупреждения пользователя."""
        async with get_session() as session:
            query = select(Warn).filter_by(user_id=user_id)
            result = await session.execute(query)
            return result.scalars().all()

    async def add_warn(self, user_id: int, moderator_id: int, reason: str, start_time: datetime.datetime):
        """Добавляет новое предупреждение."""
        async with get_session() as session:
            session.add(Warn(
                user_id=user_id,
                moderator_id=moderator_id,
                reason=reason,
                start_time=start_time,
            ))
            await session.commit()

    async def remove_warn_by_id(self, warn_id: int):
        """Удаляет предупреждение по его уникальному ID."""
        async with get_session() as session:
            query = delete(Warn).where(Warn.id == warn_id)
            await session.execute(query)
            await session.commit()

    async def remove_all_warns(self, user_id: int):
        """Удаляет все предупреждения пользователя."""
        async with get_session() as session:
            query = delete(Warn).where(Warn.user_id == user_id)
            await session.execute(query)
            await session.commit()