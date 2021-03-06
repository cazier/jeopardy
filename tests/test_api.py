import json
import pathlib

import pytest
import requests

from jeopardy import web, config
from jeopardy.api import models


API_VERSION = config.api_version


@pytest.fixture
def testclient():
    jeopardy = web.create_app()
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-full.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.test_client() as client:
        yield client


@pytest.fixture
def api_emptyclient():
    jeopardy = web.create_app()
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-empty.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.app_context():
        models.db.create_all()

        with jeopardy.test_client() as client:
            yield client

        models.db.drop_all()


def test_get_details_methods(api_emptyclient):
    rv = {
        api_emptyclient.post(f"/api/v{API_VERSION}/details").status_code,
        api_emptyclient.delete(f"/api/v{API_VERSION}/details").status_code,
        api_emptyclient.put(f"/api/v{API_VERSION}/details").status_code,
        api_emptyclient.patch(f"/api/v{API_VERSION}/details").status_code,
    }

    assert rv == {405}


def test_empty_client(api_emptyclient):
    for endpoint in [f"/api/v{API_VERSION}/details", f"/api/v{API_VERSION}/show", f"/api/v{API_VERSION}/set"]:
        rv = api_emptyclient.get(endpoint)

        assert rv.status_code == 404
        assert "no items" in rv.get_json()["message"]


def test_invalid_endpoint(api_emptyclient):
    rv = api_emptyclient.get(f"/api/v{API_VERSION}/alex")

    assert rv.status_code == 404


def test_get_details(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/details")

    assert rv.status_code == 200
    assert rv.get_json()["sets"]["total"] == len(test_data)
    assert list(rv.get_json().keys()) == ["air_dates", "categories", "sets", "shows"]


def test_pagination(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"number": 13, "start": 4})
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 13

    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"start": 100})
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(test_data) - 100

    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"start": 200})
    assert rv.status_code == 400
    assert rv.get_json()["message"] == "start number too great"


def test_sets_including_by_id(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/set")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 100

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == dict(test_data[0], **{"id": 1})

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_set_changes(testclient, test_data):
    set_ = test_data[-1]

    rv = testclient.delete(f"/api/v{API_VERSION}/set/id/119")
    assert rv.status_code == 200
    assert rv.get_json() == {"deleted": 119}

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    assert rv.status_code == 200
    assert rv.get_json() == dict(set_, **{"id": 119})

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/119")
    assert rv.status_code == 200
    assert rv.get_json() == dict(set_, **{"id": 119})

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "The question set supplied is already in the database!"}

    set_.pop("show")

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    assert rv.status_code == 400
    assert rv.get_json() == {"message": "The question set supplied is missing some data. Every field is required."}


def test_sets_by_show(testclient, test_data):
    matching = [i for i in test_data if i["show"] == 1]

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/number/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/id/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/number/100")

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "Unfortunately, there is no show in the database with that number. Please double check your values."}

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/id/100")

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "Unfortunately, there is no show in the database with that ID. Please double check your values."}


