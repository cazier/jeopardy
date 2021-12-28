from flask import request
from flask_socketio import SocketIO, rooms, join_room

try:
    import config

except ImportError:
    from jeopardy import config

socketio = SocketIO(cors_allowed_origins=config.url)


def get_room(sid: str) -> str:
    return sorted(rooms(sid=sid), key=lambda k: len(k), reverse=True)[1]
