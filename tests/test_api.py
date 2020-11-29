import json
import pathlib

import pytest
import requests

from jeopardy_data import api


@pytest.fixture
def testclient():
    jeopardy = api.app
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-full.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.test_client() as client:
        yield client


@pytest.fixture
def emptyclient():
    jeopardy = api.app
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-empty.db').absolute()}"
    jeopardy.config["TESTING"] = True

    api.db.create_all()

    with jeopardy.test_client() as client:
        yield client

    api.db.drop_all()


def test_get_details_empty(emptyclient, test_data):
    rv = emptyclient.get("/details")

    assert rv.status_code == 404
    assert rv.json == {"message": "there are no items currently in the database"}


def test_get_details_methods(emptyclient):
    rv = {
        emptyclient.post("/details").status_code,
        emptyclient.delete("/details").status_code,
        emptyclient.put("/details").status_code,
        emptyclient.patch("/details").status_code,
    }

    assert rv == {405}


def test_get_details(testclient, test_data):
    rv = testclient.get("/details")

    assert rv.status_code == 200
    assert rv.json["sets"] == len(test_data)
    assert list(rv.json.keys()) == ["air_dates", "categories", "has_external", "is_complete", "sets", "shows"]


# def test_empty_db(emptyclient, test_data):
#     question = test_data[0]

#     rv = emptyclient.post("/sets", json=question)

#     assert rv.data != None

