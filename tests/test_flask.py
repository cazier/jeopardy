import json

import pytest
from flask import request, session
from unittest import mock

from jeopardy import config, storage

def test_home(webclient):
    _, flask = webclient

    rv = flask.get(f"/")
    assert rv.status_code == 200
    assert f"<title>{config.game_name} - Python/WebSocket Trivia!</title>" in rv.get_data(as_text=True)

    rv = flask.post(f"/")
    assert rv.status_code == 405


def test_test(webclient, testclient):
    config.debug = False
    _, flask = webclient
    
    obj = testclient.get(f"/api/v{config.api_version}/game?round=0").get_json()
    data, cleaned = json.dumps(obj), obj

    with flask as c:
        rv = c.get('/test/')
        assert rv.status_code == 302
        assert request.path == '/test/'

        rv = c.get('/test/', follow_redirects = True)
        assert request.path == '/'

    config.debug = True

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        with flask as c:
            rv = c.get('/test/', follow_redirects = True)
            assert request.path == '/test/'
            assert "iframe" in rv.get_data(as_text=True)
    
    config.debug = False
    storage.GAMES = dict()

def test_new(webclient):
    _, flask = webclient

    rv = flask.get('/new/')
    assert rv.status_code == 200
    assert "Number of Categories" in rv.get_data(as_text=True)

    rv = flask.post(f"/")
    assert rv.status_code == 405

def test_join(webclient, testclient):
    _, flask = webclient

    rv = flask.get('/join/')
    assert rv.status_code == 200
    assert "What is the room code?" in rv.get_data(as_text =True)
    assert 'readonly' not in rv.get_data(as_text = True)
    
    assert "ABCD" not in storage.rooms()

    rv = flask.get('/join/ABCD')
    assert rv.status_code == 200
    assert 'readonly' not in rv.get_data(as_text = True)

    storage.GAMES["ABCD"] = True

    rv = flask.get('/join/ABCD')
    assert rv.status_code == 200
    assert 'readonly' in rv.get_data(as_text = True)


# def test_board(webclient, testclient):
#     _, flask = webclient

#     with flask as c:
#         c.session["room"] = "ABCD"
        
#     rv = flask.get('/board/')