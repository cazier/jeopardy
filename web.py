from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
    flash,
    get_flashed_messages,
)
from flask_socketio import SocketIO, join_room

import random

import alex
import config
import storage

import rounds
import routing
import sockets

import wagers

app = Flask(__name__)
app.register_blueprint(blueprint=rounds.rounds)
app.register_blueprint(blueprint=routing.routing)

app.jinja_env.globals.update(game_name=config.game_name)
app.jinja_env.globals.update(currency=config.currency)

app.config[u"SECRET_KEY"] = config.app_secret
app.debug = config.debug

socketio = sockets.socketio
socketio.init_app(app)

# rounds.socketio.init_app(app)
# socketio = SocketIO(app)


# @app.route(u'/score/<string:user>/<int:incrementer>')
# def add_score(user, incrementer):
#   LIVE_GAME_CONTAINER[u'ABCD'].score[user] += incrementer
#   print(LIVE_GAME_CONTAINER[u'ABCD'].score)
#   return u'Added {incrementer} to user {user}'.format(incrementer = incrementer, user = user)


@socketio.on(u"dismiss_modal")
def dismiss_modal(data):
    socketio.emit(u"clear_modal", {u"room": data[u"room"]})

    rounds.end_question(data)


@socketio.on(u"get_wagers")
def get_wagers(data):
    game = storage.pull(data[u"room"])

    socketio.emit(
        u"start_wager_round",
        {u"room": data[u"room"], u"players": list(game.score.keys())},
    )


@socketio.on(u"reveal_question")
def reveal_question(data):
    game = storage.pull(data[u"room"])

    socketio.emit(u"final_question_revealed")


@socketio.on(u"wager_submitted")
def received_wager(data):
    game = storage.pull(data[u"room"])

    game.wagered_round[data[u"name"]] = {u"wager": data[u"wager"]}

    socketio.emit("wagerer_received", {u"room": data[u"room"], u"name": data[u"name"]})


@socketio.on(u"answer_submitted")
def received_answer(data):
    game = storage.pull(data[u"room"])

    game.wagered_round[data[u"name"]][u"answer"] = data[u"answer"]

    socketio.emit("wagerer_received", {u"room": data[u"room"], u"name": data[u"name"]})


@socketio.on(u"final_wagerer_reveal")
def wagerer_reveal(data):
    game = storage.pull(data[u"room"])
    name = data[u"name"][:-8]

    socketio.emit(
        "final_wager_received",
        {
            u"room": data[u"room"],
            u"name": name,
            u"wager": game.wagered_round[name][u"wager"],
            u"answer": game.wagered_round[name][u"answer"],
        },
    )


@socketio.on(u"reveal_answer")
def reveal_answer(data):
    game = storage.pull(data[u"room"])

    socketio.emit(u"reveal_wager_answer", {u"room": data[u"room"],})


@socketio.on(u"correct_wager")
def correct_wager(data):
    game = storage.pull(data[u"room"])

    game.score[data[u"name"]] += game.wagered_round[data[u"name"]][u"wager"]

    game.wagered_round = dict()

    socketio.emit(
        u"update_scores",
        {u"room": data[u"room"], u"scores": game.score, u"final": True},
    )


@socketio.on(u"incorrect_wager")
def incorrect_wager(data):
    game = storage.pull(data[u"room"])

    game.score[data[u"name"]] -= game.wagered_round[data[u"name"]][u"wager"]

    game.wagered_round = dict()

    socketio.emit(
        u"update_scores",
        {u"room": data[u"room"], u"scores": game.score, u"final": True},
    )


@socketio.on(u"single_wager_prompt")
def single_wager_prompt(data):
    game = storage.pull(data[u"room"])

    game.wagered_round[data[u"name"][:-15]] = dict()

    socketio.emit(
        u"single_wager_player_prompt",
        {u"room": data[u"room"], u"players": [data[u"name"][:-15]]},
    )


@socketio.on(u"single_wager_submitted")
def received_wager(data):
    game = storage.pull(data[u"room"])

    info = game.current_question.get()

    if data[u"name"] in game.wagered_round.keys():

        game.wagered_round[data[u"name"]] = {u"wager": data[u"wager"]}

        socketio.emit(
            u"single_question_revealed",
            {
                u"room": data[u"room"],
                u"question": info[u"question"].replace(u"<br />", u"\n"),
                u"answer": info[u"answer"],
            },
        )

    else:
        pass
        ##TODO ERROR HANDLE THIS!


@socketio.on(u"player_selected")
def player_selected(data):
    game = storage.pull(data[u"room"])

    if game.round < 3:
        game.wagered_round[data[u"name"]] = {}

    print(u"WAGERER RECEIVED! They're name is:", data[u"name"])


@socketio.on(u"join")
def socket_join(data):
    join_room(data[u"room"])


if __name__ == u"__main__":
    socketio.run(app, host=u"0.0.0.0")

