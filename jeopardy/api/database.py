import zlib
import datetime

from .models import *
from . import KEYS


class SetAlreadyExistsError(Exception):
    def __init__(self):
        self.message = "This set is already in the database"

        super().__init__(self.message)


class MissingDataError(Exception):
    def __init__(self, message: str):
        self.message = message

        super().__init__(self.message)


class BadDataError(Exception):
    def __init__(self, item: str, error: str):
        self.message = f"Please ensure the {item} is {error}"

        super().__init__(self.message)


def add(clue_data: dict, uses_shortnames: bool) -> list:
    def key(key: str) -> str:
        if uses_shortnames:
            return clue_data[key[0].lower() if key.lower() != "complete" else "f"]

        return clue_data[key]

    keys = KEYS

    if uses_shortnames:
        keys = {i[0] if i != "complete" else "f" for i in keys}

    if (missing := keys.difference(set(clue_data.keys()))) != set():
        raise MissingDataError(message=f"This set is missing the following keys: {' '.join(missing)}")

    for k, v in clue_data.items():
        if len(str(v)) == 0:
            raise MissingDataError(message=f"This set has an empty value for key: {k}")

    try:
        date_format = datetime.date.fromisoformat(key("date"))

    except ValueError:
        raise BadDataError(item="date", error="in the isoformat: YYYY-MM-DD")

    if (date := Date.query.filter_by(date=date_format).first()) is None:
        date = Date(date=date_format)
        db.session.add(date)

    try:
        show_format = int(key("show"))

    except ValueError:
        raise BadDataError(item="show number", error="an integer (positive or negative)")

    if (show := Show.query.filter_by(number=show_format).first()) is None:
        show = Show(number=show_format, date=date)
        db.session.add(show)

    try:
        round_format = int(key("round"))
        if round_format not in (0, 1, 2, 4):
            raise ValueError

    except ValueError:
        raise BadDataError(item="round number", error="one of the following integers: (0, 1, 2, 4)")

    if (round_ := Round.query.filter_by(number=round_format).first()) is None:
        round_ = Round(number=round_format)
        db.session.add(round_)

    if (complete_format := key("complete")) not in (True, False):
        raise BadDataError(item="complete tag", error="supplied with a boolean value")

    if (category := Category.query.filter_by(name=key("category")).filter_by(date=date).first()) is None:
        category = Category(name=key("category"), show=show, round=round_, complete=complete_format, date=date)
        db.session.add(category)

    try:
        value_format = int(str(key("value")).replace("$", ""))
        if value_format < 0:
            raise ValueError

    except ValueError:
        raise BadDataError(item="value", error='a positive number, with or without, a "$"')

    if (value := Value.query.filter_by(amount=value_format).first()) is None:
        value = Value(amount=value_format, round=round_)
        db.session.add(value)

    if (external_format := key("external")) not in (True, False):
        raise BadDataError(item="external tag", error="supplied with a boolean value")

    hash = zlib.adler32(f'{key("question")}{key("answer")}{show.number}'.encode())

    if Set.query.filter_by(hash=hash).first() is None:
        set_ = Set(
            category=category,
            date=date,
            show=show,
            round=round_,
            answer=key("answer"),
            question=key("question"),
            value=value,
            external=external_format,
            complete=complete_format,
            hash=hash,
        )

        db.session.add(set_)
        db.session.commit()

        return set_

    else:
        raise SetAlreadyExistsError()
