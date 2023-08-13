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
        round_ = Round(number=number)

        assert round_.number == number
        assert repr(round_) == f"<Round {number}>"

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
        round_ = Round(number=0)

        amount = 1
        value = Value(amount=amount, round=round_)

        assert value.amount == amount
        assert value.round == round_
        assert repr(value) == f"<Value {amount}>"

    def test_model_show(self):
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))

        number = 1
        show = Show(number=number, date=date)

        assert show.number == number
        assert show.date == date
        assert repr(show) == f"<Show {number}>"

    def test_model_category(self):
        round_ = Round(number=0)
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))
        show = Show(number=1, date=date)

        name = "Category"
        complete = True
        category = Category(name=name, round=round_, date=date, show=show, complete=complete)

        assert category.name == name
        assert category.round == round_
        assert category.date == date
        assert category.show == show
        assert category.complete == complete
        assert repr(category) == f"<Category {name}>"

    def test_model_set(self):
        round_ = Round(number=0)
        date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))
        value = Value(amount=200, round=round_)
        show = Show(number=1, date=date)
        category = Category(name="Category", round=round_, date=date)

        external = False
        complete = True
        hash_ = "hash_string"
        answer = "Answer"
        question = "Question"

        set_ = Set(
            external=external,
            complete=complete,
            hash=hash_,
            answer=answer,
            question=question,
            round=round_,
            date=date,
            value=value,
            show=show,
            category=category,
        )
        assert set_.external == external
        assert set_.complete == complete
        assert set_.hash == hash_
        assert set_.answer == answer
        assert set_.question == question
        assert set_.round == round_
        assert set_.date == date
        assert set_.value == value
        assert set_.show == show
        assert set_.category == category
        assert repr(set_) == f"<Set None, (Hash={hash_})>"
