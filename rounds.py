from flask import Blueprint
from sockets import socketio

import config
import wagers
import storage

rounds = Blueprint(name="rounds", import_name=__name__)


@socketio.on("host_clicked_answer-h>s")
def host_clicked_answer(data):
    """The host has selected an answer from their device.

    Required Arguments:

    - `data` (dict) - A dictionary containing the information associated with the selected
    set; the identifier of the set, and the room it was selected from.
    """
    game = storage.pull(data["room"])
    info = game.get(data["identifier"])

    socketio.emit(
        "disable_question-s>b",
        {
            "room": data["room"],
            "identifier": f'#{data[u"identifier"]}',
        },
    )

    # If the set is not a Daily Double or Final Round (which would require a wager!)
    if not info["wager"]:
        socketio.emit(
            "reveal_standard_set-s>bh",
            {
                "room": data["room"],
                "updates": {
                    "question": info["question"].replace("<br />", "\n"),
                    "answer": info["answer"].replace("<br />", "\n"),
                },
            },
        )

    # If the set is a DD or in one of the final rounds, need to request a wager prior to
    # showing the
    else:
        wagers.start_wager(game=game)


@socketio.on("finished_reading-h>s")
def enable_buzzers(data, incorrect_players: list = list()):
    """After receiving the `socket.on` that the host has finished reading the answer, `socket.emit` the
    signal to enable the buzzers for each player.

    This takes an optional argument `incorrect_players` prohiting players who have already guessed
    incorrectly to try to do so again.
    """
    socketio.emit("enable_buzzers-s>p", {"room": data["room"], "players": incorrect_players})


@socketio.on("dismiss-h>s")
def dismiss(data):
    """After receiving the `socket.on` that the host has determined no one wants to buzz in, `socket.emit` the signal to dismiss the set and return to the game board."""

    socketio.emit("reset_buzzers-s>p", {"room": data["room"]})

    end_set(data=data)


@socketio.on("buzz_in-p>s")
def player_buzzed_in(data):
    """After receiving the `socket.on` that a player is buzzing in, `socket.emit` the player's name to the
    host.
    """
    game = storage.pull(data["room"])
    game.buzz(data["name"])

    socketio.emit("reset_buzzers-s>p", {"room": data["room"]})

    socketio.emit(
        "player_buzzed-s>h",
        {
            "room": data["room"],
            "name": game.buzz_order[-1],
        },
    )


@socketio.on("response_given-h>s")
def response_given(data):
    """After receiving the `socket.on` that the player gave a response, update the game record,
    and `socket.emit` the updated scores to that player and the game board.

    If the player was correct, clean up the board and continue the game. Otherwise, allow the buzzing
    in availability for the remaining players.
    """
    game = storage.pull(data["room"])

    game.score.update(game=game, correct=int(data["correct"]))

    socketio.emit("update_scores-s>bph", {"room": data["room"], "scores": game.score.emit()})

    if data["correct"] or len(game.score) == len(game.buzz_order):
        end_set(data)

    else:
        enable_buzzers(data, incorrect_players=game.buzz_order)


@socketio.on("start_next_round-h>s")
def start_next_round(data):
    """After receiving the `socket.on` that the host has clicked to start the next round, run
    the game logic that does so, and then `socket.emit` to the board and host to move on.
    """
    game = storage.pull(data["room"])

    game.start_next_round()

    socketio.emit("next_round_started-s>bh")


def end_set(data):
    """Clean up some variables and code whenever a set is completed. Firstly clear the buzzers list
    and the current set, and check to see if the round is over.
    """
    game = storage.pull(data["room"])

    game.buzz_order = list()
    game.current_set = None

    socketio.emit("clear_modal-s>bh", {"room": data["room"]})

    if config.debug:
        print(game.remaining_content)

    socketio.sleep(0.5)

    if (game.remaining_content <= 0) and (game.round < 3):
        socketio.emit(
            "round_complete-s>bh",
            {
                "room": data["room"],
                "updates": {
                    "current_round": game.round_text(),
                    "next_round": game.round_text(upcoming=True),
                },
            },
        )

    elif game.round == 3:
        socketio.emit("results-page-s>bph")
