import pytest
import requests


import os
import json
import shutil
import pathlib

from jeopardy_data.tools import scrape
from jeopardy_data import api

scrape.DELAY = 0


@pytest.fixture(scope="module")
def emptyclient():
    jeopardy = api.app
    jeopardy.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{pathlib.Path('tests/files/test-empty.db').absolute()}"
    jeopardy.config["TESTING"] = True

    api.db.create_all()

    with jeopardy.test_client() as client:
        yield client

    api.db.drop_all()


@pytest.fixture(autouse=True, scope="session")
def empty_cache_upon_completion():
    yield

    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def empty_cache_after_test():
    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def test_data():
    with open("tests/files/complete.json", "r") as sample_file:
        data = json.load(sample_file)

    with open("tests/files/incomplete.json", "r") as sample_file:
        data.extend(json.load(sample_file))

    return data


@pytest.fixture
def PatchedRequests(monkeypatch):
    def localGet(uri, *args, **kwargs):
        file = uri.split("/")[-1].replace("?", "_")

        path = pathlib.Path(os.getcwd(), "tests/files/mock_get", file).absolute()

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
def complete_file():
    with open("tests/files/complete.json", "r") as sample_file:
        return json.load(sample_file)


@pytest.fixture
def incomplete_file():
    with open("tests/files/incomplete.json", "r") as sample_file:
        return json.load(sample_file)
