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
    assert rv.get_json()["sets"]["total"] == len(test_data)
    assert list(rv.get_json().keys()) == ["air_dates", "categories", "sets", "shows"]


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


def test_sets_including_by_id(testclient, test_data):
    rv = testclient.get(f"/sets")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 100

    rv = testclient.get(f"/set/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == dict(test_data[0], **{"id": 1})

    rv = testclient.get(f"/set/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_set_changes(testclient, test_data):
    set_ = test_data[-1]

    rv = testclient.delete(f"/set/id/119")
    assert rv.status_code == 200
    assert rv.get_json() == {"deleted": 119}

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 200
    assert rv.get_json() == dict(set_, **{"id": 119})

    rv = testclient.get(f"/set/id/119")
    assert rv.status_code == 200
    assert rv.get_json() == dict(set_, **{"id": 119})

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "the supplied data is already in the database"}

    set_.pop("show")

    rv = testclient.post(f"/sets", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "the posted data is missing some data"}


def test_sets_by_show(testclient, test_data):
    matching = [i for i in test_data if i["show"] == 1]

    rv = testclient.get(f"/set/show/number/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/set/show/id/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/set/show/number/100")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}

    rv = testclient.get(f"/set/show/id/100")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_sets_by_date(testclient, test_data):
    rv = testclient.get(f"/set/date/1992")
    matching = [i for i in test_data if i["date"] == "1992-08-13"]

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/set/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_sets_by_round(testclient, test_data):
    matching = [i for i in test_data if i["round"] == 1]

    rv = testclient.get(f"/set/round/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/set/round/4")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]

    rv = testclient.get(f"/set/round/-1")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]


def test_sets_by_round_empty(emptyclient):
    rv = emptyclient.get(f"/set/round/1")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


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


def test_categories_by_name(testclient, test_data):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if "BEER" in i["category"]}

    rv = testclient.get(f"/category/name/BEER")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    matching = {f"{i['category']}_{i['show']}" for i in test_data if "D" in i["category"]}

    rv = testclient.get(f"/category/name/D")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)


def test_categories_by_show(testclient, test_data):
    matching = {f"{i['category']}" for i in test_data if i["show"] == 1}

    rv = testclient.get(f"/category/show/number/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/category/show/id/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/category/show/number/100")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}

    rv = testclient.get(f"/category/show/id/100")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_categories_by_round(testclient, test_data):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if i["round"] == 1}

    rv = testclient.get(f"/category/round/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/category/round/4")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]

    rv = testclient.get(f"/category/round/-1")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]


def test_categories_by_round_empty(emptyclient):
    rv = emptyclient.get(f"/category/round/1")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_empty_db(emptyclient, test_data):
    question = test_data[0]

    rv = emptyclient.post("/sets", json=question)

    assert rv.data != None


def test_game_resource(testclient, test_data):
    rv = testclient.get("/game")

    assert rv.status_code == 200
    assert len(rv.get_json()) == 6

    expected = [i for i in test_data if i["complete"]]
    rv = testclient.get("/game", query_string={"round": 1})

    assert rv.status_code == 200
    assert len(rv.get_json()) == min(
        6,
        len(
            {f'{i["category"]}_{i["show"]}' for i in expected if i["round"] == 1}.difference(
                {f'{i["category"]}_{i["show"]}' for i in expected if i["external"]}
            )
        ),
    )

    expected = [i for i in test_data if (i["date"][:4] == "1992") & (i["complete"])]
    rv = testclient.get("/game", query_string={"year": 1992})

    assert rv.status_code == 200
    assert len(rv.get_json()) == min(
        6,
        len(
            {f'{i["category"]}_{i["show"]}' for i in expected if i["round"] != 2}.difference(
                {f'{i["category"]}_{i["show"]}' for i in expected if i["external"]}
            )
        ),
    )

    expected = [i for i in test_data if (i["show"] == 2) & (i["complete"])]
    rv = testclient.get("/game", query_string={"show_number": 2})

    assert rv.status_code == 200
    assert len(rv.get_json()) == min(
        6,
        len(
            {f'{i["category"]}_{i["show"]}' for i in expected if i["round"] != 2}.difference(
                {f'{i["category"]}_{i["show"]}' for i in expected if i["external"]}
            )
        ),
    )

    expected = [i for i in test_data if (i["show"] == 2) & (i["complete"])]
    rv = testclient.get("/game", query_string={"show_id": 2})

    assert rv.status_code == 200
    assert len(rv.get_json()) == min(
        6,
        len(
            {f'{i["category"]}_{i["show"]}' for i in expected if i["round"] != 2}.difference(
                {f'{i["category"]}_{i["show"]}' for i in expected if i["external"]}
            )
        ),
    )

    rv = testclient.get("/game", query_string={"show_id": 2, "show_number": 2})

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "only one of show_number and show_id may be supplied at a time"}

    rv = testclient.get("/game", query_string={"show_number": 2, "round": 1, "allow_external": True})

    assert rv.status_code == 200
    assert any([j["external"] for i in rv.get_json().values() for j in i["sets"]])

    rv = testclient.get("/game", query_string={"show_number": 2, "round": 0, "allow_incomplete": True})

    assert rv.status_code == 200
    assert any([not (i["category"]["complete"]) for i in rv.get_json().values()])

    rv = testclient.get("/game", query_string={"round": 4})

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "round number must be between 0 (jeopardy) and 2 (final jeopardy/tiebreaker)"}

    rv = testclient.get("/game", query_string={"size": 30})

    assert rv.status_code == 400
    assert "requested too many categories; only " in rv.get_json()["message"]

    # Due to omitting duplicated category names
    rv = testclient.get("/game", query_string={"size": 18})

    assert rv.status_code == 400
    assert "requested too many categories; only " in rv.get_json()["message"]

