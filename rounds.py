from flask import Flask, Blueprint
from flask_socketio import SocketIO, join_room

import storage

rounds = Blueprint(name=u"rounds", import_name=__name__)

socketio = SocketIO()


@socketio.on(u"host_clicked_question")
def host_clicked_question(data):
    """The host has selected a question from their device.

    Required Arguments: 

    - `data` (dict) - A dictionary containing the information associated with the selected 
    question; the identifier of the question, and the room it was selected from.
    """
    game = storage.pull(data[u"room"])
    info = game.get(data[u"identifier"])

    # If the question is not a Daily Double or Final Round (which would require a wager!)
    if not info[u"wager"]:
        socketio.emit(
            u"question_revealed",
            {
                u"room": data[u"room"],
                u"question": info[u"question"].replace(u"<br />", u"\n"),
                u"answer": info[u"answer"],
            },
        )

    # If the question is a DD or in one of the final rounds, need to request a wager prior to
    # showing the
    else:
        if game.round < 3:
            isDailyDouble = True
            footer_buttons = {
                u"Correct": u"btn btn-success disabled mr-auto",
                u"Incorrect": u"btn btn-danger disabled mr-auto",
                u"Reveal Question": u"btn btn-dark mr-auto",
            }

        elif game.round >= 3:
            isDailyDouble = False
            footer_buttons = {
                u"Prompt For Wagers": u"btn btn-success",
                u"Reveal Question": u"btn btn-success disabled",
            }

        socketio.emit(
            u"start_wager_round",
            {
                u"room": data[u"room"],
                u"isDailyDouble": isDailyDouble,
                u"players": list(game.score.keys()),
                u"buttons": footer_buttons,
            },
        )


@socketio.on(u"finished_reading")
def enable_buzzers(data, incorrect_players: list = list()):
    socketio.emit(
        u"enable_buzzers", {u"room": data[u"room"], u"players": incorrect_players}
    )


@socketio.on(u"correct_answer")
def host_correct_answer(data):
    game = storage.pull(data[u"room"])
    game.score[game.buzz_order[-1]] += game.current_question.value

    socketio.emit(u"clear_modal", {u"room": data[u"room"]})

    socketio.emit(
        u"update_scores",
        {u"room": data[u"room"], u"scores": game.score, u"final": False},
    )

    end_question(data)


@socketio.on(u"incorrect_answer")
def host_incorrect_answer(data):
    game = storage.pull(data[u"room"])
    game.score[game.buzz_order[-1]] -= game.current_question.value

    socketio.emit(u"update_scores", {u"room": data[u"room"], u"scores": game.score})

    enable_buzzers(data, incorrect_players=game.buzz_order)


@socketio.on(u"buzzed_in")
def player_buzzed_in(data):
    game = storage.pull(data[u"room"])
    game.buzz(data[u"name"])

    socketio.emit(u"reset_player", {u"room": data[u"room"], u"player": None})

    socketio.emit(
        u"player_buzzed", {u"room": data[u"room"], u"name": game.buzz_order[-1],},
    )


def end_question(data):
    game = storage.pull(data[u"room"])

    game.buzz_order = list()
    game.current_question = None

    print(game.remaining_questions)

    if game.remaining_questions <= 0 and game.round <= 3:
        socketio.emit(
            u"round_complete",
            {
                u"room": data[u"room"],
                u"current_round": game.round_text(),
                u"next_round": game.round_text(upcoming=True),
            },
        )
