import typing
import datetime
import functools
import dataclasses

from sqlalchemy import Column, String, Boolean, Integer, ClauseList, ForeignKey, ColumnElement, and_, desc, false
from sqlalchemy.orm import Mapped, DeclarativeBase, CompositeProperty, synonym, composite, relationship, mapped_column
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.elements import UnaryExpression

db = SQLAlchemy()


class Base(DeclarativeBase):
    @staticmethod
    def valid_inputs(*args: typing.Any, **kwargs: dict[str, typing.Any]) -> str:
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


@dataclasses.dataclass(order=True)
class _Date:
    year: int
    month: int
    day: int

    def isoformat(self) -> str:
        return f"{self.year:04}-{self.month:02}-{self.day:02}"

    def as_date(self) -> datetime.date:
        return datetime.date(year=self.year, month=self.month, day=self.day)


class _DateComparator(CompositeProperty.Comparator[bool]):
    @functools.cached_property
    def columns(self) -> dict[str, Column[_Date]]:
        return {column.key: column for column in self.__clause_element__().clauses}

    def __eq__(self, obj: typing.Any) -> ColumnElement[bool]:  # type: ignore[override]
        if isinstance(obj, (datetime.date, datetime.datetime)):
            obj = {"year": obj.year, "month": obj.month, "day": obj.day}

        if isinstance(obj, dict):
            if "start" in obj:
                return and_(obj["start"] <= self.columns["year"], self.columns["year"] <= obj["stop"])

            return and_(
                *[
                    obj[key.name] == self.columns[key.name]
                    for key in dataclasses.fields(_Date)
                    if obj.get(key.name, -1) >= 0
                ]
            )

        return false()

    def desc(self) -> UnaryExpression[bool]:
        return ClauseList(desc("year"), desc("month"), desc("day"))  # type: ignore[return-value]


class Date(Base):
    __tablename__ = "date"

    id: Mapped[int] = mapped_column(primary_key=True)

    date: Mapped[_Date] = composite(
        mapped_column("year"),
        mapped_column("month"),
        mapped_column("day"),
        comparator_factory=_DateComparator,
        info={"serialize": lambda k: k.isoformat()},
    )
    sets: Mapped[list[Set]] = relationship("Set", back_populates="date")
    shows: Mapped["Show"] = relationship("Show", back_populates="date")
    categories: Mapped[Category] = relationship("Category", back_populates="date")

    @staticmethod
    def valid_inputs(  # type: ignore[override]
        *,
        start: typing.Optional[int] = None,
        stop: typing.Optional[int] = None,
        year: typing.Optional[int] = None,
        month: typing.Optional[int] = None,
        day: typing.Optional[int] = None,
        **kwargs: dict[str, typing.Any],
    ) -> str:
        if start is not None and stop is not None:
            if start > stop:
                return "The stop year must come after the starting year."

            if not (1 <= start <= 9999) or not (1 <= stop <= 9999):
                return "The year range must be between 0001 and 9999."

            return ""

        try:
            month, day = month or 1, day or 1
            datetime.datetime.strptime(f"{year:04d}/{abs(month):02d}/{abs(day):02d}", "%Y/%m/%d")

        except ValueError:
            return "That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)."

        return ""

    def __repr__(self) -> str:
        return f"<Date {self.date.isoformat()}>"


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
    def valid_inputs(*, number: int, **kwargs: dict[str, typing.Any]) -> str:  # type: ignore[override]
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


Q = typing.TypeVar("Q", Set, Category, Date, Show, Round, Value)
N = typing.TypeVar("N", Set, Category, Date, Show, Round, Value, NoResultFound)
M: typing.TypeAlias = type[Set | Category | Date | Show | Round | Value]


def or_none(scalar: N | None) -> N | NoResultFound:
    return NoResultFoundSentinel if scalar is None else scalar
