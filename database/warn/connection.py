import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database.warn.models import Base

# Получаем все значение из .env
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/{POSTGRES_DB}"
)

# Создаём движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаём фабрику сессий, через которую делаются запросы.
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Функция создаёт все таблицы по моделям
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Контекстный менеджер для получения сессии. Он сам откроет и закроет соединение.
@asynccontextmanager
async def get_session():
    async with async_session_maker() as session:
        yield session