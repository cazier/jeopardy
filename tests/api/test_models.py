import datetime

from jeopardy.api.models import *


def test_model_round():
    number = 0
    round_ = Round(number=number)

    assert round_.number == number
    assert repr(round_) == f"<Round {number}>"


def test_model_date():
    year, month, day = 1964, 3, 30
    date_string = f"{str(year).zfill(4)}-{str(month).zfill(2)}-{str(day).zfill(2)}"

    date = Date(date=datetime.datetime.fromisoformat(date_string))

    assert date.date == datetime.datetime.fromisoformat(date_string)

    assert date.year == year
    assert date.month == month
    assert date.day == day
    assert repr(date) == f"<Date {date_string} 00:00:00>"


def test_model_value():
    round_ = Round(number=0)

    amount = 1
    value = Value(amount=amount, round=round_)

    assert value.amount == amount
    assert value.round == round_
    assert repr(value) == f"<Value {amount}>"


def test_model_show():
    date = Date(date=datetime.datetime.fromisoformat("1964-03-30"))

    number = 1
    show = Show(number=number, date=date)

    assert show.number == number
    assert show.date == date
    assert repr(show) == f"<Show {number}>"


def test_model_category():
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


def test_model_set():
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
