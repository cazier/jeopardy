import datetime

from sqlalchemy import Date, String, Boolean, Integer, ForeignKey, extract
from sqlalchemy.orm import Mapped, DeclarativeBase, relationship, mapped_column
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()
session = db.session


class Base(DeclarativeBase):
    pass


class Set(Base):
    __tablename__ = "set"

    id: Mapped[int] = mapped_column(primary_key=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"), nullable=False)
    show_id: Mapped[int] = mapped_column(ForeignKey("show.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)
    value_id: Mapped[int] = mapped_column(ForeignKey("value.id"), nullable=False)

    category: Mapped["Category"] = relationship(back_populates="sets")
    date: Mapped["Date"] = relationship(back_populates="sets")
    show: Mapped["Show"] = relationship(back_populates="sets")
    round: Mapped["Round"] = relationship(back_populates="sets")
    value: Mapped["Value"] = relationship(back_populates="sets")

    external: Mapped[bool] = mapped_column(Boolean, nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hash: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    answer: Mapped[str] = mapped_column(String(1000))
    question: Mapped[str] = mapped_column(String(255))

    def __repr__(self):
        return f"<Set {self.id}, (Hash={self.hash})>"


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    show_id: Mapped[int] = mapped_column(ForeignKey("show.id"), nullable=False)
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"), nullable=False)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)

    show: Mapped["Show"] = relationship(back_populates="categories")
    date: Mapped["Date"] = relationship(back_populates="categories")
    round: Mapped["Round"] = relationship(back_populates="categories")

    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sets: Mapped[list[Set]] = relationship(back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Date(Base):
    __tablename__ = "date"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(Date)
    sets: Mapped[list[Set]] = relationship("Set", back_populates="date")
    show: Mapped["Show"] = relationship("Show", back_populates="date")
    categories: Mapped[Category] = relationship("Category", back_populates="date")

    @hybrid_property
    def year(self):
        return self.date.year

    @year.expression
    def year(cls):
        return extract("year", cls.date)

    @hybrid_property
    def month(self):
        return self.date.month

    @month.expression
    def month(cls):
        return extract("month", cls.date)

    @hybrid_property
    def day(self):
        return self.date.day

    @day.expression
    def day(cls):
        return extract("day", cls.date)

    def __repr__(self):
        return f"<Date {self.date}>"


class Show(Base):
    __tablename__ = "show"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer)
    date_id: Mapped[int] = mapped_column(ForeignKey("date.id"))

    date: Mapped["Date"] = relationship(back_populates="show")

    sets: Mapped[list[Set]] = relationship("Set", back_populates="show")
    categories: Mapped[list[Category]] = relationship("Category", back_populates="show")

    def __repr__(self):
        return f"<Show {self.number}>"


class Round(Base):
    __tablename__ = "round"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(Integer)
    sets: Mapped[list[Set]] = relationship("Set", back_populates="round")
    categories: Mapped[list[Category]] = relationship("Category", back_populates="round")
    values: Mapped["Value"] = relationship("Value", back_populates="round")

    def __repr__(self):
        return f"<Round {self.number}>"


class Value(Base):
    __tablename__ = "value"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)
    round_id: Mapped[int] = mapped_column(ForeignKey("round.id"), nullable=False)

    round: Mapped["Round"] = relationship(back_populates="values")

    sets: Mapped[list[Set]] = relationship("Set", back_populates="value")

    def __repr__(self):
        return f"<Value {self.amount}>"
