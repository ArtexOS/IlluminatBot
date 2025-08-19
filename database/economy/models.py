from sqlalchemy import BigInteger, String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .connection import Base

class User(Base):
    __tablename__ = 'economy_users'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cash: Mapped[int] = mapped_column(BigInteger, default=0)
    bank: Mapped[int] = mapped_column(BigInteger, default=0)

    last_daily: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    last_work: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    last_steal: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    last_collect: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    businesses: Mapped[list["UserBusiness"]] = relationship(back_populates="owner")

    @property
    def total(self) -> int:
        return self.cash + self.bank

class Business(Base):
    __tablename__ = 'businesses'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    price: Mapped[int] = mapped_column(BigInteger)
    income: Mapped[int] = mapped_column(BigInteger)
    limit: Mapped[int] = mapped_column(Integer, default=1)

class UserBusiness(Base):
    __tablename__ = 'user_businesses'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('economy_users.user_id'))
    business_id: Mapped[int] = mapped_column(Integer, ForeignKey('businesses.id'))

    owner: Mapped["User"] = relationship(back_populates="businesses")
    business_info: Mapped["Business"] = relationship()