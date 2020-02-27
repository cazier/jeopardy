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

app = Flask(__name__)
app.jinja_env.globals.update(game_name=config.game_name)
app.jinja_env.globals.update(currency=config.currency)

app.config[u"SECRET_KEY"] = config.app_secret
app.debug = config.debug
socketio = SocketIO(app)


@app.route(u"/test")
def route_test():
    room = generate_room_code()

    storage.push(
        room=room,
        value=alex.Game(
            room=room, size=int(request.form.get(u"categories", default=6)),
        ),
    )

    storage.pull(room=room).make_board()

    return render_template(template_name_or_list=u"testing.html")


@app.route(u"/", methods=[u"GET"])
def route_index():
    """Display the home (index) page, with two buttons to start or join a game
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list=u"index.html")


@app.route(u"/new", methods=[u"GET"])
def route_new():
    """Display the option(s) available to start a new game. As of now, this only supports selecting the
    number of categories with which to play. Conceivably "infinte" number of players can join.
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list=u"new.html")


@app.route(u"/join", methods=[u"GET"])
def route_join():
    """Display the page to join a game. This does include some error handling, but largely is messy...
    
    - Players will enter their name, and the room code created by the host. No two players can have the same name
    - The "Board" will just enter a room code.
    - If the host gets disconnected, they can rejoin here too.
    
    Only allows GET requests.
    """
    return render_template(
        template_name_or_list=u"join.html", errors=get_flashed_messages()
    )


@app.route(u"/host", methods=[u"POST"])
def route_host():
    """Displays the page used by the game host to manage the gameplay. It can be "accessed" either from the `/new`
    endpoint or the `/join` endpoint, and will do different things, as needed.

    Only allows POST requests.
    """
    if request.form.get(u"players") and request.form.get(u"categories"):

        room = generate_room_code()

        storage.push(
            room=room,
            value=alex.Game(
                room=room, size=int(request.form.get(u"categories", default=6)),
            ),
        )

        storage.pull(room=room).make_board()

        session[u"name"] = u"Host"
        session[u"room"] = room

    elif request.form.get(u"room"):
        room = request.form.get(u"room")

    else:
        abort(500)

    return render_template(
        template_name_or_list=u"host.html",
        session=session,
        game=storage.pull(room=room),
    )


@app.route(u"/play", methods=[u"GET", u"POST"])
def route_player():
    """Displays the page used by the players to "compete". The page will initially run a number of checks
    to verify that the room code was valid, or that the name entered can be done. If anything is invalid,
    reroute back to `/join` and display the messages.

    Allows both GET and POST requests.
    """
    if request.method == u"POST":
        error_occurred = False

        room = request.form.get(u"room").upper()
        name = request.form.get(u"name")

        if room not in storage.rooms():
            flash(
                message=u"The room code you entered was invalid. Please try again!",
                category=u"error",
            )
            error_occurred = True

        if name in storage.pull(room=room).score.keys():
            flash(
                message=u"The name you selected already exists. Please choose another one!",
                category=u"error",
            )
            error_occurred = True

        elif (len(name) < 1) or (name.isspace()):
            flash(
                message=u"The name you entered was invalid. Please try again!",
                category=u"error",
            )
            error_occurred = True

        if error_occurred:
            return redirect(url_for(u"route_join"))

        else:
            storage.pull(room=room).add_player(name)

            socketio.emit(u"add_player_to_board", {u"room": room, u"player": name})

            session[u"name"] = name
            session[u"room"] = room

    elif request.method == u"GET" and session is not None:
        if config.debug:
            session[u"name"] = request.args.get(key="name")
            session[u"room"] = request.args.get(key="room")

        room = session[u"room"]

    return render_template(
        template_name_or_list=u"play.html", session=session, game=storage.pull(room),
    )


@app.route(u"/board", methods=[u"POST"])
def route_board():
    """Displays the page used to display the board. As with `/play`, performs a small amount of error checking
    to ensure the room exists.

    Allows only POST requests.
    """
    room = request.form.get(u"room").upper()

    if room not in storage.rooms():
        flash(
            message=u"The room code you entered was invalid. Please try again!",
            category=u"error",
        )
        return redirect(url_for(u"route_join"))

    return render_template(
        template_name_or_list=u"board.html", game=storage.pull(room=room)
    )


# @app.route(u'/score/<string:user>/<int:incrementer>')
# def add_score(user, incrementer):
#   LIVE_GAME_CONTAINER[u'ABCD'].score[user] += incrementer
#   print(LIVE_GAME_CONTAINER[u'ABCD'].score)
#   return u'Added {incrementer} to user {user}'.format(incrementer = incrementer, user = user)


@app.errorhandler(500)
def internal_server_error(error):
    """Directs Flask to load the error handling page on HTTP Status Code 500 (Server Errors)"""
    return render_template(template_name_or_list=u"errors.html", error_code=error), 500


