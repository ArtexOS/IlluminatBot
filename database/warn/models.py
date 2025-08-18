import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, DateTime

class Base(DeclarativeBase):
    pass

class Warn(Base):
    __tablename__ = 'warns'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    moderator_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)