import requests
from bs4 import BeautifulSoup, element
from pyjsparser import parse

import time
import re
import string
import datetime
from collections import defaultdict, OrderedDict

import pathlib
import os

CACHE = False
CACHE_PATH = ""

BASE_URL = "http://www.j-archive.com"

DELAY = 5


class Webpage(object):
    def __init__(self, resource: str) -> None:
        if len(resource) == 0:
            raise ValueError("resource argument cannot be empty")

        if BASE_URL[-1] == "/":
            self.url = f"{BASE_URL}{resource}"

        else:
            self.url = f"{BASE_URL}/{resource}"

        self.storage = pathlib.Path(CACHE_PATH, resource).absolute()

    def __repr__(self) -> str:
        return self.url

    def get(self):
        if self.storage.exists() and CACHE:
            print("using cache")
            with open(self.storage, "r") as store_file:
                page = store_file.read()

        else:
            print("downloading")
            time.sleep(DELAY)

            page = requests.get(self.url)

            if page.status_code != 200:
                return False, {"message": f"failed to receive webpage data"}

            page = page.text

            if CACHE:
                self.storage.parent.mkdir(parents=True, exist_ok=True)

                with open(self.storage, "w") as store_file:
                    store_file.write(page)

        return True, BeautifulSoup(page, "lxml")


# class Season(object):
#     def __init__(self, identifier: str) -> None:
#         self.url = Webpage(resource=f"showseason.php?season={identifier}")

#         time.sleep(DELAY)
#         self.data = self.url.get().table

#         self.games = [game.get("href") for game in self.data.find_all("a") if "game_id" in game.get("href")]


class Game(object):
    def __init__(self, identifier: str) -> None:
        self.url = Webpage(resource=f"showgame.php?game_id={identifier}")

        success, self.data = self.url.get()

        if not success:
            raise NotImplementedError("Error handling en route")

        self.board: defaultdict = defaultdict(dict)
        self.show = -1
        self.json: list = list()

        self.get_show_and_date()
        self.get_categories()
        self.get_clues()

        self.schema()

    def __repr__(self):
        return f"<GAME URL:{self.url} SHOW: {self.show}>"

    def schema(self, board: dict = {}, show: int = None, date: datetime.datetime = None) -> dict:
        if board == {}:
            board = self.board

        if show == None:
            show = self.show

        if date == None:
            date = self.date

        for round_, categories in board.items():
            for _, category in categories.items():
                for value, clue in category["clues"].items():
                    self.json.append(
                        {
                            "show": show,
                            "date": date,
                            "category": category["name"],
                            "complete": category["complete"],
                            "answer": clue["answer"],
                            "question": clue["question"],
                            "external": clue["external"],
                            "value": value,
                            "round": round_,
                        }
                    )

        return self.json

    def get_show_and_date(self, show_title: str = "") -> tuple:
        """Using the div with the ID matching "game_title, match to the supplied regex string. It contains
        the show number, and the date the show aired, using a number of written out, English words for the day
        of the week and of the month. Occasionally, if it's a "special" season, there will also be a title for
        the season written before the Show number.
        
        Prior to saving the results, convert the show string into an `int`, and the date string into a `datetime`

        If the show is one of the "special" seasons, in order to maintain the show number as an integer, invert to
        negative, and subtract some constants to keep separation. The only reason these numbers are chosen is to
        provide clear distinction between these seasons' games.
        """
        if show_title == "":
            show_title = self.data.find(id="game_title").text

        (title, show, date) = re.findall(pattern=r"^(.*)?[Ss]how #(\d{0,6}) - (.*)$", string=show_title)[0]

        self.date = datetime.datetime.strptime(date, "%A, %B %d, %Y").date().isoformat()
        self.show = int(show)

        return (show, date)

    def get_categories(self, game_board: str = "") -> list:
        """Extract the categories from each round of the game. This assumes there are 6 categories in each game,
        which appears to have been the case since the original Trebek run of the show.

        Using a combination of integer division (floor) and modulo, fill out the dictionary for each round with
        the category name, the assumption that it is complete (which can be "corrected" later) and an empty
        `defaultdict` for the clues.
        """
        if game_board == "":
            game_board = self.data.find_all("td", class_="category_name")

        resp = list()

        for num, category in enumerate(game_board):
            self.board[num // 6][num % 6] = {
                "name": category.text,
                "complete": True,
                "clues": defaultdict(dict),
            }

            resp.append(category)

        return resp

    def get_clues(self, game_board: str = "") -> dict:
        """Start pulling out the question data!
        """
        if game_board == "":
            game_board = self.data

        resp = list()

        # The variable `ROUND_MAP` has a "legend" for the HTML IDs or class names in which the data is stored
        ROUND_MAP = (
            ("jeopardy_round", "round", "clue"),
            ("double_jeopardy_round", "round", "clue"),
            ("final_jeopardy_round", "final_round", "category"),
        )

        # So iterating over each of the items in the legend, corresponding to the rounds in Jeopardy!
        for self.round_, r_name in enumerate(ROUND_MAP):
            if (round_html := game_board.find("div", id=r_name[0])) is None:
                break

            # Use each table that has the game board for each round. Note that Final Jeopardy! and any Tiebreaker
            # rounds (for instance in game #7709) are within the same "final_jeopardy" `div`. They're in separate
            # tables within that div, but which both use the same class name "final_round"
            for count, board in enumerate(round_html.find_all("table", class_=r_name[1])):

                # Continuing to loop over each ROW in the table, without the `recursive` flag set to `False`. This
                # only searches the first sublevel, rather than matching every single child `tr` node.
                # Note this loop corresponds to each ROW of the game board, meaning the `value` index set by the
                # `enumerate` refers to the $ value in the game, and  also that each subsequent item found is
                # in a different category of the game.
                for self.value, text in enumerate(board.find_all("tr", recursive=False)):

                    # Now looking through each row of table, loop through each COLUMN. This provides the CATEGORY
                    # index of the clue. Still using the ROUND_MAP legend, though, because J-Archive has the JS
                    # containing the clue information in different places depending on the round...
                    # Note that, because this loop only looks at the specific class name, this ignores the first
                    # actual row of the table, which has category names. We already pulled that info anyways!
                    for self.column, self.clue in enumerate(text.find_all("td", class_=r_name[2])):

                        # And now that we're at a specific clue, extract the clue data from the BS4 element
                        set_ = self.get_clue_data()

                        # Then save that to the Game object.
                        self.board[self.round_][self.column if self.round_ < 2 else count]["clues"][self.value] = set_

    def get_clue_data(self, clue_data="") -> dict:
        """Extracts the clue information (primarily from some JS code on the web page) and sets both the `external` and
        `complete flags as needed.
        """
        if clue_data == "":
            clue_data = self.clue

        # Prep default flags
        external, complete = (False, True)

        # Check to see if the square has a question on the square. In particular on some of the older boards, or whenever
        # the game runs "long" there may be some incomplete boards. If the clue data is available though:
        if clue_data.find("div", onmouseout=True) is not None:

            # Extract the answer element from the JS function `onmouseout`
            answer = pjs(clue_data.find("div").get("onmouseout"))

            # Extract the question element from the JS function `onmouseover`
            question = pjs(clue_data.find("div").get("onmouseover")).find("em", class_="correct_response")

            # Check to see if the answer has any external media (like pictures, sound clips, video etc.) by looking
            # for an <a> tag.
            if answer.a is not None:

                # If it has one, set the external flag to true. Note this flag is set "per-clue".
                external = True

                # Create a list containing all of the external media found on the answer. Some clues have more than
                # one  external media item listed. Then pass that list to the function that stores download info in a
                # separate file.
                urls = [url.get("href") for url in answer.find_all("a")]
                get_external_media(round_=f"{self.show}_{self.round_}_{self.column}_{self.value}", urls=urls)

        else:
            # If the clue doesn't happen to have any content, just set it to blank BS4 elements, and mark the CATEGORY
            # as being incomplete.
            self.board[self.round_][self.column]["complete"] = False
            question = BeautifulSoup("", "lxml")
            answer = BeautifulSoup("", "lxml")

        # Return all that juicy clue information to be stored!
        return {"question": question.text, "answer": answer.text, "external": external}


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


