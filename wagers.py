import config
import rounds
import storage

from sockets import socketio


def start_wager(game):
    socketio.emit(
        "start_wager_round_s-bh", {"room": game.room, "players": game.score.keys()},
    )


@socketio.on("get_wager_h-s")
def wager_answered(data):
    game = storage.pull(room=data["room"])

    if game.round <= 2:
        players = [data["name"]]

    else:
        players = game.score.keys()

    socketio.emit(
        "wager_amount_prompt_s-p", {"room": data["room"], "players": players},
    )


@socketio.on("wager_submitted_p-s")
def wager_receipt(data):
    game = storage.pull(room=data["room"])

    game.score[data["name"]] = int(data["wager"])

    if game.round < 3 or (game.round >= 3 and (game.score.num > len(game.score))):
        info = game.current_question.get()

        socketio.emit(
            "reveal_wager_question_s-bh",
            {
                "room": game.room,
                "updates": {
                    "wager_question": info["question"].replace("<br />", "\n"),
                    "wager_answer": info["answer"],
                },
            },
        )

    else:
        socketio.emit(
            "wager_submitted_s-h",
            {"room": game.room, "updates": {"wager_player": data["name"]}},
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
