from scraping.scrape import Links, Season, Game
import json


def db_add(clue_data: dict, shortnames: bool = True):
    import zlib
    import datetime
    from api.dbapi import db
    from api.dbapi.models import Set, Date, Category, Show, Round, Complete, External, Value

    if (date := Date.query.filter_by(date=datetime.date.fromisoformat(key("date"))).first()) is None:
        date = Date(date=datetime.date.fromisoformat(key("date")))
        db.session.add(date)

    if (show := Show.query.filter_by(number=key("show")).first()) is None:
        show = Show(number=key("show"), date=date)
        db.session.add(show)

    if (round_ := Round.query.filter_by(number=key("round")).first()) is None:
        round_ = Round(number=key("round"))
        db.session.add(round_)

    if (complete := Complete.query.filter_by(state=key("complete")).first()) is None:
        complete = Complete(state=key("complete"))
        db.session.add(complete)

    if (category := Category.query.filter_by(name=key("category")).first()) is None:
        category = Category(name=key("category"), show=show, round=round_, complete=complete, date=date)
        db.session.add(category)

    if (value := Value.query.filter_by(amount=key("value")).first()) is None:
        value = Value(amount=key("value"), round=round_)
        db.session.add(value)

    if (external := External.query.filter_by(state=key("external")).first()) is None:
        external = External(state=key("external"))
        db.session.add(external)

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
            external=external,
            complete=complete,
            hash=hash,
        )

        db.session.add(set_)
        db.session.commit()


def web_add(url: str, clue_data: dict, shortnames: bool = True):
    import requests

    def key(key: str) -> str:
        if shortnames:
            return clue_data[key[0].lower() if key.lower() != "complete" else "f"]

        return clue_data[key]

    data = {
        k: key(k) for k in ("date", "category", "show", "round", "answer", "question", "value", "external", "complete")
    }

    requests.post(url=url, json=data)


def get_seasons(start: int, stop: int, include_special: bool) -> list:
    seasons = Links(url="http://www.j-archive.com/listseasons.php").get().find(id="content").find_all("a")
    urls = (a.get("href").split("=")[1] for a in seasons)

    standard = [Season(id) for id in (url for url in urls if url.isnumeric()) if (start <= int(id) <= stop)]
    specials = [Season(id) for id in urls if (not id.isnumeric()) & include_special]

    return standard + specials


def store_initial_games(seasons: list) -> None:
    with open("status.json", "w") as json_file:
        json.dump(
            {"error": [], "success": [], "pending": [game_url for season in seasons for game_url in season.games]},
            json_file,
            indent="\t",
        )


