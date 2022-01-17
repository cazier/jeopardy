from jeopardy import alex

GAMES: dict = dict()


def pull(room: str) -> alex.Game:
    return GAMES[room.upper()]


def push(room: str, value) -> None:
    GAMES[room.upper()] = value


def rooms():
    return GAMES.keys()
