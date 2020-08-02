from flask import Flask, Blueprint
from flask_socketio import SocketIO, join_room

import config
import wagers
import storage
from sockets import socketio

rounds = Blueprint(name="rounds", import_name=__name__)


@socketio.on("host_clicked_question-h>s")
def host_clicked_question(data):
    """The host has selected a question from their device.

    Required Arguments: 

    - `data` (dict) - A dictionary containing the information associated with the selected 
    question; the identifier of the question, and the room it was selected from.
    """
    game = storage.pull(data["room"])
    info = game.get(data["identifier"])

    # If the question is not a Daily Double or Final Round (which would require a wager!)
    if not info["wager"]:
        socketio.emit(
            "reveal_standard_question-s>bh",
            {
                "room": data["room"],
                "updates": {
                    "question": info["question"].replace("<br />", "\n"),
                    "answer": info["answer"],
                },
                "identifier": f'#{data[u"identifier"]}',
            },
        )

    # If the question is a DD or in one of the final rounds, need to request a wager prior to
    # showing the
    else:
        wagers.start_wager(game=game)


@socketio.on("finished_reading-h>s")
def enable_buzzers(data, incorrect_players: list = list()):
    """After receiving the `socket.on` that the host has finished reading the question, `socket.emit` the
    signal to enable the buzzers for each player.

    This takes an optional argument `incorrect_players` prohiting players who have already guessed
    incorrectly to try to do so again.
    """
    socketio.emit(
        "enable_buzzers-s>p", {"room": data["room"], "players": incorrect_players}
    )


@socketio.on("buzz_in-p>s")
def player_buzzed_in(data):
    """After receiving the `socket.on` that a player is buzzing in, `socket.emit` the player's name to the
    host.
    """
    game = storage.pull(data["room"])
    game.buzz(data["name"])

    socketio.emit("reset_buzzers-s>p", {"room": data["room"]})

    socketio.emit(
        "player_buzzed-s>h", {"room": data["room"], "name": game.buzz_order[-1],},
    )


@socketio.on("question_answered-h>s")
def question_answered(data):
    """After receiving the `socket.on` that the player guessed an answer, update the game record,
    and `socket.emit` the updated scores to that player and the game board.

    If the player was correct, clean up the board and continue the game. Otherwise, allow the buzzing
    in availability for the remaining players.
    """
    game = storage.pull(data["room"])

    game.score.update(game=game, correct=int(data["correct"]))

    socketio.emit(
        "update_scores-s>bph", {"room": data["room"], "scores": game.score.emit()}
    )

    if data["correct"] or len(game.score) == len(game.buzz_order):
        end_question(data)

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


def end_question(data):
    """Clean up some variables and code whenever a question is completed. Firstly clear the buzzers list
    and the current question, and check to see if the round is over.
    """
    game = storage.pull(data["room"])

    game.buzz_order = list()
    game.current_question = None

    socketio.emit("clear_modal-s>bh", {"room": data["room"]})

    if config.debug:
        print(game.remaining_questions)

    socketio.sleep(0.2)

    if (game.remaining_questions <= 0) and (game.round < 3):
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
