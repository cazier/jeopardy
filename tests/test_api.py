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


def test_get_details_methods(emptyclient):
    rv = {
        emptyclient.post("/details").status_code,
        emptyclient.delete("/details").status_code,
        emptyclient.put("/details").status_code,
        emptyclient.patch("/details").status_code,
    }

    assert rv == {405}


def test_empty_client(emptyclient):
    for endpoint in ["/details", "/shows", "/show", "/set", "/sets"]:
        rv = emptyclient.get(endpoint)

        assert rv.status_code == 404
        assert "no items" in rv.get_json()["message"]


def test_invalid_endpoint(emptyclient):
    rv = emptyclient.get("/alex")

    assert rv.status_code == 404


def test_get_details(testclient, test_data):
    rv = testclient.get("/details")

    assert rv.status_code == 200
    assert rv.get_json()["sets"] == len(test_data)
    assert list(rv.get_json().keys()) == ["air_dates", "categories", "has_external", "is_complete", "sets", "shows"]


def test_pagination(testclient, test_data):
    rv = testclient.get("/sets", query_string={"number": 13, "start": 4})
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 13

    rv = testclient.get("/sets", query_string={"start": 100})
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(test_data) - 100

    rv = testclient.get("/sets", query_string={"start": 200})
    assert rv.status_code == 400
    assert rv.get_json()["message"] == "start number too great"


def test_sets(testclient, test_data):
    rv = testclient.get(f"/sets")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 100

    rv = testclient.get(f"/set/1")

    assert rv.status_code == 200
    assert rv.get_json() == dict(test_data[0], **{"id": 1})

    rv = testclient.get(f"/set/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_set_changes(testclient, test_data):
    set_ = test_data[-1]

    rv = testclient.delete(f"/set/119")
    assert rv.status_code == 200
    assert rv.get_json() == {"deleted": 119}

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 200
    assert rv.get_json() == dict(set_, **{"id": 119})

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "the supplied data is already in the database"}

    set_.pop("show")

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "the posted data is missing some data"}


def test_show(testclient):
    rv = testclient.get(f"/shows")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 2


def test_show_by_id(testclient):
    rv = testclient.get(f"/show/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"date": "1992-08-13", "id": 1, "number": 1}

    rv = testclient.get(f"/show/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_show_by_number(testclient):
    rv = testclient.get(f"/show/number/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"date": "1992-08-13", "id": 1, "number": 1}

    rv = testclient.get(f"/show/number/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_show_by_date(testclient):
    rv = testclient.get(f"/show/date/1992")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/show/date/1992/8")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/show/date/1992/08")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/show/date/1992/8/13")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/show/date/1992/08/13")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/show/date/2020/01/01")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}

    rv = testclient.get(f"/show/date/00/01/01")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]

    rv = testclient.get(f"/show/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_categories(testclient, test_data):
    rv = testclient.get(f"/categories")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len({f"{i['category']}_{i['show']}" for i in test_data})


def test_category_by_id(testclient):
    rv = testclient.get(f"/category/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"complete": True, "date": "1992-08-13", "id": 1, "name": "DOGS", "round": 0, "show": 1}

    rv = testclient.get(f"/category/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_categories_by_date(testclient, test_data):
    rv = testclient.get(f"/category/date/1992")
    expected = {f"{i['category']}_{i['show']}" for i in test_data if i["date"] == "1992-08-13"}

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(expected)

    rv = testclient.get(f"/category/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_categories_by_completion(testclient, test_data):
    complete = {f"{i['category']}_{i['show']}" for i in test_data if i["complete"]}
    incomplete = {f"{i['category']}_{i['show']}" for i in test_data if not i["complete"]}

    rv = testclient.get(f"/category/complete")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(complete)

    rv = testclient.get(f"/category/complete/true")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(complete)

    rv = testclient.get(f"/category/incomplete")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(incomplete)

    rv = testclient.get(f"/category/complete/false")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(incomplete)

    rv = testclient.get(f"/category/complete/alex")

    assert rv.status_code == 400
    assert "completion status must be" in rv.get_json()["message"]


def test_empty_db(emptyclient, test_data):
    question = test_data[0]

    rv = emptyclient.post("/sets", json=question)

    assert rv.data != None

