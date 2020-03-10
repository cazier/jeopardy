import time

from flask import Flask, Blueprint
from flask_socketio import SocketIO, join_room

import config
import storage

rounds = Blueprint(name="rounds", import_name=__name__)

socketio = SocketIO()


@socketio.on("host_clicked_question_h-s")
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
            "reveal_standard_question_s-bh",
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
        if game.round < 3:
            isDailyDouble = True
            footer_buttons = {
                "Correct": "btn btn-success disabled mr-auto",
                "Incorrect": "btn btn-danger disabled mr-auto",
                "Reveal Question": "btn btn-dark mr-auto",
            }

        elif game.round >= 3:
            isDailyDouble = False
            footer_buttons = {
                "Prompt For Wagers": "btn btn-success",
                "Reveal Question": "btn btn-success disabled",
            }

        socketio.emit(
            "start_wager_round",
            {
                "room": data["room"],
                "isDailyDouble": isDailyDouble,
                "players": list(game.score.keys()),
                "buttons": footer_buttons,
            },
        )


@socketio.on("finished_reading_h-s")
def enable_buzzers(data, incorrect_players: list = list()):
    """After receiving the `socket.on` that the host has finished reading the question, `socket.emit` the
    signal to enable the buzzers for each player.

    This takes an optional argument `incorrect_players` prohiting players who have already guessed
    incorrectly to try to do so again.
    """
    socketio.emit(
        "enable_buzzers_s-p", {"room": data["room"], "players": incorrect_players}
    )


@socketio.on("buzz_in_p-s")
def player_buzzed_in(data):
    """After receiving the `socket.on` that a player is buzzing in, `socket.emit` the player's name to the
    host.
    """
    game = storage.pull(data["room"])
    game.buzz(data["name"])

    socketio.emit("reset_buzzers_s-p", {"room": data["room"]})

    socketio.emit(
        "player_buzzed_s-h", {"room": data["room"], "name": game.buzz_order[-1],},
    )


@socketio.on("correct_answer_h-s")
def host_correct_answer(data):
    """After receiving the `socket.on` that the player guessed the correct answer, update the game record,
    and `socket.emit` the updated scores to that player and the game board.

    Then reset any data in the existing modals and `end_question`.
    """
    game = storage.pull(data["room"])
    game.score[game.buzz_order[-1]] += game.current_question.value

    socketio.emit(
        "update_scores_s-ph",
        {"room": data["room"], "scores": game.score, "final": False},
    )

    socketio.emit("clear_modal", {"room": data["room"]})

    end_question(data)


@socketio.on("incorrect_answer_h-s")
def host_incorrect_answer(data):
    """After receiving the `socket.on` that the player guessed the incorrect answer, update the game record,
    and `socket.emit` the updated scores to that player and the game board.

    Then resume the buzzing in availability for the remaining players.
    """
    game = storage.pull(data["room"])
    game.score[game.buzz_order[-1]] -= game.current_question.value

    socketio.emit("update_scores_s-ph", {"room": data["room"], "scores": game.score})

    if len(game.score.keys()) == len(game.buzz_order):
        end_question(data)

    else:
        enable_buzzers(data, incorrect_players=game.buzz_order)


def end_question(data):
    """Clean up some variables and code whenever a question is completed. Firstly clear the buzzers list
    and the current question, and check to see if the round is over.
    """
    game = storage.pull(data["room"])

    game.buzz_order = list()
    game.current_question = None

    socketio.emit("clear_modal_s-bh", {"room": data["room"]})

    if config.debug:
        print(game.remaining_questions)

    if game.remaining_questions <= 0 and game.round <= 3:
        time.sleep(1)
        socketio.emit(
            "round_complete_s-bh",
            {
                "room": data["room"],
                "updates": {
                    "current_round": game.round_text(),
                    "next_round": game.round_text(upcoming=True),
                },
            },
        )

