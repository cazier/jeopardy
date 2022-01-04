import random

import pytest
from flask import url_for

from jeopardy import config, routing, storage


@pytest.fixture(scope="function", autouse=True)
def _setup():
    yield

    storage.GAMES.clear()


@pytest.fixture
def patch_random_sample():
    _old = random.sample

    def func():
        result = ["0000", "1111"]

        def _new(iterable, num):
            return result.pop(0)

        random.sample = _new

    yield func

    random.sample = _old


def test_route_index(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_index"))
    assert rv.status_code == 200
    assert f"<h2>Welcome to {config.game_name}!</h2>" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(url_for("routing.route_index"))
    assert rv.status_code == 405


def test_route_test(webclient):
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


def test_route_host_post(webclient, gen_room):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_host"), headers={"Referer": "/new/"}, data={"size": 6}, follow_redirects=True
    )
    assert rv.get_data(as_text=True).count('class="card-header" id="category_') == 6

    room = gen_room()
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


def test_route_host_get(webclient):
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


def test_route_host_error(webclient):
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


def test_route_play_post(webclient, gen_room):
    room = gen_room()

    rv = webclient.flask_test_client.post(
        url_for("routing.route_play"), data={"room": room, "name": "Player"}, follow_redirects=True
    )

    assert room in rv.get_data(as_text=True)
    assert "<h2>Hey Player!</h2>" in rv.get_data(as_text=True)


def test_route_play_get(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_play"), follow_redirects=True)
    assert rv.history[-1].request.path == "/play/"
    assert rv.request.path == "/join/"

    config.debug = True

    rv = webclient.flask_test_client.get(url_for("routing.route_test"), follow_redirects=True)
    assert rv.status_code == 200

    rv = webclient.flask_test_client.get(
        url_for("routing.route_play", room="ABCD", name="Test"), headers={"Referer": "/test/"}, follow_redirects=True
    )
    assert "<h2>Hey Test!</h2>" in rv.get_data(as_text=True)


def test_route_play_error(webclient, gen_room):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_play"), data={"room": "TEST", "name": "Player"}, follow_redirects=True
    )

    assert "invalid or missing" in rv.get_data(as_text=True)
    assert rv.request.path == "/join/"

    room = gen_room()

    for name in ("", " ", "\n", "\t"):
        rv = webclient.flask_test_client.post(
            url_for("routing.route_play"), data={"room": room, "name": name}, follow_redirects=True
        )

        assert "name entered is invalid" in rv.get_data(as_text=True)
        assert rv.request.path == f"/join/{room}"

    for _ in range(2):
        rv = webclient.flask_test_client.post(
            url_for("routing.route_play"), data={"room": room, "name": "Player"}, follow_redirects=True
        )

    assert "selected already exists" in rv.get_data(as_text=True)
    assert rv.request.path == f"/join/{room}"


def test_route_board_post(webclient, gen_room):
    room = gen_room()

    rv = webclient.flask_test_client.post(url_for("routing.route_board"), data={"room": room}, follow_redirects=True)

    assert room in rv.get_data(as_text=True)
    assert "<h4>Scores!</h4>" in rv.get_data(as_text=True)


def test_route_board_get(webclient, gen_room):
    rv = webclient.flask_test_client.get(url_for("routing.route_board"), follow_redirects=True)
    assert rv.history[-1].request.path == "/board/"
    assert rv.request.path == "/join/"

    config.debug = True

    rv = webclient.flask_test_client.get(url_for("routing.route_test"), follow_redirects=True)
    assert rv.status_code == 200

    rv = webclient.flask_test_client.get(
        url_for("routing.route_board", room="ABCD"), headers={"Referer": "/test/"}, follow_redirects=True
    )
    assert "<h4>Scores!</h4>" in rv.get_data(as_text=True)


def test_route_board_error(webclient):
    rv = webclient.flask_test_client.post(url_for("routing.route_board"), data={"room": "TEST"}, follow_redirects=True)

    assert "invalid or missing" in rv.get_data(as_text=True)
    assert rv.request.path == "/join/"


def test_route_results_post(webclient, gen_room):
    room = gen_room()
    game = storage.pull(room)

    for score, name in enumerate(("Brad", "Alex")):
        game.add_player(name)
        game.score.players[name]["score"] = (score + 1) * 500

    storage.push(room, game)

    rv = webclient.flask_test_client.post(url_for("routing.route_results"), data={"room": room}, follow_redirects=True)
    assert "<h1>Congratulations!</h1>" in rv.get_data(as_text=True)
    assert "// Start spraying confetti" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(
        url_for("routing.route_results"), data={"room": room, "name": "Alex"}, follow_redirects=True
    )
    assert "// Start spraying confetti" in rv.get_data(as_text=True)

    rv = webclient.flask_test_client.post(
        url_for("routing.route_results"), data={"room": room, "name": "Brad"}, follow_redirects=True
    )
    assert "// Start spraying confetti" not in rv.get_data(as_text=True)


def test_route_results_get(webclient):
    rv = webclient.flask_test_client.get(url_for("routing.route_results"), follow_redirects=True)
    assert rv.history[-1].request.path == url_for("routing.route_results")
    assert rv.request.path == url_for("routing.route_index")

    config.debug = True

    rv = webclient.flask_test_client.get(url_for("routing.route_results"), follow_redirects=True)
    assert rv.request.path == url_for("routing.route_results")
    assert "<h1>Congratulations!</h1>" in rv.get_data(as_text=True)
    assert "// Start spraying confetti" in rv.get_data(as_text=True)


def test_route_results_error(webclient):
    rv = webclient.flask_test_client.post(
        url_for("routing.route_results"), data={"room": "TEST"}, follow_redirects=True
    )

    assert "invalid or missing" in rv.get_data(as_text=True)
    assert rv.request.path == "/join/"


def test_generate_room_code(patch_random_sample):
    room = routing.generate_room_code()
    assert len(room) == 4 and room.isupper() and room.isalpha()

    patch_random_sample()
    storage.GAMES["0000"] = True
    assert routing.generate_room_code() == "1111"

    config.debug = True
    assert routing.generate_room_code() == "ABCD"
