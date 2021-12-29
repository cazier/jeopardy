import os
import json
import shutil
import pathlib
import sqlite3
import datetime

import pytest

from jeopardy import web, config, sockets


@pytest.fixture(scope="module", autouse=True)
def populate_databses():
    dbs = (pathlib.Path("tests/_files/test-empty.db"), pathlib.Path("tests/_files/test-full.db"))

    for db in dbs:
        db.unlink(missing_ok=True)

        sql = db.with_suffix("").with_suffix(".db.sqlite").read_text()

        con = sqlite3.connect(db.absolute())
        cur = con.cursor()
        cur.executescript(sql)
        con.close()

    yield

    for db in dbs:
        db.unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def empty_cache_upon_completion():
    yield

    path = pathlib.Path(os.getcwd(), "tests/_files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def test_data():
    with open("tests/_files/complete.json", "r") as sample_file:
        data = json.load(sample_file)

    with open("tests/_files/incomplete.json", "r") as sample_file:
        data.extend(json.load(sample_file))

    return data


@pytest.fixture
def clean_content():
    def _clean(data: dict) -> dict:
        data.update({"year": datetime.datetime.fromisoformat(data["date"]).strftime("%Y"), "wager": False})
        return {k: v for k, v in data.items() if k in ("year", "wager", "answer", "question")}

    return _clean


@pytest.fixture
def samplecontent(webclient, clean_content):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game").get_json()[0]["sets"][0]

    return data, clean_content(data=data)


@pytest.fixture
def samplecategory(webclient):
    data = list()
    category = webclient.flask_test_client.get(f"/api/v{config.api_version}/game").get_json()[0]

    for content in category["sets"]:
        data.append(
            {
                "year": datetime.datetime.fromisoformat(content["date"]).strftime("%Y"),
                "wager": False,
                "answer": content["answer"],
                "question": content["answer"],
                "value": content["value"],
            }
        )

    return category, data


def _app(db):
    app = web.create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/_files/test').absolute()}-{db}.db"
    app.config["TESTING"] = True

    return app


@pytest.fixture
def webclient():
    app = _app("full")

    socketio = sockets.socketio
    socketio.init_app(app)

    flask = app.test_client()

    yield socketio.test_client(app, flask_test_client=flask)


@pytest.fixture(scope="module")
def emptyclient():
    app = _app("empty")

    with app.app_context():
        with app.test_client() as client:
            yield client
