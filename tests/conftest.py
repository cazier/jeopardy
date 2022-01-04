import os
import json
import shutil
import pathlib
import sqlite3
import datetime
from urllib import request as urllib_request

import pytest
from flask import request, url_for, wrappers

from jeopardy import web, config, sockets, storage


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


@pytest.fixture(scope="session")
def app_factory():
    def func(db):
        app = web.create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/_files/test').absolute()}-{db}.db"
        app.config["TESTING"] = True

        return app

    return func


@pytest.fixture
def webclient(app_factory):
    backup = urllib_request.urlopen

    class mocked_urlopen:
        def __init__(self, url: str) -> None:
            self.page = client.flask_test_client.get(url)

        def read(self):
            return bytes(self.page.get_data(as_text=True), encoding="utf-8")

    urllib_request.urlopen = mocked_urlopen

    app = app_factory("full")

    socketio = sockets.socketio
    socketio.init_app(app)

    flask = app.test_client()

    with app.test_request_context() as ctx:
        client = socketio.test_client(app, flask_test_client=flask)

        yield client

    urllib_request.urlopen = backup


@pytest.fixture
def emptyclient(app_factory):
    app = app_factory("empty")

    with app.app_context():
        with app.test_client() as client:
            yield client


@pytest.fixture(scope="session", autouse=True)
def patch_socketio():
    class mocked_request(wrappers.Request):
        def __init__(self, *args, **kwargs):
            self.namespace = "/"
            super().__init__(*args, **kwargs)

    @sockets.socketio.on("connect")
    def on_connect(json):
        sockets.socketio.sid = request.sid

    import flask

    backup = wrappers.Request

    flask.Flask.request_class = mocked_request

    yield

    flask.Flask.request_class = backup


@pytest.fixture
def gen_room(webclient):
    def func():
        _rooms = set(storage.GAMES.keys())

        rv = webclient.flask_test_client.post(
            url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": 6}, follow_redirects=True
        )
        assert rv.status_code == 200
        assert len(storage.GAMES) > 0

        return [i for i in storage.GAMES.keys() if i not in _rooms][0]

    return func


@pytest.fixture(scope="function", autouse=True)
def _setup_teardown():
    yield

    config.debug = False
