import json
import urllib
import hashlib
from io import BytesIO
from unittest import mock

import pytest

from jeopardy import alex, config


def test_safe_name():
    name = "Test"
    assert alex.safe_name(name) == hashlib.md5(name.encode("utf-8")).hexdigest()

    name = "Test With Spaces"
    assert " " not in alex.safe_name(name)

    name = "Test %20 Special Characters $%^&;"
    assert alex.safe_name(name).isalnum()


def test_content_creation(samplecontent):
    data, cleaned = samplecontent

    content = alex.Content(data["value"], data["answer"], data["question"], data["date"], 0)

    assert content.value == data["value"]

    assert content.id == f"{0}_{data['value']}"

    assert content.shown == False
    assert content.question == cleaned["question"]
    assert content.shown == True

    sample = alex.Content(content.value + 200, data["answer"], data["question"], data["date"], 0)

    assert content < sample


def test_category_creation(samplecategory):
    data, cleaned = samplecategory

    category = alex.Category(name=data["category"]["name"], index=0, sets=data["sets"])

    assert category.category == str(category) == repr(category) == data["category"]["name"]
    assert category.index == 0

    assert len(category.sets) == len(cleaned)
    assert (category.sets[0].value == 0) & (category.sets[-1].value == 4)


def test_board_creation_r0(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=0, settings={})

    board.add_wagers()

    assert board.round == 0
    assert set({i.category for i in board.categories}) == {i["category"]["name"] for i in data}
    assert sum([j.is_wager for i in board.categories for j in i.sets]) == 1


def test_board_creation_r1(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=1").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=1, settings={})

    board.add_wagers()

    assert sum([j.is_wager for i in board.categories for j in i.sets]) == 2


def test_board_creation_r2(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=2&size=1").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=2, settings={})

    assert len(board.categories) == 1


def test_board_creation_debug(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=1").get_json()

    config.debug = True

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=1, settings={})

    board.add_wagers()

    assert board.round == 1
    assert sum([j.is_wager for i in board.categories for j in i.sets]) == 1
    assert board.categories[0].sets[0].is_wager == True


def test_board_creation_400(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=3").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(json.dumps(data).encode("utf-8")), code=400
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert board.message == data["message"]


def test_board_creation_404(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/404").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(json.dumps(data).encode("utf-8")), code=404
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert (
        board.message
        == "An error occurred finding the API. Please try restarting the server, or check your configuration."
    )


def test_board_creation_500(webclient):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/500").get_json()

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", msg="", hdrs="", fp=BytesIO(json.dumps(data).encode("utf-8")), code=500
        )
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        board = alex.Board(round_=0, settings={})

    assert board.build_error == True
    assert board.message == "An unknown error occurred. Please submit a bug report with details!"


def test_game_creation(webclient, clean_content):
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0&size=6").get_json()
    content = clean_content(data[0]["sets"][0])

    game = alex.Game(game_settings={"size": 6, "room": "ABCD"})

    assert game.score.players == {}
    game.add_player("Test")
    assert game.score.players == {
        "Test": {
            "safe": alex.safe_name("Test"),
            "score": 0,
            "wager": {"amount": 0, "question": ""},
        }
    }

    assert game.round_text() == f"{config.game_name}!"
    assert game.round_text(upcoming=True) == f"Double {config.game_name}!"
    assert game.heading() == "Daily Double!"

    with pytest.raises(AttributeError):
        game.board
        game.remaining_content

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        game.make_board()

    assert (len(game.board.categories) == 6) & (len(game.board.categories) * 5 == game.remaining_content)

    assert game.get("q_0_0").question == content["question"]

    assert game.round == 0

    # Second Round
    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=1&size=6").get_json()
    content = clean_content(data[0]["sets"][0])

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

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

    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=2&size=1").get_json()

    # Final Round
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        game.start_next_round()

    assert game.round == 2
    assert game.round_text() == f"Final {config.game_name}!"
    assert game.round_text(upcoming=True) == f"Tiebreaker {config.game_name}!"
    assert game.heading() == f"Final {config.game_name}!"

    # Checking for no round 4
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        game.start_next_round()

    assert game.round == 3
    assert game.round_text(upcoming=True) == "An error has occurred...."


def test_game_creation_debug(webclient):
    config.debug = True

    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0&size=6").get_json()

    game = alex.Game(game_settings={"size": 6, "room": "ABCD"})

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        game.make_board()

    assert game.score.players == {
        "Alex": {
            "safe": alex.safe_name("Alex"),
            "score": 1500,
            "wager": {"amount": 0, "question": ""},
        },
        "Brad": {
            "safe": alex.safe_name("Brad"),
            "score": 500,
            "wager": {"amount": 0, "question": ""},
        },
        "Carl": {
            "safe": alex.safe_name("Carl"),
            "score": 750,
            "wager": {"amount": 0, "question": ""},
        },
    }

    assert game.board.categories[0].sets[0].is_wager == True


def test_scoreboard_creation():
    board = alex.Scoreboard()
    assert board.player_exists("test") == False
    board.add("test")
    assert board.player_exists("test") == True

    assert len(board) == 1
    assert board["test"] == 0
    board.add("second")

    assert {k: v["score"] for k, v in board.emit().items()} == {"test": 0, "second": 0}


def test_scoreboard_updates():
    names = ["first", "second"]

    game = mock.Mock()
    game.round = 0
    game.current_set.value = 0
    game.buzz_order = {j: {"time": 1000 * i, "allowed": True} for i, j in enumerate(names)}

    score = alex.Scoreboard()
    for i in names:
        score.add(i)
    assert score.keys() == names

    assert score.players["first"]["score"] == 0
    score.update(game=game, correct=0)

    assert score.players["first"]["score"] == -200

    score.wagerer = "second"
    score.players["second"]["wager"]["amount"] = 1000
    score.update(game=game, correct=1)

    assert score.players["second"]["score"] == 1000


def test_scoreboard_methods():
    names = ["first", "second"]

    score = alex.Scoreboard()
    for i in names:
        score.add(i)
    assert score.keys() == names

    score.players["first"]["score"] = 500
    assert score.sort() == names[::-1]

    score.players["second"]["score"] = 1000
    assert score.sort() == names

    score["first"] = ("amount", 1000)
    score["first"] = ("question", "response")
    assert score.wager("first") == {"amount": 1000, "player": "first", "question": "response", "score": 500}


def test_game_reset(webclient):
    config.debug = True

    data = webclient.flask_test_client.get(f"/api/v{config.api_version}/game?round=0&size=6").get_json()

    game = alex.Game(game_settings={"size": 6, "room": "ABCD"})

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.read.return_value.decode.return_value = json.dumps(data)

        game.make_board()

    game.score.reset("score")

    assert game.score.players == {
        "Alex": {
            "safe": alex.safe_name("Alex"),
            "score": 0,
            "wager": {"amount": 0, "question": ""},
        },
        "Brad": {
            "safe": alex.safe_name("Brad"),
            "score": 0,
            "wager": {"amount": 0, "question": ""},
        },
        "Carl": {
            "safe": alex.safe_name("Carl"),
            "score": 0,
            "wager": {"amount": 0, "question": ""},
        },
    }

    game.score.reset("players")

    assert game.score.players == {}
