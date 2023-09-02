import pytest
from flask.testing import FlaskClient
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.test import TestResponse

from jeopardy import config

API_VERSION = config.api_version


def check_response(response: TestResponse, status: int, message: str = "", length: int = -1) -> dict[str, str]:
    assert response.status_code == status

    if message != "":
        assert f"{status} {HTTP_STATUS_CODES[status]}: {message}" == response.get_json()["message"]

    if length != -1:
        assert len(response.get_json()["data"]) == length

    return response.get_json()


def test_get_details_methods(emptyclient: FlaskClient):
    rv = {
        emptyclient.post(f"/api/v{API_VERSION}/details").status_code,
        emptyclient.delete(f"/api/v{API_VERSION}/details").status_code,
        emptyclient.put(f"/api/v{API_VERSION}/details").status_code,
        emptyclient.patch(f"/api/v{API_VERSION}/details").status_code,
    }

    assert rv == {405}


@pytest.mark.parametrize("endpoint", ("details", "show", "set"))
def test_empty_client(emptyclient: FlaskClient, endpoint: str):
    rv = emptyclient.get(f"/api/v{API_VERSION}/{endpoint}")
    check_response(rv, 404, "no items were found with that query")


def test_invalid_endpoint(emptyclient: FlaskClient):
    rv = emptyclient.get(f"/api/v{API_VERSION}/alex")
    check_response(rv, 404)


def test_get_details(testclient: FlaskClient, test_data: list[dict[str, str]]):
    rv = testclient.get(f"/api/v{API_VERSION}/details")

    assert rv.status_code == 200
    assert rv.get_json()["sets"]["total"] == len(test_data)
    assert list(rv.get_json().keys()) == ["air_dates", "categories", "sets", "shows"]


def test_pagination(testclient: FlaskClient, test_data: list[dict[str, str]]):
    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"number": 13, "start": 4})
    check_response(rv, 200, length=13)

    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"start": 100})
    assert rv.status_code == 200
    check_response(rv, 200, length=len(test_data) - 100)

    rv = testclient.get(f"/api/v{API_VERSION}/set", query_string={"start": 200})
    check_response(rv, 400, "start number too great")


def test_sets_including_by_id(testclient: FlaskClient, test_data: list[dict[str, str]]):
    rv = testclient.get(f"/api/v{API_VERSION}/set")

    assert rv.status_code == 200
    check_response(rv, 200, length=100)

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/1")
    assert check_response(rv, 200) == {**test_data[0], "id": 1}

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/200")
    check_response(rv, 404, "no items were found with that query")


def test_set_changes(testclient: FlaskClient, test_data: list[dict[str, str]]):
    set_ = test_data[-1]

    rv = testclient.delete(f"/api/v{API_VERSION}/set/id/119")
    assert check_response(rv, 200) == {"deleted": 119}

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    assert check_response(rv, 200) == {**set_, "id": 119}

    rv = testclient.get(f"/api/v{API_VERSION}/set/id/119")
    assert check_response(rv, 200) == {**set_, "id": 119}

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    check_response(rv, 400, "The question set supplied is already in the database!")

    set_.pop("show")

    rv = testclient.post(f"/api/v{API_VERSION}/set", json=set_)
    check_response(rv, 400, "The question set supplied is missing some data. Every field is required.")


