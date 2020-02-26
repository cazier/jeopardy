from typing import Any

GAMES: dict = dict()


def pull(room: str):
    return GAMES[room]


def push(room: str, value: Any) -> None:
    GAMES[room] = value


def rooms():
    return GAMES.keys()
