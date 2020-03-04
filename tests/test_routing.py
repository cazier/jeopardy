import os
import tempfile

import pytest
from flask import Flask, request

import help_test

import web
import routing


@pytest.fixture
def client():
    app = web.app
    app.config[u"TESTING"] = True

    with app.test_client() as client:
        yield client


def test_route_index(client):
    page = client.get(u"/")

    assert page.data is not None
    assert b"Start a New Game!" in page.data


def test_route_new(client):
    page = client.get(u"/new")

    assert page.data is not None
    assert b"Game Settings" in page.data


def test_route_join(client):
    page = client.get(u"/join")

    assert page.data is not None
    assert b"Player Settings" in page.data


def test_route_host_get(client):
    client.get(u"/test")
    page = client.get(u"/host?room=ABCD")

    assert page.data is not None
    assert b"var type = 'host';" in page.data
    assert request.args[u"room"] == u"ABCD"


def test_route_player_get(client):
    page = client.get(u"/play?room=ABCD&name=Alex")

    assert page.data is not None
    assert b"var type = 'player';" in page.data
    assert request.args[u"name"] == u"Alex"


def test_route_board_get(client):
    page = client.get(u"/board?room=ABCD")

    assert page.data is not None
    assert b"var type = 'board';" in page.data
    assert request.args[u"room"] == u"ABCD"

def test_route_test(client):


def test_generate_room_code():
    room = routing.generate_room_code()

    assert type(room) == str
    assert len(room) == 4
    assert " " not in room

