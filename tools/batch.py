from scraping.scrape import Links, Season, Game
import json
import time



def db_add(clue_data: dict, shortnames: bool = True):
    import zlib
    import datetime
    from api import db
    from api.models import Set, Date, Category, Show, Round, Complete, External, Value

    def key(key: str) -> str:
        if shortnames:
            return clue_data[key[0].lower() if key.lower() != "complete" else "f"]

        return clue_data[key]

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
            {
                "error": [],
                "success": [],
                "pending": [game_url for season in seasons for game_url in season.games],
                "out_clues": [],
            },
            json_file,
            indent="\t",
        )


class External(object):
    def __init__(self, filename: str, output: str = "media"):
        with open(filename, "r") as dl_file:
            data = dl_file.readlines()

        self.dl = [[i.split()[0], i.split()[1]] for i in data]

        self.output = output

    def clean(self):
        for index, data in enumerate(self.dl):
            if len(data[1]) < 48:
                self.dl[index][1] = f'http://www.j-archive.com/media/{data[1].split("/")[-1]}'

    def download(self):
        import subprocess

        for (file, url) in self.dl[:3]:
            try:
                subprocess.check_output(["wget", "-O", f'{self.output}/{file}.{url.split(".")[-1]}', url])

            except subprocess.CalledProcessError as e:
                print("Fuck...", e)

            time.sleep(0.5)


class Pull(object):
    def __init__(
        self,
        start: int = 1,
        stop: int = 36,
        include_special: bool = False,
        initial: bool = False,
        error_only: bool = False,
        shortnames: bool = False,
        method: str = "db",
    ):
        self.start = start
        self.stop = stop
        self.include_special = include_special
        self.method = method
        self.shortnames = shortnames
        self.json_backup = list()

        print("Pulling season data")
        start = time.perf_counter()
        if error_only:
            with open("status.json", "r") as json_file:
                json_data = json.load(json_file)

            self.error = list()
            self.success = json_data["success"]
            self.pending = json_data["pending"] + json_data["error"]
            self.outstanding_clues = json_data["out_clues"]

            self.save(clues=False)
            initial = False

        if initial:
            seasons = get_seasons(start=self.start, stop=self.stop, include_special=self.include_special)
            store_initial_games(seasons)

        elapsed = time.perf_counter() - start
        print(f"Finished pulling season data! Time taken: {elapsed:.2f} seconds")

        if input("Saved all season data to JSON file. Continue? (yN)").lower() == "y":
            with open("status.json", "r") as json_file:
                json_data = json.load(json_file)

            self.error = json_data["error"]
            self.success = json_data["success"]
            self.pending = json_data["pending"]

            self.outstanding_clues = json_data["out_clues"]

            self.scrape()

    def save(self, clues: bool = True):
        with open("status.json", "w") as json_file:
            json.dump(
                {
                    "error": self.error,
                    "success": self.success,
                    "pending": self.pending,
                    "out_clues": self.outstanding_clues,
                },
                json_file,
                indent="\t",
            )

        if clues:
            with open("clue_backup.json", "w") as json_file:
                json.dump(self.json_backup, json_file, indent="\t")

    def scrape(self):
        print("Starting to scrape game data")
        while len(self.pending) > 0:
            start = time.perf_counter()
            url = self.pending.pop()

            try:
                if url not in self.error and url not in self.success:
                    clues = Game(url=url)

                    self.outstanding_clues = clues.json

                    while len(self.outstanding_clues) > 0:
                        clue = self.outstanding_clues.pop()

                        if self.method == "db":
                            db_add(clue_data=clue, shortnames=self.shortnames)

                        elif self.method == "web":
                            web_add(url=self.url, clue_data=clue, shortnames=self.shortnames)

                        self.json_backup.append(clue)

            except KeyboardInterrupt:
                self.save()
                import sys

                sys.quit()

            except:
                print(f"An error occurred with game {clues.show}")
                self.error.append(url)

            else:
                elapsed = time.perf_counter() - start
                print(f"Successfully scraped game {clues.show} Time taken: {elapsed:.2f} seconds")
                self.success.append(url)

                time.sleep(0.5)

        self.save()


if __name__ == "__main__":
    _ = External(filename="downloads.txt", output="media")
    _.clean()
    _.download()
