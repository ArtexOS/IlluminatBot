from sqlalchemy import select, func, delete, exists, update
from sqlalchemy.orm import selectinload
from .connection import get_session
from .models import User, Business, UserBusiness
from datetime import datetime

class Database:
    async def update_balance(self, user_id: int, cash_delta: int = 0, bank_delta: int = 0):
        async with get_session() as session:
            result = await session.execute(select(User).filter_by(user_id=user_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(user_id=user_id, cash=500, bank=0)
                session.add(user)
            user.cash += cash_delta
            user.bank += bank_delta
            await session.commit()

    async def get_user(self, user_id: int) -> User | None:
        async with get_session() as session:
            return await session.get(User, user_id)

    async def update_cooldown(self, user_id: int, command_name: str):
        async with get_session() as session:
            user_exists = await session.get(User, user_id)
            if not user_exists:
                await self.update_balance(user_id)

            stmt = (
                update(User)
                .where(User.user_id == user_id)
                .values({command_name: datetime.utcnow()})
            )
            await session.execute(stmt)
            await session.commit()

    async def get_top_users(self, limit: int = 10):
        async with get_session() as session:
            query = select(User).order_by((User.cash + User.bank).desc()).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    async def add_business(self, name: str, price: int, income: int, limit: int) -> bool:
        async with get_session() as session:
            query = select(exists().where(Business.name == name))
            business_exists = await session.scalar(query)
            if business_exists:
                return False
            new_business = Business(name=name, price=price, income=income, limit=limit)
            session.add(new_business)
            await session.commit()
            return True

    async def get_all_businesses(self):
        async with get_session() as session:
            result = await session.execute(select(Business))
            return result.scalars().all()

    async def get_business_by_id(self, business_id: int) -> Business | None:
        async with get_session() as session:
            return await session.get(Business, business_id)

    async def count_owned_businesses(self, business_id: int) -> int:
        async with get_session() as session:
            query = select(func.count()).select_from(UserBusiness).filter_by(business_id=business_id)
            result = await session.scalar(query)
            return result or 0

    async def purchase_business(self, user_id: int, business_id: int):
        async with get_session() as session:
            user_business = UserBusiness(user_id=user_id, business_id=business_id)
            session.add(user_business)
            await session.commit()

    async def get_user_businesses(self, user_id: int):
        async with get_session() as session:
            query = (
                select(UserBusiness)
                .options(selectinload(UserBusiness.business_info))
                .filter_by(user_id=user_id)
            )
            result = await session.execute(query)
            return result.scalars().all()

    async def get_user_business_by_id(self, user_business_id: int) -> UserBusiness | None:
        async with get_session() as session:
            query = (
                select(UserBusiness)
                .options(selectinload(UserBusiness.business_info))
                .where(UserBusiness.id == user_business_id)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def sell_business(self, user_business_id: int):
        async with get_session() as session:
            await session.execute(delete(UserBusiness).where(UserBusiness.id == user_business_id))
            await session.commit()