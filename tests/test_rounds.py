import concurrent.futures

import pytest

from jeopardy import config, storage
from tests.conftest import gen_room, webclient


@pytest.fixture(scope="class")
def client(app_factory):
    config.debug = False
    yield from webclient.__wrapped__(app_factory)


@pytest.fixture(scope="class")
def room(client, players):
    _room = gen_room.__wrapped__(client)()
    _game = storage.pull(_room)
    for score, name in enumerate(players, start=1):
        _game.add_player(name)
        _game.score.players[name]["score"] = 1500 // score

    return _room


@pytest.fixture(scope="class")
def players():
    return {"Alex", "Brad", "Carl"}


@pytest.fixture(scope="function")
def game(room):
    return storage.pull(room)


@pytest.fixture(scope="class")
def ids(client, room):
    game = storage.pull(room)

    _ids = {"standard": list(), "wager": list()}

    for category in range(6):
        for value in range(5):
            if (_id := (category, value)) in game.board.daily_doubles:
                _ids["wager"].append(_id)
            else:
                _ids["standard"].append(_id)

    return _ids


def get_qa(game, identifier) -> dict:
    return game.board.categories[identifier[0]].sets[identifier[1]]


@pytest.mark.incremental
class TestRounds:
    @pytest.fixture(scope="class", autouse=True)
    def _setup(self, client, room):
        client.emit("join", {"room": room})

    @pytest.fixture(scope="function", autouse=True)
    def _setup_function(self, client):
        # Empty message log
        client.get_received()

        yield

    def test_host_selected_answer(self, client, room, game, ids):
        assert len(ids["standard"]) > 0
        num = ids["standard"].pop()

        identifier = f"q_{num[0]}_{num[1]}"
        content = get_qa(game, num)

        client.emit("host_clicked_answer-h>s", {"identifier": identifier}, to=room)
        messages = client.get_received()

        assert (
            messages[0]["name"] == "disable_question-s>b" and {"identifier": f"#{identifier}"} in messages[0]["args"]
        )

        assert (
            messages[1]["name"] == "reveal_standard_set-s>bh"
            and messages[1]["args"][0]["updates"]["question"] == content.question
        )

        client.emit("host_clicked_answer-h>s", {"identifier": identifier}, to=room)
        messages = client.get_received()

        assert (
            messages[0]["name"] == "error-s>bph"
            and {"message": "The selection has already been revealed."} in messages[0]["args"]
        )

    def test_enable_buzzers(self, client, room):
        client.emit("finished_reading-h>s", to=room)

        messages = client.get_received()

        assert messages[0]["name"] == "enable_buzzers-s>p" and messages[0]["args"][0]["except_players"] == []

    def test_dismiss(self, client, room):
        client.emit("dismiss-h>s", to=room)

        messages = client.get_received()

        assert messages[0]["name"] == "reset_buzzers-s>p"
        assert messages[1]["name"] == "clear_modal-s>bh"

    def test_player_buzzed_in(self, client, room, players):
        client.emit("buzz_in-p>s", {"name": list(players)[0], "time": 0.1}, to=room)

        messages = client.get_received()

        assert messages[0]["name"] == "reset_buzzers-s>p"
        assert messages[1]["name"] == "player_buzzed-s>h" and messages[1]["args"][0]["name"] == list(players)[0]

    def test_players_buzzed_in(self, client, room, players):
        def buzz(name, time):
            client.emit("buzz_in-p>s", {"name": name, "time": time}, to=room)

        def done(results):
            return concurrent.futures.wait(results, return_when="ALL_COMPLETED")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = [executor.submit(buzz, player, time) for time, player in enumerate(players)]

        done(results)

        messages = client.get_received()
        assert messages[1]["name"] == "player_buzzed-s>h" and messages[1]["args"][0]["name"] == list(players)[0]

    def test_host_selected_wager(self, client, room, players, ids):
        assert len(ids["wager"]) > 0
        num = ids["wager"].pop()

        identifier = f"q_{num[0]}_{num[1]}"

        client.emit("host_clicked_answer-h>s", {"identifier": identifier}, to=room)
        messages = client.get_received()

        assert (
            messages[0]["name"] == "disable_question-s>b" and {"identifier": f"#{identifier}"} in messages[0]["args"]
        )

        assert messages[1]["name"] != "reveal_standard_set-s>bh"
        assert messages[1]["name"] == "start_wager_round-s>bh" and set(messages[1]["args"][0]["players"]) == players
