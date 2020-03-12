import config
import storage

from sockets import socketio


def start_wager(game):
    if game.round < 3:
        footer_buttons = {
            "Correct": "btn btn-success mr-auto",
            "Incorrect": "btn btn-danger mr-auto",
        }

    else:
        footer_buttons = {
            "Prompt For Wagers": "btn btn-success",
            "Reveal Question": "btn btn-success disabled",
        }

    socketio.emit(
        "start_wager_round_s-bh",
        {
            "room": game.room,
            "players": list(game.score.keys()),
            "buttons": footer_buttons,
        },
    )


@socketio.on("wager_identified_h-s")
def single_wager_identified(data):
    game = storage.pull(room=data["room"])

    if game.round < 3:
        game.wagers["single"] = data["name"]

    socketio.emit(
        "wager_amount_prompt_s-p", {"room": data["room"], "players": [data["name"]],},
    )


@socketio.on("wager_submitted_p-s")
def wager_receipt(data):
    game = storage.pull(room=data["room"])

    info = game.current_question.get()

    game.wagers["wagers"][data["name"]] = int(data["wager"])
    game.wagers["received"] += 1 if game.round > 3 else len(game.score.keys())

    if game.wagers["received"] >= len(game.score.keys()):
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

