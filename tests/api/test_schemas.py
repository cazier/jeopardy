import json
import random
import typing as t
import datetime

import pytest
from faker.proxy import Faker
from sqlalchemy.exc import NoInspectionAvailable

from jeopardy.api.models import *
from jeopardy.api.schemas import ApiJSONProvider, schema_keys


def parse(data: Base) -> dict[str, t.Any]:
    return json.loads(json.dumps(data, default=ApiJSONProvider.default))


def test_schema_keys():
    with pytest.raises(NoInspectionAvailable):
        schema_keys("schema")

    assert schema_keys(Round(number=123)) == [("number", int)]


def test_date():
    date_date = datetime.date.today()

    date = Date(date=date_date)
    assert parse(date) == {"date": date_date.isoformat()}


def test_round():
    round_number = random.randint(0, 100)

    round = Round(number=round_number)
    assert parse(round) == {"number": round_number}


def test_value():
    amount = random.randint(0, 100)
    round = Round(number=random.randint(0, 100))

    value = Value(amount=amount, round=round)
    assert parse(value) == {"amount": amount}


def test_show():
    date_date = datetime.date.today()
    date = Date(date=date_date)

    show_id = random.randint(0, 100)
    show_number = random.randint(0, 100)

    show = Show(id=show_id, date=date, number=show_number)
    assert parse(show) == {"id": show_id, "number": show_number, "date": date_date.isoformat()}


def test_category(faker: Faker):
    date_date = datetime.date.today()
    show_number = random.randint(0, 100)
    round_number = random.randint(0, 100)
    date = Date(date=date_date)
    round = Round(number=round_number)
    show = Show(id=random.randint(0, 100), date=date, number=show_number)

    name = faker.name()
    category_id = random.randint(0, 100)
    complete = bool(random.randint(0, 1))

    category = Category(id=category_id, name=name, show=show, date=date, round=round, complete=complete)
    assert parse(category) == {
        "id": category_id,
        "name": name,
        "show": show_number,
        "date": date_date.isoformat(),
        "round": round_number,
        "complete": complete,
    }


def test_set(faker: Faker):
    date_date = datetime.date.today()
    show_number = random.randint(0, 100)
    round_number = random.randint(0, 100)
    value_amount = random.randint(0, 100)
    category_name = faker.name()
    category_complete = bool(random.randint(0, 1))
    date = Date(date=date_date)
    round = Round(number=round_number)
    value = Value(amount=value_amount, round=round)
    show = Show(id=random.randint(0, 100), date=date, number=show_number)
    category = Category(
        id=random.randint(0, 100), name=category_name, show=show, date=date, round=round, complete=category_complete
    )

    set_id = random.randint(0, 100)
    external = bool(random.randint(0, 1))
    answer = faker.name()
    question = faker.name()

    set = Set(
        id=set_id,
        category=category,
        date=date,
        show=show,
        round=round,
        value=value,
        external=external,
        hash=faker.name(),
        answer=answer,
        question=question,
    )
    assert parse(set) == {
        "id": set_id,
        "category": category_name,
        "date": date_date.isoformat(),
        "show": show_number,
        "round": round_number,
        "value": value_amount,
        "external": external,
        "complete": category_complete,
        "answer": answer,
        "question": question,
    }
