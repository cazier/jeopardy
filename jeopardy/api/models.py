import typing
import datetime

from sqlalchemy import Date as DateType
from sqlalchemy import String, Boolean, Integer, ForeignKey, ColumnElement, event, extract
from sqlalchemy.orm import Mapped, Session, DeclarativeBase, synonym, relationship, mapped_column
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import Comparator, hybrid_property

db = SQLAlchemy()


class Base(DeclarativeBase):
    @staticmethod
    def valid_inputs(*args, **kwargs) -> str:
        return ""


class Set(Base):
    __tablename__ = "set"

    id: Mapped[int] = mapped_column(primary_key=True, info={"serialize": int})

    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"), nullable=False)
    show_id: Mapped[int] = mapped_column(ForeignKey("show.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)
    value_id: Mapped[int] = mapped_column(ForeignKey("value.id"), nullable=False)

    category: Mapped["Category"] = relationship(back_populates="sets", info={"serialize": lambda k: k.name})
    date: Mapped["Date"] = relationship(back_populates="sets", info={"serialize": lambda k: k.date.isoformat()})
    show: Mapped["Show"] = relationship(back_populates="sets", info={"serialize": lambda k: k.number})
    round: Mapped["Round"] = relationship(back_populates="sets", info={"serialize": lambda k: k.number})
    value: Mapped["Value"] = relationship(back_populates="sets", info={"serialize": lambda k: k.amount})

    external: Mapped[bool] = mapped_column(Boolean, nullable=False, info={"serialize": bool})
    complete: Mapped[bool] = synonym("_complete", info={"serialize": bool})
    hash: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    answer: Mapped[str] = mapped_column(String(1000), info={"serialize": str})
    question: Mapped[str] = mapped_column(String(255), info={"serialize": str})

    def __repr__(self) -> str:
        return f"<Set {self.id}, (Hash={self.hash})>"

    @hybrid_property
    def _complete(self) -> bool:
        return self.category.complete if self.category else False


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True, info={"serialize": int})

    name: Mapped[str] = mapped_column(String(100), info={"serialize": str})

    show_id: Mapped[int] = mapped_column(ForeignKey("show.id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)

    show: Mapped["Show"] = relationship(back_populates="categories", info={"serialize": lambda k: k.number})
    date: Mapped["Date"] = relationship(back_populates="categories", info={"serialize": lambda k: k.date.isoformat()})
    round: Mapped["Round"] = relationship(back_populates="categories", info={"serialize": lambda k: k.number})

    complete: Mapped[bool] = mapped_column(Boolean, nullable=False, info={"serialize": bool})
    sets: Mapped[list[Set]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Date(Base):
    __tablename__ = "date"

    id: Mapped[int] = mapped_column(primary_key=True)

    date: Mapped[datetime.date] = mapped_column(DateType, info={"serialize": lambda k: k.isoformat()})
    sets: Mapped[list[Set]] = relationship("Set", back_populates="date")
    shows: Mapped["Show"] = relationship("Show", back_populates="date")
    categories: Mapped[Category] = relationship("Category", back_populates="date")

    @hybrid_property
    def _year(self) -> int:
        return self.date.year

    @_year.expression
    @classmethod
    def year(cls) -> ColumnElement[int]:
        return extract("year", cls.date)

    @hybrid_property
    def _month(self) -> int:
        return self.date.month

    @_month.expression
    @classmethod
    def month(cls) -> ColumnElement[int]:
        return extract("month", cls.date)

    @hybrid_property
    def _day(self) -> int:
        return self.date.day

    @_day.expression
    @classmethod
    def day(cls) -> ColumnElement[int]:
        return extract("day", cls.date)

    # @hybrid_property
    # def _date(self) -> datetime.Date:
    #     return self.date

    # @_date.inplace.comparator(Comparator[datetime.date])

    def __repr__(self) -> str:
        return f"<Date {self.date}>"


class Show(Base):
    __tablename__ = "show"

    id: Mapped[int] = mapped_column(primary_key=True, info={"serialize": int})

    number: Mapped[int] = mapped_column(Integer, info={"serialize": int})
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"))

    date: Mapped["Date"] = relationship(back_populates="shows", info={"serialize": lambda k: k.date.isoformat()})

    sets: Mapped[list[Set]] = relationship("Set", back_populates="show")
    categories: Mapped[list[Category]] = relationship("Category", back_populates="show")

    def __repr__(self) -> str:
        return f"<Show {self.number}>"


class Round(Base):
    __tablename__ = "round"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer, info={"serialize": int})
    sets: Mapped[list[Set]] = relationship("Set", back_populates="round")
    categories: Mapped[list[Category]] = relationship("Category", back_populates="round")
    values: Mapped["Value"] = relationship("Value", back_populates="round")

    def __repr__(self) -> str:
        return f"<Round {self.number}>"

    @staticmethod
    def valid_inputs(*, number: int, **kwargs) -> tuple:
        if 0 <= number <= 2:
            return ""

        return "the round must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)"


class Value(Base):
    __tablename__ = "value"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, info={"serialize": int})
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)

    round: Mapped["Round"] = relationship(back_populates="values")

    sets: Mapped[list[Set]] = relationship("Set", back_populates="value")

    def __repr__(self) -> str:
        return f"<Value {self.amount}>"


class NoResultFound:
    def __getattr__(self, name: str) -> None:
        return None


NoResultFoundSentinel = NoResultFound()


def or_zero(scalar: int | None) -> int:
    return 0 if scalar is None else scalar


Q = typing.TypeVar("Q", Set, Category, Date, Show, Round, Value, NoResultFound)
M: typing.TypeAlias = type[Set | Category | Date | Show | Round | Value]


def or_none(scalar: Q | None) -> Q | NoResultFound:
    return NoResultFoundSentinel if scalar is None else scalar
