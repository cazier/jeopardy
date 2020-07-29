import config
import rounds
import storage

from sockets import socketio


def start_wager(game):
    socketio.emit(
        "start_wager_round-s>bh", {"room": game.room, "players": game.score.keys()},
    )


@socketio.on("get_wager-h>s")
def wager_receipt(data):
    game = storage.pull(room=data["room"])
    game.score.num = 0

    if game.round <= 2:
        players = [data["name"]]

    else:
        players = game.score.keys()

    socketio.emit(
        "wager_amount_prompt-s>p", {"room": data["room"], "players": players},
    )


@socketio.on("wager_submitted-p>s")
def wager_submittal(data):
    game = storage.pull(room=data["room"])

    socketio.emit(
        "wager_submitted-s>h", {"room": game.room, "updates": {"name": data["name"]}},
    )

    if "wager" in data.keys():
        game.score[data["name"]] = ("amount", int(data["wager"]))

        updates: dict = dict()

        if game.round >= 3:
            if game.score.num == len(game.score):
                game.get(u"q_0_0")
                info = game.current_question.get()

                updates = {
                    "wager_question": info["question"].replace("<br />", "\n"),
                    "wager_answer": info["answer"],
                    "displayedInModal": "#wager_round",
                }

                socketio.emit(
                    "reset_wager_names-s>h",
                    {"room": game.room, "players": list(game.score.players.keys())},
                )

                reveal_wager_question(game=game, updates=updates)

            # socketio.emit(
            #     "wager_submitted-s>h",
            #     {"room": game.room, "updates": {"name": data["name"]}},
            # )

        elif game.round < 3:
            info = game.current_question.get()

            updates = {
                "wager_question": info["question"].replace("<br />", "\n"),
                "wager_answer": info["answer"],
            }

            reveal_wager_question(game=game, updates=updates)

    elif "answer" in data.keys():
        game.score[data["name"]] = ("answer", data["answer"])

        updates: dict = dict()

        if game.score.num == len(game.score):
            socketio.emit(
                "reveal_wager_answer_s-bh", {"room": game.room, "updates": updates,},
            )


def reveal_wager_question(game, updates: dict) -> None:
    socketio.emit(
        "reveal_wager_question-s>bh", {"room": game.room, "updates": updates,},
    )


@socketio.on("wager_answered-h>s")
def wager_answered(data):
    game = storage.pull(room=data["room"])

    game.score.update(game=game, correct=int(data["correct"]), round_=u"wager")

    socketio.emit(
        "update_scores-s>bph",
        {
            "room": data["room"],
            "scores": game.score.emit(),
        },
    )

    socketio.emit("clear_modal", {"room": data["room"]})

    rounds.end_question(data)

@socketio.on("get_answers-h>s")
def answer_receipt(data):
    game = storage.pull(room=data["room"])
    game.score.num = 0

    players = game.score.keys()

    socketio.emit(
        "wager_answer_prompt-s>p", {"room": data["room"], "players": players},
    )
