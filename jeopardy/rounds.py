import asyncio

from flask import Blueprint, request, Markup

try:
    from sockets import socketio, get_room
    import config
    import wagers
    import storage

except ImportError:
    from jeopardy.sockets import socketio, get_room
    from jeopardy import config
    from jeopardy import wagers
    from jeopardy import storage


rounds = Blueprint(name="rounds", import_name=__name__)


@socketio.on("host_clicked_answer-h>s")
def host_clicked_answer(data):
    """The host has selected an answer from their device.

    Required Arguments:

    - `data` (dict) - A dictionary containing the information associated with the selected
    set; the identifier of the set, and the room it was selected from.
    """
    room = get_room(sid=request.sid)

    game = storage.pull(room)
    info = game.get(data["identifier"])

    socketio.emit(
        event="disable_question-s>b",
        data={
            "identifier": f'#{data[u"identifier"]}',
        },
        room=room,
    )

    # If the set is not a Daily Double or Final Round (which would require a wager!)
    if not info["wager"]:
        socketio.emit(
            event="reveal_standard_set-s>bh",
            data={
                "updates": {
                    "question": Markup(info["question"]),
                    "answer": Markup(info["answer"]),
                    "year": info["year"],
                },
            },
            room=room,
        )

    # If the set is a DD or in one of the final rounds, need to request a wager prior to
    # showing the
    else:
        wagers.start_wager(game=game)


@socketio.on("finished_reading-h>s")
def enable_buzzers(incorrect_players: list = list()):
    """After receiving the `socket.on` that the host has finished reading the answer, `socket.emit` the
    signal to enable the buzzers for each player.

    This takes an optional argument `incorrect_players` prohiting players who have already guessed
    incorrectly to try to do so again.
    """
    room = get_room(sid=request.sid)

    socketio.emit(event="enable_buzzers-s>p", data={"players": incorrect_players}, room=room)


@socketio.on("dismiss-h>s")
def dismiss():
    """After receiving the `socket.on` that the host has determined no one wants to buzz in, `socket.emit` the signal to dismiss the set and return to the game board."""

    room = get_room(sid=request.sid)

    socketio.emit(event="reset_buzzers-s>p", room=room)

    end_set(room=room)


@socketio.on("buzz_in-p>s")
def player_buzzed_in(data):
    """After receiving the `socket.on` that a player is buzzing in, `socket.emit` the player's name to the
    host.
    """
    room = get_room(sid=request.sid)

    game = storage.pull(room)
    game.buzz(data=data)

    if len([k for k, v in game.buzz_order.items() if v["allowed"]]) == 1:
        asyncio.run(wait_to_emit(room=room))


async def wait_to_emit(room: str):
    game = storage.pull(room)

    await asyncio.sleep(config.buzzer_time)

    socketio.emit(event="reset_buzzers-s>p", data={"room": room}, room=room)

    valid_players = {k: v for k, v in game.buzz_order.items() if v["allowed"]}
    player = sorted(valid_players.items(), key=lambda item: item[1]["time"])[0][0]
    socketio.emit(
        event="player_buzzed-s>h",
        data={
            "name": player,
        },
        room=room,
    )


@socketio.on("response_given-h>s")
def response_given(data):
    """After receiving the `socket.on` that the player gave a response, update the game record,
    and `socket.emit` the updated scores to that player and the game board.

    If the player was correct, clean up the board and continue the game. Otherwise, allow the buzzing
    in availability for the remaining players.
    """
    room = get_room(sid=request.sid)

    game = storage.pull(room)

    game.score.update(game=game, correct=int(data["correct"]))

    socketio.emit(event="update_scores-s>bph", data={"scores": game.score.emit()}, room=room)

    if data["correct"] or len(game.score) == len([k for k, v in game.buzz_order.items() if not v["allowed"]]):
        end_set(room)

    else:
        game.buzz_order = {k: v for k, v in game.buzz_order.items() if not v["allowed"]}
        enable_buzzers(incorrect_players=list(game.buzz_order.keys()))


@socketio.on("start_next_round-h>s")
def start_next_round():
    """After receiving the `socket.on` that the host has clicked to start the next round, run
    the game logic that does so, and then `socket.emit` to the board and host to move on.
    """
    room = get_room(sid=request.sid)
    game = storage.pull(room)

    game.start_next_round()

    socketio.emit(event="next_round_started-s>bh", room=room)


def end_set(room: str):
    """Clean up some variables and code whenever a set is completed. Firstly clear the buzzers list
    and the current set, and check to see if the round is over.
    """
    game = storage.pull(room)

    game.buzz_order = dict()
    game.current_set = None

    socketio.emit(event="clear_modal-s>bh", room=room)

    if config.debug:
        print(game.remaining_content)

    socketio.sleep(0.5)

    if (game.remaining_content <= 0) and (game.round < 2):
        socketio.emit(
            event="round_complete-s>bh",
            data={
                "updates": {
                    "current_round": game.round_text(),
                    "next_round": game.round_text(upcoming=True),
                },
            },
            room=room,
        )

    elif game.round >= 2:
        socketio.emit(event="results-page-s>bph", room=room)
