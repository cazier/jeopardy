import json
from unittest import mock

from flask import request

from jeopardy import config, storage


def test_home(webclient):
    rv = webclient.flask_test_client.get(f"/")
    assert rv.status_code == 200
    assert f"<title>{config.game_name} - Python/WebSocket Trivia!</title>" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(f"/")
    assert rv.status_code == 405


def test_test(webclient):
    config.debug = False

    obj = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0").get_json()
    data, cleaned = json.dumps(obj), obj

    with webclient.flask_test_client as c:
        rv = c.get("/test/")
        assert rv.status_code == 302
        assert request.path == "/test/"

        rv = c.get("/test/", follow_redirects=True)
        assert request.path == "/"

    config.debug = True

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        with webclient.flask_test_client as c:
            rv = c.get("/test/", follow_redirects=True)
            assert request.path == "/test/"
            assert rv.get_data(as_text=True).count("</iframe>") == 5

    config.debug = False
    storage.GAMES = dict()


def test_new(webclient):
    rv = webclient.flask_test_client.get("/new/")
    assert rv.status_code == 200
    assert "Number of Categories" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(f"/")
    assert rv.status_code == 405


def test_join(webclient):
    rv = webclient.flask_test_client.get("/join/")
    assert rv.status_code == 200
    assert "What is the room code?" in rv.get_data(as_text=True)
    assert "readonly" not in rv.get_data(as_text=True)

    assert "ABCD" not in storage.rooms()

    rv = webclient.flask_test_client.get("/join/ABCD")
    assert rv.status_code == 200
    assert "readonly" not in rv.get_data(as_text=True)

    storage.GAMES["ABCD"] = True

    rv = webclient.flask_test_client.get("/join/ABCD")
    assert rv.status_code == 200
    assert "readonly" in rv.get_data(as_text=True)


def test_host_error(webclient):
    rv = webclient.flask_test_client.get("/host/")
    assert rv.status_code == 500
    assert "An error occurred..." in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.get("/host/?room=BCDE")
    assert rv.status_code == 500


def test_host_get(webclient):

    obj = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data
