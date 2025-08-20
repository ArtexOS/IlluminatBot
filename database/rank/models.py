from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .connection import Base

class RankUser(Base):
    __tablename__ = 'rank_users'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer, default=0)

class NoXPChannel(Base):
    __tablename__ = 'no_xp_channels'

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)