from flask_socketio import SocketIO, join_room, rooms
from flask import request

try:
    import config

except ImportError:
    from jeopardy import config

socketio = SocketIO(cors_allowed_origins=config.url)


def get_room(sid: str) -> str:
    return sorted(rooms(sid=sid), key=lambda k: len(k), reverse=True)[1]