def get_external_media(round_: str, urls: list) -> None:
    """Create a list of the external media found in the clue. The list will have identifiers for the show, round,
    question, and an incrementing letter for each item in the clue. This file can then be run in a bash script
    to download the media, which hopefully all exists...
    """
    downloads = [f"curl -O downloads/{round_}{string.ascii_lowercase[i]} {j}\n" for i, j in enumerate(urls)]
    with open("downloads.txt", "a") as file:
        file.writelines(downloads)


def pjs(function: str):
    """ A simple wrapper function around the super useful pyjsparser library. This steps through all of the AST tree
    of the library to only return the HTML element in the function.
    """
    return BeautifulSoup(parse(function)["body"][0]["expression"]["arguments"][2]["value"], "lxml")


# def get_seasons(start: int, stop: int, include_special: bool) -> list:
#     seasons = Webpage(resource="listseasons.php").get().find(id="content").find_all("a")
#     urls = (a.get("href").split("=")[1] for a in seasons)

#     standard = [Season(id) for id in (url for url in urls if url.isnumeric()) if (start <= int(id) <= stop)]
#     specials = [Season(id) for id in urls if (not id.isnumeric()) & include_special]

#     return standard + specials


def resource_id(url: str) -> str:
    if type(url) != str:
        raise TypeError("variable must be a string")

    return url.split("=")[-1]


def get_seasons(page: BeautifulSoup, start: int, stop: int, include_special: bool) -> tuple:
    try:
        all_seasons = page.find(id="content").find_all("a")
        all_seasons = [season.get("href") for season in all_seasons]

        if len(all_seasons) < 1:
            raise AttributeError

        season_ids = (resource_id(url=season) for season in all_seasons)

        return (
            True,
            [num for num in season_ids if ((num.isnumeric() and (start <= int(num) <= stop)) or include_special)],
        )

    except AttributeError:
        return False, {"message": "the webpage may have changed and cannot be parsed as is"}


def get_games(identifier: int) -> dict:
    games = dict()

    load = Webpage(resource=f"showseason.php?season={identifier}")

    success, page = load.get()

    if not success:
        raise NotImplementedError("Error handling en route")

    table = page.table

    return {
        "url": load.url,
        "games": {
            resource_id(url=game.get("href")): False for game in table.find_all("a") if "game_id" in game.get("href")
        },
    }

