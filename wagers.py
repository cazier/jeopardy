import config
import rounds
import storage

from sockets import socketio


def start_wager(game):
    socketio.emit(
        "start_wager_round_s-bh", {"room": game.room, "players": game.score.keys()},
    )


@socketio.on("get_wager_h-s")
def wager_receipt(data):
    game = storage.pull(room=data["room"])

    if game.round <= 2:
        players = [data["name"]]

    else:
        players = game.score.keys()

    socketio.emit(
        "wager_amount_prompt_s-p", {"room": data["room"], "players": players},
    )


@socketio.on("wager_submitted_p-s")
def wager_submittal(data):
    game = storage.pull(room=data["room"])

    if "wager" in data.keys():
        game.score[data["name"]] = ("amount", int(data["wager"]))

        updates: dict = dict()

        if game.round >= 3:
            if game.score.num == len(game.score):
                game.score.num = 0

                game.get(u"q_0_0")
                info = game.current_question.get()

                updates = {
                    "wager_question": info["question"].replace("<br />", "\n"),
                    "wager_answer": info["answer"],
                    "displayedInModal": "#wager_round",
                }

                reset_wager_names(game=game)

                reveal_wager_question(game=game, updates=updates)

            socketio.emit(
                "wager_submitted_s-h",
                {"room": game.room, "updates": {"name": data["name"]}},
            )

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
            reset_wager_names(game=game)



def reveal_wager_question(game, updates: dict) -> None:
    socketio.emit(
        "reveal_wager_question_s-bh",
        {
            "room": game.room,
            "updates": updates,
        },
    )


def reset_wager_names(game) -> None:
    socketio.emit(
        "reset_wager_names_s-h",
        {"room": game.room, "players": list(game.score.players.keys())},
    )


@socketio.on("wager_answered_h-s")
def wager_answered(data):
    game = storage.pull(room=data["room"])

    game.score.update(game=game, correct=int(data["correct"]), round_=u"wager")

    socketio.emit(
        "update_scores_s-ph", {"room": data["room"], "scores": game.score.emit()}
    )

    socketio.emit("clear_modal", {"room": data["room"]})

    rounds.end_question(data)


@socketio.on("get_answers_h-s")
def answer_receipt(data):
    game = storage.pull(room=data["room"])

    players = game.score.keys()

    socketio.emit(
        "wager_answer_prompt_s-p", {"room": data["room"], "players": players},
    )