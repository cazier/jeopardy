import datetime

import pytest
from marshmallow.exceptions import ValidationError

from jeopardy.api import models, schemas


def test_round_schema():
    data = {"number": 0}
    schema = schemas.RoundSchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    assert schema.dump(schema.load({"number": "0"})) == {"number": 0}

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})


def test_value_schema():
    data = {"amount": 200}
    schema = schemas.ValueSchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    assert schema.dump(schema.load({"amount": "0"})) == {"amount": 0}

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})


def test_date_schema():
    data = {"date": "1964-03-30"}
    schema = schemas.DateSchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})


def test_show_schema():
    data = {"date": "1964-03-30", "number": 1, "id": 1}
    schema = schemas.ShowSchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    assert schema.dump(schema.load({**data, **{"number": "1", "id": "1"}})) == data

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})


def test_category_schema():
    data = {"date": "1964-03-30", "id": 1, "show": 1, "name": "category", "complete": True}
    schema = schemas.CategorySchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    assert schema.dump(schema.load({**data, **{"show": "1", "id": "1"}})) == data

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})


def test_set_schema():
    data = {
        "date": "1964-03-30",
        "id": 1,
        "show": 1,
        "category": "category",
        "external": False,
        "answer": "answer",
        "question": "question",
        "value": 1,
        "complete": True,
    }
    schema = schemas.SetSchema()
    model = schema.load(data)

    assert schema.dump(model) == data
    assert schema.dump(object) == {}

    assert schema.dump(schema.load({**data, **{"show": "1", "id": "1", "value": "1", "external": "False"}})) == data

    with pytest.raises(ValidationError):
        assert schema.load({"model": 0})
