import os
import json
import shutil
import pathlib
import sqlite3
import datetime

import pytest
import requests

from jeopardy import web, config, sockets
from jeopardy.api import models


@pytest.fixture(scope="session", autouse=True)
def populate_databses():
    dbs = (pathlib.Path("tests/_files/test-empty"), pathlib.Path("tests/_files/test-full"))

    for db in dbs:
        sql = db.with_suffix(".db.sqlite").read_text()

        if db.with_suffix(".db").exists():
            db.with_suffix(".db").unlink()

        con = sqlite3.connect(db.with_suffix(".db").absolute())
        cur = con.cursor()
        cur.executescript(sql)
        con.close()


@pytest.fixture(scope="module")
def emptyclient():
    jeopardy = web.create_app()
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/_files/test-empty.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.app_context():
        models.db.create_all()

        with jeopardy.test_client() as client:
            yield client

        models.db.drop_all()


@pytest.fixture(autouse=True, scope="session")
def empty_cache_upon_completion():
    yield

    path = pathlib.Path(os.getcwd(), "tests/_files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def empty_cache_after_test():
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
def PatchedRequests(monkeypatch):
    def localGet(uri, *args, **kwargs):
        file = uri.split("/")[-1].replace("?", "_")

        path = pathlib.Path(os.getcwd(), "tests/_files/mock_get", file).absolute()

        if path.exists():
            status_code = 200

            with open(path, "r") as local_file:
                text = local_file.read()

        else:
            status_code = 404

            text = "<html><head></head><body>404 Page Not Found</body></html>"

        mock = type("PatchedRequests", (), {})()
        mock.status_code = status_code
        mock.text = text

        return mock

    monkeypatch.setattr(requests, "get", localGet)


@pytest.fixture
def testclient():
    jeopardy = web.create_app()
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/_files/test-full.db').absolute()}"
    jeopardy.config["TESTING"] = True

    with jeopardy.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def samplecontent(testclient, clean_content):
    data = testclient.get(f"/api/v{config.api_version}/game").get_json()[0]["sets"][0]

    return data, clean_content(data=data)


@pytest.fixture()
def clean_content():
    def _clean(data: dict) -> dict:
        data.update({"year": datetime.datetime.fromisoformat(data["date"]).strftime("%Y"), "wager": False})
        return {k: v for k, v in data.items() if k in ("year", "wager", "answer", "question")}

    return _clean


@pytest.fixture(scope="function")
def samplecategory(testclient):
    data = list()
    category = testclient.get(f"/api/v{config.api_version}/game").get_json()[0]

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


@pytest.fixture
def complete_file():
    with open("tests/_files/complete.json", "r") as sample_file:
        return json.load(sample_file)


@pytest.fixture
def incomplete_file():
    with open("tests/_files/incomplete.json", "r") as sample_file:
        return json.load(sample_file)


@pytest.fixture
def webclient():
    app = web.create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/_files/test-full.db').absolute()}"
    app.config["TESTING"] = True

    socketio = sockets.socketio
    socketio.init_app(app)

    flask = app.test_client()

    yield socketio.test_client(app, flask_test_client=flask), flask
