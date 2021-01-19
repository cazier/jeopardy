import json
import math
import operator

import pytest

from jeopardy_data.tools import split


def test_by_year(test_data):
    results = split.by_year(data=test_data)

    assert results["1992"] == [i for i in test_data if i["date"].startswith("1992")]

    short_data = list()

    for item in test_data:
        item["d"] = item["date"]
        del item["date"]

        short_data.append(item)

    results = split.by_year(data=short_data)

    assert results["1992"] == [i for i in short_data if i["d"].startswith("1992")]

    with pytest.raises(KeyError):
        split.by_year(data=[{}])


def test_by_show(test_data):
    results = split.by_show(data=test_data)

    assert results[1] == [i for i in test_data if i["show"] == 1]

    short_data = list()

    for item in test_data:
        item["s"] = item["show"]
        del item["show"]

        short_data.append(item)

    results = split.by_show(data=short_data)

    assert results[1] == [i for i in short_data if i["s"] == 1]

    with pytest.raises(KeyError):
        split.by_show(data=[{}])


def test_by_round(test_data):
    results = split.by_round(data=test_data)

    assert results[1] == [i for i in test_data if i["round"] == 1]

    short_data = list()

    for item in test_data:
        item["r"] = item["round"]
        del item["round"]

        short_data.append(item)

    results = split.by_round(data=short_data)

    assert results[1] == [i for i in short_data if i["r"] == 1]

    with pytest.raises(KeyError):
        split.by_round(data=[{}])


def test_by_external(test_data):
    results = split.by_external(data=test_data)

    assert results[1] == [i for i in test_data if i["external"] == 1]

    short_data = list()

    for item in test_data:
        item["e"] = item["external"]
        del item["external"]

        short_data.append(item)

    results = split.by_external(data=short_data)

    assert results[False] == [i for i in short_data if i["e"] == False]

    with pytest.raises(KeyError):
        split.by_external(data=[{}])


def test_by_complete(test_data):
    results = split.by_complete(data=test_data)

    assert results[1] == [i for i in test_data if i["complete"] == 1]

    short_data = list()

    for item in test_data:
        item["f"] = item["complete"]
        del item["complete"]

        short_data.append(item)

    results = split.by_complete(data=short_data)

    assert results[False] == [i for i in short_data if i["f"] == False]

    with pytest.raises(KeyError):
        split.by_complete(data=[{}])


def test_by_limit(test_data):
    results = split.by_limit(data=test_data, limit=25)

    assert len(results.keys()) == math.ceil(len(test_data) / 25)
    assert len(results[0]) >= len(results[1])
    assert len(results[-2]) >= len(results[-1])

    with pytest.raises(TypeError, match=".*must be an.*"):
        results = split.by_limit(data=test_data, limit="A")