@socketio.on(u"question_clicked")
def reveal_host_clue(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]
    info = game.get(data[u"identifier"])

    if info[u"wager"]:
        if game.round == 3:
            isDailyDouble = False
            footer_buttons = {
                u"Prompt For Wagers": u"btn btn-success",
                u"Reveal Question": u"btn btn-success disabled",
            }

        else:
            isDailyDouble = True
            footer_buttons = {
                u"Correct": u"btn btn-success disabled mr-auto",
                u"Incorrect": u"btn btn-danger disabled mr-auto",
                u"Reveal Question": u"btn btn-dark mr-auto",
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

        print(u"DAILY DOUBLE!!!")

    else:
        socketio.emit(
            u"question_revealed",
            {
                u"room": data[u"room"],
                u"question": info[u"question"].replace(u"<br />", u"\n"),
                u"answer": info[u"answer"],
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
    game = LIVE_GAME_CONTAINER[data[u"room"]]
    game.score[game.buzz_order[-1]] -= game.current_question.value

    socketio.emit(u"update_scores", {u"room": data[u"room"], u"scores": game.score})

    enable_buzzers(data, incorrect_players=game.buzz_order)


@socketio.on(u"buzzed_in")
def player_buzzed_in(data):
    LIVE_GAME_CONTAINER[data[u"room"]].buzz(data[u"name"])

    socketio.emit(u"reset_player", {u"room": data[u"room"], u"player": None})

    socketio.emit(
        u"player_buzzed",
        {
            u"room": data[u"room"],
            u"name": LIVE_GAME_CONTAINER[data[u"room"]].buzz_order[-1],
        },
    )


@socketio.on(u"dismiss_modal")
def dismiss_modal(data):
    socketio.emit(u"clear_modal", {u"room": data[u"room"]})

    end_question(data)


@socketio.on(u"start_next_round")
def start_next_round(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.start_next_round()

    socketio.emit(u"round_started")


@socketio.on(u"get_wagers")
def get_wagers(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    socketio.emit(
        u"start_wager_round",
        {u"room": data[u"room"], u"players": list(game.score.keys())},
    )


@socketio.on(u"reveal_question")
def reveal_question(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    socketio.emit(u"final_question_revealed")


@socketio.on(u"wager_submitted")
def received_wager(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.wagered_round[data[u"name"]] = {u"wager": data[u"wager"]}

    socketio.emit("wagerer_received", {u"room": data[u"room"], u"name": data[u"name"]})


@socketio.on(u"answer_submitted")
def received_answer(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.wagered_round[data[u"name"]][u"answer"] = data[u"answer"]

    socketio.emit("wagerer_received", {u"room": data[u"room"], u"name": data[u"name"]})


@socketio.on(u"final_wagerer_reveal")
def wagerer_reveal(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]
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
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    socketio.emit(u"reveal_wager_answer", {u"room": data[u"room"],})


@socketio.on(u"correct_wager")
def correct_wager(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.score[data[u"name"]] += game.wagered_round[data[u"name"]][u"wager"]

    game.wagered_round = dict()

    socketio.emit(
        u"update_scores",
        {u"room": data[u"room"], u"scores": game.score, u"final": True},
    )


@socketio.on(u"incorrect_wager")
def incorrect_wager(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.score[data[u"name"]] -= game.wagered_round[data[u"name"]][u"wager"]

    game.wagered_round = dict()

    socketio.emit(
        u"update_scores",
        {u"room": data[u"room"], u"scores": game.score, u"final": True},
    )


@socketio.on(u"single_wager_prompt")
def single_wager_prompt(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.wagered_round[data[u"name"][:-15]] = dict()

    socketio.emit(
        u"single_wager_player_prompt",
        {u"room": data[u"room"], u"players": [data[u"name"][:-15]]},
    )


@socketio.on(u"single_wager_submitted")
def received_wager(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

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
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    if data[u"isDailyDouble"]:
        game.wagered_round[data[u"name"]] = {}

    print(u"WAGERER RECEIVED! They're name is:", data[u"name"])


@socketio.on(u"join")
def socket_join(data):
    join_room(data[u"room"])


def generate_room_code() -> str:
    if config.debug:
        return "ABCD"

    else:
        letters = u"".join(random.sample(list(u"ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 4))
        while letters in LIVE_GAME_CONTAINER.keys():
            return generate_room_code()

        return letters


def end_question(data):
    game = LIVE_GAME_CONTAINER[data[u"room"]]

    game.buzz_order = list()
    game.current_question = None

    print(u"=" * 40)
    print(u"ROUND ENDED", game.round)
    print(u"=" * 40)

    if game.remaining_questions <= 0 and game.round <= 3:
        socketio.emit(
            u"round_complete",
            {
                u"room": data[u"room"],
                u"current_round": LIVE_GAME_CONTAINER[data[u"room"]].round_text(),
                u"next_round": LIVE_GAME_CONTAINER[data[u"room"]].round_text(
                    upcoming=True
                ),
            },
        )


if __name__ == u"__main__":
    socketio.run(app, host=u"0.0.0.0")

