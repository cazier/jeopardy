import pytest

from jeopardy.sockets import get_room


def test_get_room(webclient):
    room = "test"

    with pytest.raises(IndexError):
        get_room(webclient.socketio.sid)

    webclient.emit("join", {"room": room})

    assert get_room(webclient.socketio.sid) == room