def test_sets_by_show(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = [i for i in test_data if i["show"] == 1]

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/number/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/id/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/number/100")
    check_response(rv, 404, "no items were found with that query")

    rv = testclient.get(f"/api/v{API_VERSION}/set/show/id/100")
    check_response(rv, 404, "no items were found with that query")


def test_sets_by_date(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = [i for i in test_data if i["date"] == "1992-08-13"]

    rv = testclient.get(f"/api/v{API_VERSION}/set/date/1992")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/date/2020/02/31")
    check_response(rv, 400, "That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)")


def test_sets_by_years(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = [i for i in test_data if i["date"] == "1992-08-13"]

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1992/1992")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1992/1993")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1991/1992")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1995/1996")
    check_response(rv, 400, "There are no data in the database within that year span.")

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/1994/1992")
    check_response(rv, 400, "The stop year must come after the starting year.")

    rv = testclient.get(f"/api/v{API_VERSION}/set/years/0/20000")
    check_response(rv, 400, "year range must be between 0001 and 9999")


def test_sets_by_round(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = [i for i in test_data if i["round"] == 1]

    rv = testclient.get(f"/api/v{API_VERSION}/set/round/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/set/round/4")
    check_response(rv, 400, "the round must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)")


def test_sets_by_round_empty(emptyclient: FlaskClient):
    rv = emptyclient.get(f"/api/v{API_VERSION}/set/round/1")
    check_response(rv, 400, "There is no round in the database with that number.")


def test_show(testclient: FlaskClient):
    rv = testclient.get(f"/api/v{API_VERSION}/show")
    check_response(rv, 200, length=2)


@pytest.mark.parametrize("endpoint", ("id/1", "number/1"))
def test_show_by_query(testclient: FlaskClient, endpoint: str):
    rv = testclient.get(f"/api/v{API_VERSION}/show/{endpoint}")
    assert check_response(rv, 200) == {"date": "1992-08-13", "id": 1, "number": 1}


@pytest.mark.parametrize("endpoint", ("date/1992", "date/1992/08", "date/1992/08/13", "date/1992/8/13", "date/1992/8"))
def test_show_by_date(testclient: FlaskClient, endpoint: str):
    rv = testclient.get(f"/api/v{API_VERSION}/show/{endpoint}")
    assert check_response(rv, 200) == {
        "data": [{"date": "1992-08-13", "id": 1, "number": 1}],
        "number": 100,
        "start": 0,
        "results": 1,
    }


def test_show_by_date_failures(testclient: FlaskClient):
    rv = testclient.get(f"/api/v{API_VERSION}/show/date/2020/01/01")
    check_response(rv, 404, "no items were found with that query")

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/00/01/01")
    check_response(rv, 400, "That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)")

    rv = testclient.get(f"/api/v{API_VERSION}/show/date/2020/02/31")
    check_response(rv, 400, "That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)")


@pytest.mark.parametrize("endpoint", ("years/1992/1992", "years/1992/1993", "years/1991/1992"))
def test_shows_by_years(testclient: FlaskClient, endpoint: str):
    rv = testclient.get(f"/api/v{API_VERSION}/show/{endpoint}")
    assert check_response(rv, 200) == {
        "data": [{"date": "1992-08-13", "id": 1, "number": 1}],
        "number": 100,
        "start": 0,
        "results": 1,
    }


def test_shows_by_years_failures(testclient: FlaskClient):
    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1995/1996")
    check_response(rv, 400, "There are no data in the database within that year span.")

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/1994/1992")
    check_response(rv, 400, "The stop year must come after the starting year.")

    rv = testclient.get(f"/api/v{API_VERSION}/show/years/0/20000")
    check_response(rv, 400, "year range must be between 0001 and 9999")


def test_categories(testclient: FlaskClient, test_data: list[dict[str, str]]):
    rv = testclient.get(f"/api/v{API_VERSION}/category")
    check_response(rv, 200, length=len({f"{i['category']}_{i['show']}" for i in test_data}))


def test_category_by_id(testclient: FlaskClient):
    rv = testclient.get(f"/api/v{API_VERSION}/category/id/1")
    assert check_response(rv, 200) == {
        "complete": True,
        "date": "1992-08-13",
        "id": 1,
        "name": "DOGS",
        "round": 0,
        "show": 1,
    }

    rv = testclient.get(f"/api/v{API_VERSION}/category/id/200")
    check_response(rv, 404, "no items were found with that query")


def test_categories_by_date(testclient: FlaskClient, test_data: list[dict[str, str]]):
    expected = {f"{i['category']}_{i['show']}" for i in test_data if i["date"] == "1992-08-13"}

    rv = testclient.get(f"/api/v{API_VERSION}/category/date/1992")
    check_response(rv, 200, length=len(expected))

    rv = testclient.get(f"/api/v{API_VERSION}/category/date/2020/02/31")
    check_response(rv, 400, "That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)")


def test_category_by_years(testclient: FlaskClient, test_data: list[dict[str, str]]):
    expected = {f"{i['category']}_{i['show']}" for i in test_data if i["date"] == "1992-08-13"}

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1992/1992")
    check_response(rv, 200, length=len(expected))

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1992/1993")
    check_response(rv, 200, length=len(expected))

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1991/1992")
    check_response(rv, 200, length=len(expected))

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1995/1996")
    check_response(rv, 400, "There are no data in the database within that year span.")

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/1994/1992")
    check_response(rv, 400, "The stop year must come after the starting year.")

    rv = testclient.get(f"/api/v{API_VERSION}/category/years/0/20000")
    check_response(rv, 400, "year range must be between 0001 and 9999")


def test_categories_by_completion(testclient: FlaskClient, test_data: list[dict[str, str]]):
    complete = {f"{i['category']}_{i['show']}" for i in test_data if i["complete"]}
    incomplete = {f"{i['category']}_{i['show']}" for i in test_data if not i["complete"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete")
    check_response(rv, 200, length=len(complete))

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/true")
    check_response(rv, 200, length=len(complete))

    rv = testclient.get(f"/api/v{API_VERSION}/category/incomplete")
    check_response(rv, 200, length=len(incomplete))

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/false")
    check_response(rv, 200, length=len(incomplete))

    rv = testclient.get(f"/api/v{API_VERSION}/category/complete/alex")
    check_response(rv, 400, "The completion status value is invalid")


def test_categories_by_name(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if "BEER" in i["category"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/name/BEER")
    check_response(rv, 200, length=len(matching))

    matching = {f"{i['category']}_{i['show']}" for i in test_data if "D" in i["category"]}

    rv = testclient.get(f"/api/v{API_VERSION}/category/name/D")
    check_response(rv, 200, length=len(matching))


def test_categories_by_show(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = {f"{i['category']}" for i in test_data if i["show"] == 1}

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/number/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/id/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/number/100")
    check_response(rv, 400, "There is no show in the database with that number.")

    rv = testclient.get(f"/api/v{API_VERSION}/category/show/id/100")
    check_response(rv, 400, "There is no show in the database with that id.")


def test_categories_by_round(testclient: FlaskClient, test_data: list[dict[str, str]]):
    matching = {f"{i['category']}_{i['show']}" for i in test_data if i["round"] == 1}

    rv = testclient.get(f"/api/v{API_VERSION}/category/round/1")
    check_response(rv, 200, length=len(matching))

    rv = testclient.get(f"/api/v{API_VERSION}/category/round/4")
    check_response(rv, 400, "the round must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)")


def test_categories_by_round_empty(emptyclient: FlaskClient):
    rv = emptyclient.get(f"/api/v{API_VERSION}/category/round/1")
    check_response(rv, 400, "There is no round in the database with that number.")


def test_empty_db(emptyclient: FlaskClient, test_data: list[dict[str, str]]):
    rv = emptyclient.post(f"/api/v{API_VERSION}/set", json=test_data[0])
    assert check_response(rv, 200) == {**test_data[0], "id": 1}


def test_game_resource(testclient: FlaskClient, test_data: list[dict[str, str]]):
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
    check_response(rv, 400, "Only one of Show Number or Show ID can be supplied at a time.")

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

    check_response(
        rv, 400, "The round number must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)"
    )

    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"size": 30})
    check_response(rv, 400, "Only 20 categories were found.")

    # Due to omitting duplicated category names
    rv = testclient.get(f"/api/v{API_VERSION}/game", query_string={"size": 18})
    check_response(rv, 400, "Only 20 categories were found.")