def test_sets_by_date(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/set/date/1992")
    matching = [i for i in test_data if i["date"] == "1992-08-13"]

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_sets_by_years(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1992/1992")
    matching = [i for i in test_data if i["date"] == "1992-08-13"]

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1992/1993")
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1991/1992")
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1994/1992")
    assert rv.status_code == 400
    assert "The stop year must come after the starting year." in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/0/20000")
    assert rv.status_code == 400
    assert "year range must be between 0001 and 9999" in rv.get_json()["message"]


def test_sets_by_round(testclient, test_data):
    matching = [i for i in test_data if i["round"] == 1]

    rv = testclient.get(f"/api/v{API_VERSION}/set/round/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/set/round/4")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/set/round/-1")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]


def test_sets_by_round_empty(api_emptyclient):
    rv = api_emptyclient.get(f"/api/v{API_VERSION}/set/round/1")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_show(testclient):
    rv = testclient.get(f"/api/v{API_VERSION}/show")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == 2


def test_show_by_id(testclient):
    rv = testclient.get(f"/api/v{API_VERSION}/show/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"date": "1992-08-13", "id": 1, "number": 1}

    rv = testclient.get(f"/api/v{API_VERSION}/show/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_show_by_number(testclient):
    rv = testclient.get(f"/api/v{API_VERSION}/show/number/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"date": "1992-08-13", "id": 1, "number": 1}

    rv = testclient.get(f"/api/v{API_VERSION}/show/number/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_show_by_date(testclient):
    rv = testclient.get(f"/api/v{API_VERSION}/show/date/1992")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/1992/8")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/1992/08")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/1992/8/13")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/1992/08/13")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/2020/01/01")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/00/01/01")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_shows_by_years(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1992/1992")

    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1992/1993")
    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1991/1992")
    assert rv.status_code == 200
    assert rv.get_json()["data"] == [{"date": "1992-08-13", "id": 1, "number": 1}]

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1994/1992")
    assert rv.status_code == 400
    assert "The stop year must come after the starting year." in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/0/20000")
    assert rv.status_code == 400
    assert "year range must be between 0001 and 9999" in rv.get_json()["message"]


def test_categories(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/category")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len({f"{i['category']}_{i['show']}" for i in test_data})


def test_category_by_id(testclient):
    rv = testclient.get(f"/api/v{API_VERSION}/category/id/1")

    assert rv.status_code == 200
    assert rv.get_json() == {"complete": True, "date": "1992-08-13", "id": 1, "name": "DOGS", "round": 0, "show": 1}

    rv = testclient.get(f"/api/v{API_VERSION}/category/id/200")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_categories_by_date(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/category/date/1992")
    expected = {f"{i['category']}_{i['show']}" for i in test_data if i["date"] == "1992-08-13"}

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(expected)

    rv = testclient.get(f"/api/v{API_VERSION}/category/date/2020/02/31")

    assert rv.status_code == 400
    assert "check that your date is valid" in rv.get_json()["message"]


def test_category_by_years(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1992/1992")
    expected = {f"{i['category']}_{i['show']}" for i in test_data if i["date"] == "1992-08-13"}

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(expected)

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1992/1993")
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(expected)

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1991/1992")
    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(expected)

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1994/1992")
    assert rv.status_code == 400
    assert "The stop year must come after the starting year." in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/0/20000")
    assert rv.status_code == 400
    assert "year range must be between 0001 and 9999" in rv.get_json()["message"]


def test_categories_by_completion(testclient, test_data):
    complete = {f"{i['category']}_{i['show']}" for i in test_data if i["complete"]}
    incomplete = {f"{i['category']}_{i['show']}" for i in test_data if not i["complete"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(complete)

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/true")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(complete)

    rv = testclient.get(f"/api/v{API_VERSION}/category/incomplete")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(incomplete)

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/false")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(incomplete)

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/alex")

    assert rv.status_code == 400
    assert "completion status must be" in rv.get_json()["message"]


def test_categories_by_name(testclient, test_data):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if "BEER" in i["category"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/name/BEER")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    matching = {f"{i['category']}_{i['show']}" for i in test_data if "D" in i["category"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/name/D")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)


def test_categories_by_show(testclient, test_data):
    matching = {f"{i['category']}" for i in test_data if i["show"] == 1}

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/number/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/id/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/number/100")

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "Unfortunately, there is no show in the database with that number. Please double check your values."}

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/id/100")

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "Unfortunately, there is no show in the database with that ID. Please double check your values."}


def test_categories_by_round(testclient, test_data):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if i["round"] == 1}

    rv = testclient.get(f"/api/v{API_VERSION}/category/round/1")

    assert rv.status_code == 200
    assert len(rv.get_json()["data"]) == len(matching)

    rv = testclient.get(f"/api/v{API_VERSION}/category/round/4")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]

    rv = testclient.get(f"/api/v{API_VERSION}/category/round/-1")

    assert rv.status_code == 400
    assert "round number must be" in rv.get_json()["message"]


def test_categories_by_round_empty(api_emptyclient):
    rv = api_emptyclient.get(f"/api/v{API_VERSION}/category/round/1")

    assert rv.status_code == 404
    assert rv.get_json() == {"message": "no items were found with that query"}


def test_empty_db(api_emptyclient, test_data):
    question = test_data[0]

    rv = api_emptyclient.post(f"/api/v{API_VERSION}/set", json=question)

    assert rv.data != None


def test_game_resource(testclient, test_data):
    rv = testclient.get(f"/api/v{API_VERSION}/game")

    assert rv.status_code == 200
    assert len(rv.get_json()) == 6

    expected = [i for i in test_data if i["complete"]]
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"round": 1})

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
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"start": 1992, "stop": 1992})

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
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"show_number": 2})

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
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"show_id": 2})

    assert rv.status_code == 200
    assert len(rv.get_json()) == min(
        6,
        len(
            {f'{i["category"]}_{i["show"]}' for i in expected if i["round"] != 2}.difference(
                {f'{i["category"]}_{i["show"]}' for i in expected if i["external"]}
            )
        ),
    )

    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"show_id": 2, "show_number": 2})

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "Only one of Show Number or Show ID may be supplied at a time."}

    rv = testclient.get(
        f"/api/v{API_VERSION}/game", query_string={"show_number": 2, "round": 1, "allow_external": True}
    )

    assert rv.status_code == 200
    assert any([j["external"] for i in rv.get_json() for j in i["sets"]])

    rv = testclient.get(
        f"/api/v{API_VERSION}/game", query_string={"show_number": 2, "round": 0, "allow_incomplete": True}
    )

    assert rv.status_code == 200
    assert any([not (i["category"]["complete"]) for i in rv.get_json()])

    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"round": 4})

    assert rv.status_code == 400
    assert rv.get_json() == {"message": "The round number must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)"}

    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"size": 30})

    assert rv.status_code == 400
    assert "categories were found. Please reduce the size." in rv.get_json()["message"]

    # Due to omitting duplicated category names
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"size": 18})

    assert rv.status_code == 400
    assert "categories were found. Please reduce the size." in rv.get_json()["message"]


