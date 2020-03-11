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
            "isDailyDouble": game.round < 3,
            "players": list(game.score.keys()),
            "buttons": footer_buttons,
        },
    )


@socketio.on("wager_identified_h-s")
def single_wager_identified(data):
    game = storage.pull(room=data["room"])

    game.wagers = {data["name"]: 0}

    socketio.emit(
        "wager_amount_prompt_s-p",
        {
            "room": data["room"],
            "isDailyDouble": game.round < 3,
            "players": [data["name"]],
        },
    )
