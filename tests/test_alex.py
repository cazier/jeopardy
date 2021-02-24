import json
import urllib
import datetime
from io import BytesIO
from unittest import mock


import pytest

from jeopardy import alex, config


def test_content_creation(samplecontent):
    data, cleaned = samplecontent
    content = alex.Content(details=data, category_index=0)

    assert content.value == data["value"]

    assert content.id() == f"{0}_{data['value']}"

    assert content.shown == False
    assert content.get() == cleaned
    assert content.shown == True

    assert content.get_content() == content

    class Sample(object):
        value = content.value + 200

    sample = Sample()

    assert content < sample


def test_category_creation(samplecategory):
    data, cleaned = samplecategory

    category = alex.Category(name=data["category"]["name"], index=0, sets=data["sets"])

    assert category.category == str(category) == repr(category) == data["category"]["name"]
    assert category.index == 0

    assert len(category.sets) == len(cleaned)
    assert (category.sets[0].value == 0) & (category.sets[-1].value == 4)


def test_board_creation_r0(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=0").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=0, settings={})

    board.add_wagers()

    assert board.round == 0
    assert set({i.category for i in board.categories}) == {i["category"]["name"] for i in cleaned}
    assert sum([j.wager for i in board.categories for j in i.sets]) == 1


def test_board_creation_r1(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=1").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=1, settings={})

    board.add_wagers()

    assert sum([j.wager for i in board.categories for j in i.sets]) == 2


def test_board_creation_r2(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=2&size=1").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=2, settings={})

    assert len(board.categories) == 1


def test_board_creation_debug(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=1").get_json()
    data, cleaned = json.dumps(obj), obj

    config.debug = True

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=1, settings={})

    board.add_wagers()

    assert board.round == 1
    assert sum([j.wager for i in board.categories for j in i.sets]) == 1
    assert board.categories[0].sets[0].wager == True

    config.debug = False


def test_board_creation_400(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=3").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(data.encode("utf-8")), code=400
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert board.message == cleaned["message"]


def test_board_creation_404(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/404").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(data.encode("utf-8")), code=404
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert (
        board.message
        == "An error occurred finding the API. Please try restarting the server, or check your configuration."
    )


def test_board_creation_500(testclient):
    obj = testclient.get(f"/api/v{config.api_version}/500").get_json()
    data, cleaned = json.dumps(obj), obj

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(data.encode("utf-8")), code=500
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert board.message == "An unknown error occurred. Please submit a bug report with details!"


def test_game_creation(testclient, clean_content):
    obj = testclient.get(f"/api/v{config.api_version}/game?round=0&size=6").get_json()
    data, cleaned = json.dumps(obj), obj
    content = clean_content(cleaned[0]["sets"][0])

    game = alex.Game(game_settings={"size": 6, "room": "ABCD"})

    assert game.score.players == {}
    game.add_player("Test")
    assert game.score.players == {"Test": {"score": 0, "wager": {"amount": 0, "question": ""}}}

    assert game.round_text() == f"{config.game_name}!"
    assert game.round_text(upcoming=True) == f"Double {config.game_name}!"
    assert game.heading() == "Daily Double!"

    with pytest.raises(AttributeError):
        game.board
        game.remaining_content

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        game.make_board()

    assert (len(game.board.categories) == 6) & (len(game.board.categories) * 5 == game.remaining_content)

    # In case random wager assignment went to `q_0_0`
    assert (game.get("q_0_0") == content) or (game.get("q_0_0") == {**content, **{"wager": True}})

    assert game.round == 0

    # Second Round
    obj = testclient.get(f"/api/v{config.api_version}/game?round=1&size=6").get_json()
    data, cleaned = json.dumps(obj), obj
    content = clean_content(cleaned[0]["sets"][0])

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        game.start_next_round()

    assert game.round == 1
    assert game.round_text() == f"Double {config.game_name}!"
    assert game.round_text(upcoming=True) == f"Final {config.game_name}!"

    html_board = list(game.html_board())
    assert (len(game.board.categories) == 6) & (len(game.board.categories[0].sets) == 5)
    assert (len(html_board) == 5) & (len(html_board[0]) == 6)

    assert game.get("a_0_0") == False

    assert game.buzz_order == dict()
    game.buzz({"name": "Test", "time": 1000})
    game.buzz({"name": "False", "time": 2000})
    assert game.buzz_order == {"Test": {"time": 1000, "allowed": True}}

    obj = testclient.get(f"/api/v{config.api_version}/game?round=2&size=1").get_json()
    data, cleaned = json.dumps(obj), obj

    # Final Round
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        game.start_next_round()

    assert game.round == 2
    assert game.round_text() == f"Final {config.game_name}!"
    assert game.round_text(upcoming=True) == f"Tiebreaker {config.game_name}!"
    assert game.heading() == f"Final {config.game_name}!"

    # Checking for no round 4
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        game.start_next_round()

    assert game.round == 3
    assert game.round_text(upcoming=True) == "An error has occurred...."


def test_game_creation_debug(testclient):
    config.debug = True

    obj = testclient.get(f"/api/v{config.api_version}/game?round=0&size=6").get_json()
    data, cleaned = json.dumps(obj), obj

    game = alex.Game(game_settings={"size": 6, "room": "ABCD"})

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = data

        game.make_board()

    assert game.score.players == {
        "Alex": {"score": 1500, "wager": {"amount": 0, "question": ""}},
        "Brad": {"score": 500, "wager": {"amount": 0, "question": ""}},
        "Carl": {"score": 750, "wager": {"amount": 0, "question": ""}},
    }

    assert game.board.categories[0].sets[0].wager == True
