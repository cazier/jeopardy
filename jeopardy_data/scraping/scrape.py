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

        self.storage = pathlib.Path(CACHE_PATH, resource.replace("?", "_")).absolute()

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


class NoItemsFoundError(Exception):
    def __init__(self):
        self.message = "The page was parsed properly, however no results were found. It may be empty?"

        super().__init__(self.message)


class ParsingError(Exception):
    def __init__(self, message="The page was unable to be parsed. Check the HTML and text as it may have changed."):
        self.message = message

        super().__init__(self.message)


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


def get_external_media(round_: str, urls: list) -> None:
    """Create a list of the external media found in the clue. The list will have identifiers for the show, round,
    question, and an incrementing letter for each item in the clue. This file can then be run in a bash script
    to download the media, which hopefully all exists...
    """
    downloads = [f"curl -O downloads/{round_}{string.ascii_lowercase[i]} {j}\n" for i, j in enumerate(urls)]
    with open("downloads.txt", "a") as file:
        file.writelines(downloads)


def get_seasons(page: BeautifulSoup, start: int, stop: int, include_special: bool) -> tuple:
    if stop <= start:
        raise SyntaxError("The stop season must be greater than the start season")

    try:
        all_seasons = page.find(id="content").find_all("a")
        all_seasons = [season.get("href") for season in all_seasons]

        season_ids = (resource_id(url=season) for season in all_seasons)

        results = list()

        for num in season_ids:
            if num.isnumeric() and (start <= int(num) < stop):
                results.append(num)

            elif (not num.isnumeric()) and include_special:
                results.append(num)

        if len(results) < 1:
            raise NoItemsFoundError()

        return True, results

    except AttributeError:
        raise ParsingError()


def get_games(page: BeautifulSoup) -> dict:
    try:
        all_games = page.find(id="content").find_all("a")

        results = dict()

        for game in all_games:
            url = game.get("href")

            if "game_id" in url:
                results[resource_id(url=url)] = False

        if len(results.keys()) < 1:
            raise NoItemsFoundError()

        return True, results

    except AttributeError:
        raise ParsingError()


def get_show_and_date(page: BeautifulSoup) -> dict:
    pattern = r"^(.*)?[Ss]how #(\d{0,6}) - (.*)$"

    game = page.find("div", id="game_title")

    if game == None:
        raise NoItemsFoundError()

    else:
        game = game.text.strip()

    matches = re.findall(pattern=pattern, string=game)

    if matches == []:
        raise ParsingError("Unable to parse show title into individual parts using regex")

    else:
        [(title, show, date)] = matches

    try:
        date = datetime.datetime.strptime(date, "%A, %B %d, %Y").date().isoformat()
        show = int(show)

        return {"show": show, "date": date}

    except ValueError:
        raise ParsingError("Date format could not be read")


def get_clues(page: BeautifulSoup) -> list:
    clues = page.find_all("div", onmouseover=True)

    if len(clues) < 1:
        raise NoItemsFoundError()

    else:
        return clues


def get_clue_data(clue: BeautifulSoup) -> dict:
    try:
        numbers, answer = pjs(clue.find("div").get("onmouseout"))

        if answer.a is None:
            external = False

        else:
            external = True

        _, question = pjs(clue.find("div").get("onmouseover"))
        question = question.find("em", class_="correct_response")

        details = numbers.text.split("_")

        round_ = details[1]

        if round_ == "FJ":
            category, value = -1, 0

        else:
            category, value = map(int, details[2:])

        return {
            "category": category,
            "value": value,
            "answer": answer.text,
            "question": question.text,
            "external": external,
        }

    except AttributeError:
        raise ParsingError()

    except ValueError:
        raise ParsingError(message=f"The clue number identifier was malformed. (It should look like 'clue_J_#_#')")


def pjs(function: str) -> tuple:
    """ A simple wrapper function around the super useful pyjsparser library. This steps through all of the AST tree
    of the library to only return the HTML element in the function.
    """
    try:
        arguments = parse(function)["body"][0]["expression"]["arguments"]

        return BeautifulSoup(arguments[0]["value"], "lxml"), BeautifulSoup(arguments[2]["value"], "lxml")

    except (KeyError, IndexError):
        raise ParsingError("The javascript with the clues/answers failed to parse")


def resource_id(url: str) -> str:
    if type(url) != str:
        raise TypeError("variable must be a string")

    return url.split("=")[-1]

