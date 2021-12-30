import pytest

from jeopardy import api


def test_add_one_long(emptyclient):
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
    message = api.database.add(clue_data=clue, uses_shortnames=False)
    assert message is not None


def test_add_one_long_missing(emptyclient):
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
    with pytest.raises(api.database.MissingDataError, match=".*following keys.*"):
        api.database.add(clue_data=clue, uses_shortnames=False)


def test_add_one_short(emptyclient):
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
    message = api.database.add(clue_data=clue, uses_shortnames=True)
    assert message is not None


def test_add_one_short_missing(emptyclient):
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

    with pytest.raises(api.database.MissingDataError, match=".*following keys.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_multiple(emptyclient):
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

    assert all((response is not None for response in results))


def test_add_one_empty(emptyclient):
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

    for key in clue.keys():
        data = {k: v if k != key else "" for k, v in clue.items()}

        with pytest.raises(api.database.MissingDataError, match=".*has an empty.*"):
            api.database.add(clue_data=data, uses_shortnames=True)


def test_add_one_repeat(emptyclient):
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

    with pytest.raises(api.database.SetAlreadyExistsError):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_date(emptyclient):
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
    with pytest.raises(api.database.BadDataError, match=".*date is in the isoformat.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_show(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*show number is an integer.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_round_not_integer(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*round number is one of the.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_round_not_valid(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*round number is one of the.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_complete(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*complete tag is supplied.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_value_not_integer(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*value is a positive number.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_value_not_positive(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*value is a positive number.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)


def test_add_bad_external(emptyclient):
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

    with pytest.raises(api.database.BadDataError, match=".*external tag is supplied.*"):
        api.database.add(clue_data=clue, uses_shortnames=True)
