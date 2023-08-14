import zlib
import datetime

from sqlalchemy import select

from jeopardy.api import KEYS
from jeopardy.api.models import Set, Date, Show, Round, Value, Category, db

session = db.session


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

    if (date := session.scalar(select(Date).where(Date.date == date_format))) is None:
        date = Date(date=date_format)
        db.session.add(date)

    try:
        show_format = int(key("show"))

    except ValueError:
        raise BadDataError(item="show number", error="an integer (positive or negative)")

    if (show := session.scalar(select(Show).where(Show.number == show_format))) is None:
        show = Show(number=show_format, date=date)
        db.session.add(show)

    try:
        round_format = int(key("round"))
        if round_format not in (0, 1, 2, 4):
            raise ValueError

    except ValueError:
        raise BadDataError(item="round number", error="one of the following integers: (0, 1, 2, 4)")

    if (round_ := session.scalar(select(Round).where(Round.number == round_format))) is None:
        round_ = Round(number=round_format)
        db.session.add(round_)

    if (complete_format := key("complete")) not in (True, False):
        raise BadDataError(item="complete tag", error="supplied with a boolean value")

    if (
        category := session.scalar(
            select(Category).where(Category.name == key("category")).where(Category.date == date)
        )
    ) is None:
        category = Category(name=key("category"), show=show, round=round_, complete=complete_format, date=date)
        db.session.add(category)

    try:
        value_format = int(str(key("value")).replace("$", ""))
        if value_format < 0:
            raise ValueError

    except ValueError:
        raise BadDataError(item="value", error='a positive number, with or without, a "$"')

    if (value := session.scalar(select(Value).where(Value.amount == value_format))) is None:
        value = Value(amount=value_format, round=round_)
        db.session.add(value)

    if (external_format := key("external")) not in (True, False):
        raise BadDataError(item="external tag", error="supplied with a boolean value")

    hash = zlib.adler32(f'{key("question")}{key("answer")}{show.number}'.encode())

    if session.scalar(select(Set).where(Set.hash == hash)) is None:
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
