import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager

POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:5432/{POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        yield session

async def create_rank_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)