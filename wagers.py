import config
import rounds
import storage

from flask import request

from sockets import socketio, get_room


def start_wager(game):
    room = get_room(sid=request.sid)
    socketio.emit(event="start_wager_round-s>bh", data={"players": game.score.keys()}, room=room)


@socketio.on("get_wager-h>s")
def wager_receipt(data):
    room = get_room(sid=request.sid)

    game = storage.pull(room=room)

    if game.round < 2:
        players = [data["name"]]
        game.score.wagerer = data["name"]

    else:
        players = game.score.keys()

    socketio.emit(event="wager_amount_prompt-s>p", data={"players": players}, room=room)


@socketio.on("wager_submitted-p>s")
def wager_submittal(data):
    room = get_room(sid=request.sid)

    game = storage.pull(room=room)

    socketio.emit(event="wager_submitted-s>h", data={"updates": {"name": data["name"]}}, room=room)

    if "wager" in data.keys():
        game.score[data["name"]] = ("amount", int(data["wager"]))

        updates: dict = dict()

        if game.round >= 2:
            if game.score.num == len(game.score):
                game.score.num = 0

                game.get(u"q_0_0")
                info = game.current_set.get()

                updates = {
                    "wager_question": info["question"].replace("<br />", "\n"),
                    "wager_answer": info["answer"].replace("<br />", "\n"),
                    "displayedInModal": "#wager_round",
                }

                socketio.emit(
                    event="reset_wager_names-s>h", data={"players": list(game.score.players.keys())}, room=room
                )

                reveal_wager(game=game, updates=updates)

            # socketio.emit(
            #     "wager_submitted-s>h",
            #     {"room": game.room, "updates": {"name": data["name"]}},
            # )

        elif game.round < 2:
            game.score.num = 0

            info = game.current_set.get()

            updates = {
                "wager_question": info["question"].replace("<br />", "\n"),
                "wager_answer": info["answer"].replace("<br />", "\n"),
            }

            reveal_wager(game=game, updates=updates)

    elif "question" in data.keys():
        game.score[data["name"]] = ("question", data["question"])

        updates: dict = dict()

        if game.score.num == len(game.score):
            game.score.num = 0

            socketio.emit(
                event="enable_show_responses-s>h",
                data={
                    "updates": updates,
                },
                room=room,
            )


def reveal_wager(game, updates: dict) -> None:
    socketio.emit(
        event="reveal_wager-s>bh",
        data={
            "updates": updates,
        },
        room=game.room,
    )


@socketio.on("wager_responded-h>s")
def wager_responded(data):
    room = get_room(sid=request.sid)

    game = storage.pull(room=room)

    game.score.update(game=game, correct=int(data["correct"]))

    socketio.emit(
        event="update_scores-s>bph",
        data={
            "scores": game.score.emit(),
        },
        room=room,
    )

    if game.round < 2:
        socketio.emit(
            event="reset_wagers_modals-s>bh", data={"updates": {"wager_answer": "", "wager_question": ""}}, room=room
        )

        socketio.emit(event="clear_modal-s>bh", room=room)

        rounds.end_set(room)


@socketio.on("get_responses-h>s")
def wager_response_prompt():
    room = get_room(sid=request.sid)

    game = storage.pull(room=room)

    players = game.score.keys()

    socketio.emit(event="wager_response_prompt-s>p", data={"players": players}, room=room)


@socketio.on("show_responses-h>s")
def show_responses():
    room = get_room(sid=request.sid)

    game = storage.pull(room=room)

    if game.score.num == len(game.score):
        rounds.end_set(room)

    else:
        player = game.score.sort()[game.score.num]
        game.score.wagerer = player

        socketio.emit(event="display_final_response-s>bph", data={"updates": game.score.wager(player)}, room=room)

        game.score.num += 1
