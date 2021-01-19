import os
import tempfile

import pytest
from flask import Flask, request

import help_test

import web
import routing


@pytest.fixture
def get_client():
    app = web.app
    app.config[u"TESTING"] = True

    with app.test_client() as get_client:
        yield get_client


@pytest.fixture
def post_client():
    app = web.app
    app.config[u"TESTING"] = True
    with app.test_client() as post_client:
        yield post_client


def test_route_index(get_client):
    """Testing function for the index page template (`index.html`). Uses the `test_client()` pytest fixture."""
    page = get_client.get(u"/")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"Start a New Game!" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data


def test_route_new(get_client):
    """Testing function for the new game template (`new.html`). Uses the `test_client()` pytest fixture.

    This only performs a check of the GET request.
    """
    page = get_client.get(u"/new")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"Game Settings" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data


def test_route_join(get_client):
    """Testing function for the join game template (`join.html`). Uses the `test_client()` pytest fixture.

    This only performs a check of the GET request.
    """
    page = get_client.get(u"/join")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"Player Settings" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data


def test_route_host_get(get_client):
    """Testing function for the host game template (`host.html`). Uses the `test_client()` pytest fixture.

    This only performs a check of the GET request. Additionally, it requires rendering of the `/test` endpoint
    to create the sample room. Full blown testing would probably do better at this.
    """
    get_client.get(u"/test")
    page = get_client.get(u"/host?room=ABCD")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"var type = 'host';" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data

    # Ensure request arguments are received and "calculated"
    assert request.args[u"room"] == u"ABCD"


def test_route_player_get(get_client):
    """Testing function for the player game template (`play.html`). Uses the `test_client()` pytest fixture.

    This only performs a check of the GET request.

    Additionally, it requires rendering of the `/test` endpoint to create the sample room. Use of the
    client/pytest fixture means this uses the existing `/test` pull from `test_route_host_get()`
    """
    page = get_client.get(u"/play?room=ABCD&name=Alex")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"var type = 'player';" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data

    # Ensure request arguments are received and "calculated"
    assert request.args[u"name"] == u"Alex"


def test_route_board_get(get_client):
    """Testing function for the player game template (`play.html`). Uses the `test_client()` pytest fixture.

    This only performs a check of the GET request.

    Additionally, it requires rendering of the `/test` endpoint to create the sample room. Use of the
    client/pytest fixture means this uses the existing `/test` pull from `test_route_host_get()`
    """
    page = get_client.get(u"/board?room=ABCD")

    # Ensure page is not empty
    assert page.data is not None

    # Ensure page is GETed
    assert request.method == u"GET"

    # Ensure text unique to that page is rendered
    assert b"var type = 'board';" in page.data

    # Ensure page context is updated
    assert b"{{ game_name }}" not in page.data

    # Ensure request arguments are received and "calculated"
    assert request.args[u"room"] == u"ABCD"


def test_route_host_post(post_client):
    resp = post_client.post("/host", data={"categories": 6})

    from pprint import pprint

    pprint(request.form)
    # assert data is not None


def test_generate_room_code():
    """Testing room code generation function"""
    room = routing.generate_room_code()

    assert type(room) == str
    assert len(room) == 4
    assert room.isalpha() == True
