import pathlib
import json

import pytest

from jeopardy_data import api


@pytest.fixture(autouse=True, scope="module")
def emptyclient():
    jeopardy = api.app
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-empty.db').absolute()}"
    jeopardy.config["TESTING"] = True

    api.db.create_all()

    with jeopardy.test_client() as client:
        yield client

    api.db.drop_all()


def test_add_one_long():
    clue = {
        "date": "2020-01-01",
        "show": 1,
        "round": 0,
        "complete": True,
        "answer": "answer",
        "question": "question",
        "external": True,
        "value": 1,
        "category": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=False)
    assert success


def test_add_one_long_missing():
    clue = {
        "date": "2020-01-01",
        "show": 1,
        "round": 0,
        "answer": "answer",
        "question": "question",
        "external": True,
        "value": 1,
        "category": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=False)
    assert not success


def test_add_one_short():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert success


def test_add_one_short_missing():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success


def test_add_multiple():
    clues = [
        {
            "d": "2020-01-01",
            "s": 3,
            "r": 0,
            "f": True,
            "a": "answer",
            "q": "question",
            "e": True,
            "v": 1,
            "c": "test",
        },
        {
            "d": "2020-01-01",
            "s": 4,
            "r": 0,
            "f": True,
            "a": "answer",
            "q": "question",
            "e": True,
            "v": 1,
            "c": "test",
        },
    ]
    results = [api.database.add(clue_data=clue, uses_shortnames=True) for clue in clues]

    assert all((response[0] for response in results))


def test_add_one_empty():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }

    results = list()

    for key in clue.keys():
        data = {k: v if k != key else "" for k, v in clue.items()}
        results.append(api.database.add(clue_data=data, uses_shortnames=True))

    assert all((not response[0] for response in results))


def test_add_one_repeat():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "this set already exists"})


def test_add_one_repeat():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "this set already exists"})


def test_add_bad_date():
    clue = {
        "d": "20210-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "please format the date in the isoformat: YYY-MM-DD"})


def test_add_bad_show():
    clue = {
        "d": "2020-01-01",
        "s": "alex",
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "please format the date in the isoformat: YYY-MM-DD"})


def test_add_bad_round_not_integer():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": "alex",
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (
        message == {"message": "please ensure the round number is one of the following integers: (0, 1, 2, 4)"}
    )


def test_add_bad_round_not_valid():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 3,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (
        message == {"message": "please ensure the round number is one of the following integers: (0, 1, 2, 4)"}
    )


def test_add_bad_complete():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": "alex",
        "a": "answer",
        "q": "question",
        "e": True,
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "please ensure the complete tag is supplied with a boolean value"})


def test_add_bad_value_not_integer():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": "alex",
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (
        message == {"message": 'please ensure the value is a positive number, with or without, a "$"'}
    )


def test_add_bad_value_not_positive():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": True,
        "v": -1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (
        message == {"message": 'please ensure the value is a positive number, with or without, a "$"'}
    )


def test_add_bad_external():
    clue = {
        "d": "2020-01-01",
        "s": 2,
        "r": 0,
        "f": True,
        "a": "answer",
        "q": "question",
        "e": "alex",
        "v": 1,
        "c": "test",
    }
    success, message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert not success & (message == {"message": "please ensure the external tag is supplied with a boolean value"})
