import re

import pytest
from flask import url_for

from jeopardy import config, storage


@pytest.fixture(scope="function", autouse=True)
def _setup():
    config.debug = False
    storage.GAMES.clear()

    yield


def test_route_index(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_index"))
    assert rv.status_code == 200
    assert f"<h2>Welcome to {config.game_name}!</h2>" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(url_for("routing.route_index"))
    assert rv.status_code == 405


def test_route_test(webclient, patch_urlopen):
    rv = webclient.flask_test_client.get(url_for("routing.route_test"))
    assert rv.status_code == 302
    assert rv.request.path == "/test/"

    rv = webclient.flask_test_client.get(url_for("routing.route_test"), follow_redirects=True)
    assert rv.request.path == "/"

    config.debug = True

    rv = webclient.flask_test_client.get(url_for("routing.route_test"), follow_redirects=True)
    assert rv.request.path == "/test/"
    assert rv.get_data(as_text=True).count("</iframe>") == 5


def test_route_new(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_new"))
    assert rv.status_code == 200
    assert "<h2>Let's start a new game!</h2>" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(url_for("routing.route_index"))
    assert rv.status_code == 405


def test_route_join(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_join"))
    assert rv.status_code == 200
    assert "<h2>Ready to join a game?</h2>" in rv.get_data(as_text=True)
    assert "readonly" not in rv.get_data(as_text=True)  # No Magic Link

    rv = webclient.flask_test_client.get(url_for("routing.route_join", room="TEST"))
    assert "readonly" not in rv.get_data(as_text=True)  # BAD Magic Link

    storage.GAMES["TEST"] = True

    rv = webclient.flask_test_client.get(url_for("routing.route_join", room="Test"))
    assert "readonly" in rv.get_data(as_text=True)  # GOOD Magic Link

    rv = webclient.flask_test_client.get(url_for("routing.route_join", room="test"))
    assert "readonly" in rv.get_data(as_text=True)  # Lowercase good magic link


def test_route_host_post(webclient, patch_urlopen):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": 6}, follow_redirects=True
    )
    assert rv.get_data(as_text=True).count('class="card-header" id="category_') == 6

    room = list(storage.GAMES.keys())[0]
    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/join/"}, data={"room": room}, follow_redirects=True
    )
    assert room in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": 3}, follow_redirects=True
    )
    assert rv.get_data(as_text=True).count('class="card-header" id="category_') == 3

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"),
        headers={"Referer": "/new/"},
        data={"size": 6, "start": 1000, "stop": 9999},
        follow_redirects=True,
    )
    assert rv.get_data(as_text=True).count('class="card-header" id="category_') == 6


def test_route_host_get(webclient, patch_urlopen):
    rv = webclient.flask_test_client.get(url_for("routing.route_host"), follow_redirects=True)
    assert rv.history[-1].request.path == "/host/"
    assert rv.request.path == "/join/"

    config.debug = True

    rv = webclient.flask_test_client.get(url_for("routing.route_test"), follow_redirects=True)
    assert rv.status_code == 200

    rv = webclient.flask_test_client.get(
        url_for("routing.route_host", room="ABCD"), headers={"Referer": "/test/"}, follow_redirects=True
    )
    assert rv.get_data(as_text=True).count('class="card-header" id="category_') == 6


def test_route_host_redirects(webclient, patch_urlopen):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/join/"}, data={"room": "    "}, follow_redirects=True
    )
    assert "invalid or missing" in rv.get_data(as_text=True)
    assert rv.request.path == "/join/"

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": "size"}, follow_redirects=True
    )
    assert "The board size must be a number" in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"),
        headers={"Referer": "/new/"},
        data={"size": 6, "start": 1964},
        follow_redirects=True,
    )
    assert "include both a start and stop year" in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"),
        headers={"Referer": "/new/"},
        data={"size": 6, "stop": 1964},
        follow_redirects=True,
    )
    assert "include both a start and stop year" in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": 25}, follow_redirects=True
    )
    assert "categories were found. Please reduce the size." in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"


def test_route_host_error(webclient):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), data={}, headers={"Referer": "/join/"}, follow_redirects=True
    )
    assert "An error occurred joining the room" in rv.get_data(as_text=True)
    assert rv.request.path == "/join/"

    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), data={}, headers={"Referer": "/new/"}, follow_redirects=True
    )
    assert "An error occurred creating the game" in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"

    rv = webclient.flask_test_client.post(url_for("routing.route_host"), data={}, follow_redirects=True)
    assert "An error occurred trying to access a game" in rv.get_data(as_text=True)
    assert rv.request.path == "/new/"
