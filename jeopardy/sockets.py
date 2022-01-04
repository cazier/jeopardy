from flask import request
from flask_socketio import SocketIO, rooms, join_room

try:
    import config

except ImportError:
    from jeopardy import config

socketio = SocketIO(cors_allowed_origins=config.url, logger=True)


def get_room(sid: str) -> str:
    return sorted(rooms(sid=sid), key=lambda k: len(k), reverse=True)[1]


@socketio.on("join")
def on_join(data):
    """Connects the player to the specific room associated with the game"""

    join_room(room=data["room"])
