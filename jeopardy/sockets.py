from flask_socketio import SocketIO, join_room, rooms
from flask import request

socketio = SocketIO()


def get_room(sid: str) -> str:
    return sorted(rooms(sid=sid), key=lambda k: len(k), reverse=True)[1]
