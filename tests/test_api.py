import json
import pathlib

import pytest
import requests

from jeopardy_data import api


@pytest.fixture
def testclient():
    jeopardy = api.app
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/testing.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.test_client() as client:
        yield client


def test_get_details(testclient, test_data):
    rv = testclient.get("/details")

    assert rv.status_code == 200
    assert rv.json["sets"] == len(test_data)
    assert list(rv.json.keys()) == ["air_dates", "categories", "has_external", "is_complete", "sets", "shows"]