# """
# | ROUTE               |       |                   |        |       |          |      |          |                 |        |
# | ------------------- | ----- | ----------------- | ------ | ----- | -------- | ---- | -------- | --------------- | ------ |
# | CATEGORY (MULTIPLE) | N     | Y                 | N      | Y     | N        | Y    | Y        | Y (NAME and ID) |        |
# | COMPLETE            | N/A   | N/A               | N/A    | N/A   | N/A      | N/A  | N/A      | N/A             |        |
# | DATE                | N/A   | N/A               | N/A    | N/A   | N/A      | N/A  | N/A      | N/A             |        |
# | EXTERNAL            | N/A   | N/A               | N/A    | N/A   | N/A      | N/A  | N/A      | N/A             |        |
# | ROUND               | N/A   | N/A               | N/A    | N/A   | N/A      | N/A  | N/A      | N/A             |        |
# | SET (MULTIPLE)      | Y     | Y                 | Y (ID) | Y     | Y        | Y    | Y        | Y               |        |
# | SHOW (MULTIPLE)     | N     | Y (NUMBER and ID) | N      | N     | N        | Y    | N        | N               |        |
# | VALUE               | N/A   | N/A               | N/A    | N/A   | N/A      | N/A  | N/A      | N/A             |        |
# |                     | VALUE | SHOW              | SET    | ROUND | EXTERNAL | DATE | COMPLETE | CATEGORY        | FILTER |

# https://restfulapi.net/http-status-codes/
# https://restfulapi.net/http-methods/#summary

# """
