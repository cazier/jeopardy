import config
import storage

from sockets import socketio


def start_wager(game):
    if game.round < 3:
        footer_buttons = {
            "Correct": "btn btn-success disabled mr-auto",
            "Incorrect": "btn btn-danger disabled mr-auto",
            "Reveal Question": "btn btn-dark disabled mr-auto",
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
    if game.round < 3:
        game = storage.pull()
