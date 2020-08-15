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

    if game.round <= 2:
        players = [data["name"]]
        game.score.wagerer = data["name"]

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
                game.score.num = 0

                game.get(u"q_0_0")
                info = game.current_set.get()

                updates = {
                    "wager_question": info["question"].replace("<br />", "\n"),
                    "wager_answer": info["answer"].replace("<br />", "\n"),
                    "displayedInModal": "#wager_round",
                }

                socketio.emit(
                    "reset_wager_names-s>h",
                    {"room": game.room, "players": list(game.score.players.keys())},
                )

                reveal_wager_answer(game=game, updates=updates)

            # socketio.emit(
            #     "wager_submitted-s>h",
            #     {"room": game.room, "updates": {"name": data["name"]}},
            # )

        elif game.round < 3:
            game.score.num = 0

            info = game.current_set.get()

            updates = {
                "wager_question": info["question"].replace("<br />", "\n"),
                "wager_answer": info["answer"].replace("<br />", "\n"),
            }

            reveal_wager_answer(game=game, updates=updates)

    elif "question" in data.keys():
        game.score[data["name"]] = ("question", data["question"])

        updates: dict = dict()

        if game.score.num == len(game.score):
            game.score.num = 0

            socketio.emit(
                "enable_show_responses-s>h", {"room": game.room, "updates": updates,},
            )


def reveal_wager_answer(game, updates: dict) -> None:
    socketio.emit(
        "reveal_wager_answer-s>bh", {"room": game.room, "updates": updates,},
    )


@socketio.on("wager_responded-h>s")
def wager_answered(data):
    game = storage.pull(room=data["room"])

    game.score.update(game=game, correct=int(data["correct"]))

    socketio.emit(
        "update_scores-s>bph", {"room": data["room"], "scores": game.score.emit(),},
    )

    if game.round <= 2:
        socketio.emit("clear_modal", {"room": data["room"]})

        rounds.end_question(data)


@socketio.on("get_questions-h>s")
def answer_receipt(data):
    game = storage.pull(room=data["room"])

    players = game.score.keys()

    socketio.emit(
        "wager_question_prompt-s>p", {"room": data["room"], "players": players},
    )


@socketio.on("show_responses-h>s")
def show_player_answers(data):
    game = storage.pull(room=data["room"])

    if game.score.num == len(game.score):
        rounds.end_question(data)

    else:
        player = game.score.sort()[game.score.num]
        game.score.wagerer = player

        socketio.emit(
            "display_final_response-s>bph",
            {"room": data["room"], "updates": game.score.wager(player)},
        )

        game.score.num += 1
