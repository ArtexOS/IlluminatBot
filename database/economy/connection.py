import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager

# --- НАСТРОЙКА ---
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/{POSTGRES_DB}"
)
# -----------------

# Создаем асинхронный "движок" для взаимодействия с БД
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий, через которую будем делать запросы
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Базовый класс для всех наших моделей (таблиц)
class Base(AsyncAttrs, DeclarativeBase):
    pass

@asynccontextmanager
async def get_session():
    """Асинхронный менеджер контекста для получения сессии."""
    async with async_session() as session:
        yield session

async def create_tables():
    """Создает все таблицы в базе данных, если их еще нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)