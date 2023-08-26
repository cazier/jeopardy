import datetime

import pytest
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from jeopardy.api.models import Set, Base, Date, Show, Round, Value, Category


class TestModels:
    @pytest.fixture(scope="session", autouse=True)
    def _setup_session(self):
        engine = create_engine("sqlite://")
        with Session(engine) as session:
            Base.metadata.create_all(engine)
            yield session

    @pytest.fixture(scope="function", autouse=True)
    def _attach_session(self, _setup_session):
        self.session: Session = _setup_session

    def test_model_round(self):
        number = 0
        round = Round(number=number)

        assert round.number == number
        assert repr(round) == f"<Round {number}>"

    def test_model_date(self):
        year, month, day = 1964, 3, 30
        date_string = f"{str(year).zfill(4)}-{str(month).zfill(2)}-{str(day).zfill(2)}"

        date = Date(date=datetime.datetime.fromisoformat(date_string))

        self.session.add(date)
        self.session.commit()

        assert date.date == datetime.date.fromisoformat(date_string)

        assert date.year == year
        assert date.month == month
        assert date.day == day
        assert repr(date) == f"<Date {date_string}>"

        assert self.session.scalar(select(Date).where(Date.year == year)) == date
        assert self.session.scalar(select(Date).where(Date.month == month)) == date
        assert self.session.scalar(select(Date).where(Date.day == day)) == date

    def test_model_value(self):
        round = Round(number=0)

        amount = 1
        value = Value(amount=amount, round=round)

        assert value.amount == amount
        assert value.round == round
        assert repr(value) == f"<Value {amount}>"

    def test_model_show(self):
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))

        number = 1
        show = Show(number=number, date=date)

        assert show.number == number
        assert show.date == date
        assert repr(show) == f"<Show {number}>"

    def test_model_category(self):
        round = Round(number=0)
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))
        show = Show(number=1, date=date)

        name = "Category"
        complete = True
        category = Category(name=name, round=round, date=date, show=show, complete=complete)

        assert category.name == name
        assert category.round == round
        assert category.date == date
        assert category.show == show
        assert category.complete == complete
        assert repr(category) == f"<Category {name}>"

    def test_model_set(self):
        round = Round(number=0)
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))
        value = Value(amount=200, round=round)
        show = Show(number=1, date=date)
        category = Category(name="Category", round=round, date=date, complete=True)

        external = False
        complete = True
        hash = "hashstring"
        answer = "Answer"
        question = "Question"

        set = Set(
            external=external,
            hash=hash,
            answer=answer,
            question=question,
            round=round,
            date=date,
            value=value,
            show=show,
            category=category,
        )
        assert set.external == external
        assert set.complete == complete
        assert set.hash == hash
        assert set.answer == answer
        assert set.question == question
        assert set.round == round
        assert set.date == date
        assert set.value == value
        assert set.show == show
        assert set.category == category
        assert repr(set) == f"<Set None, (Hash={hash})>"
