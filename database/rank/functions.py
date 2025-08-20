from sqlalchemy import select, delete
from .connection import get_session
from .models import RankUser, NoXPChannel


class RankDatabase:
    async def get_user(self, user_id: int) -> RankUser | None:
        async with get_session() as session:
            return await session.get(RankUser, user_id)

    async def update_user_xp(self, user_id: int, xp_to_add: int) -> tuple[RankUser | None, bool]:
        async with get_session() as session:
            result = await session.execute(select(RankUser).filter_by(user_id=user_id))
            user = result.scalar_one_or_none()

            if not user:
                user = RankUser(user_id=user_id)
                session.add(user)

            user.xp += xp_to_add

            leveled_up = False
            xp_needed = (user.level + 1) * 100

            if user.xp >= xp_needed:
                user.level += 1
                user.xp -= xp_needed
                leveled_up = True

            await session.commit()
            await session.refresh(user)

            return user, leveled_up

    async def set_user_rank(self, user_id: int, level: int | None = None, xp: int | None = None) -> RankUser:
        async with get_session() as session:
            result = await session.execute(select(RankUser).filter_by(user_id=user_id))
            user = result.scalar_one_or_none()
            if not user:
                user = RankUser(user_id=user_id)
                session.add(user)

            if level is not None:
                user.level = level
            if xp is not None:
                user.xp = xp

            await session.commit()
            await session.refresh(user)
            return user

    async def get_top_users(self, limit: int = 10):
        async with get_session() as session:
            query = select(RankUser).order_by(RankUser.level.desc(), RankUser.xp.desc()).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_no_xp_channels(self) -> set[int]:
        async with get_session() as session:
            query = select(NoXPChannel.channel_id)
            result = await session.execute(query)
            return set(result.scalars().all())

    async def add_no_xp_channel(self, channel_id: int) -> bool:
        async with get_session() as session:
            result = await session.execute(select(NoXPChannel).filter_by(channel_id=channel_id))
            if result.scalar_one_or_none():
                return False

            new_channel = NoXPChannel(channel_id=channel_id)
            session.add(new_channel)
            await session.commit()
            return True

    async def remove_no_xp_channel(self, channel_id: int) -> bool:
        async with get_session() as session:
            result = await session.execute(delete(NoXPChannel).where(NoXPChannel.channel_id == channel_id))
            await session.commit()
            return result.rowcount > 0