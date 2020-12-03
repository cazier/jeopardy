import requests
from bs4 import BeautifulSoup, element
from pyjsparser import parse

import os
import re
import json
import time
import string
import pathlib
import datetime
from collections import defaultdict
import urllib.parse as urlparse


CACHE = False
CACHE_PATH = ""

BASE_URL = "http://www.j-archive.com"

DELAY = 5

EXTERNAL_LINKS: list = list()


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
            with open(self.storage, "r") as store_file:
                page = store_file.read()

        else:
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


class NoInputSuppliedError(Exception):
    def __init__(self, message="The BeautifulSoup object was empty. Check the HTML to ensure data is supplied."):
        self.message = message

        super().__init__(self.message)


def get_seasons(page: BeautifulSoup):
    try:
        all_seasons = page.find(id="content").find_all("a")
        all_seasons = [season.get("href") for season in all_seasons]

        results = [resource_id(url=season) for season in all_seasons]

        if len(results) < 1:
            raise NoItemsFoundError()

        results.sort(key=lambda k: int(k) if k.isdigit() else float("inf"))

        return results

    except AttributeError:
        raise ParsingError()


def get_games(page: BeautifulSoup) -> list:
    try:
        all_games = page.find(id="content").find_all("a")
        all_games = [game.get("href") for game in all_games]

        results = [resource_id(url=game) for game in all_games]

        if len(results) < 1:
            raise NoItemsFoundError()

        results.sort(key=lambda k: int(k) if k.isdigit() else float("inf"))

        return results

    except AttributeError:
        raise ParsingError()


def get_game_title(page: BeautifulSoup) -> tuple:
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

        return (show, date)

    except ValueError:
        raise ParsingError("Date format could not be read")


def get_categories(page: BeautifulSoup) -> dict:
    categories = page.find_all("td", class_="category_name")

    if (num := len(categories)) < 1:
        raise NoItemsFoundError()

    elif num not in [13, 14]:
        raise ParsingError("An incorrect number of categories was found.")

    names = [category.text for category in categories]

    results = {i: j for i, j in zip(generate_headers(length=num), names)}

    return results


def get_clues(page: BeautifulSoup) -> list:
    clues = page.find_all("div", onmouseover=True)

    if len(clues) < 1:
        raise NoItemsFoundError()

    else:
        return clues


def get_clue_data(clue: BeautifulSoup) -> dict:
    clue = BeautifulSoup(str(clue), "lxml")

    if clue.html == None:
        raise NoInputSuppliedError()

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
            category, value, round_ = 0, 0, 2

        elif round_ == "TB":
            category, value, round_ = 1, 0, 2

        else:
            category, value = map(lambda k: int(k) - 1, details[2:])

            if round_ == "DJ":
                round_ = 1

            elif round_ == "J":
                round_ = 0

            else:
                raise ParsingError(message="The clue number identifier didn't match 'J', 'DJ', or 'FJ'")

        return {
            "category": category,
            "value": value,
            "answer": answer,
            "question": question.text,
            "external": external,
            "round": round_,
        }

    except AttributeError:
        raise ParsingError()

    except ValueError:
        raise ParsingError(message=f"The clue number identifier was malformed. (It should look like 'clue_J_#_#')")


def get_board(page: BeautifulSoup) -> list:
    show, date = get_game_title(page=page)
    category_names = get_categories(page=page)
    clues = [get_clue_data(clue=clue) for clue in get_clues(page=page)]

    board: dict = defaultdict(dict)

    for category in category_names:
        round_number, category_number = map(int, category.split("_"))

        board[round_number][category_number] = list()

    for clue in clues:
        board[clue["round"]][clue["category"]].append(clue)

    results: list = list()

    for round_number, categories in board.items():
        for category_number, question_sets in categories.items():
            for question_number, item in enumerate(question_sets):
                if len(question_sets) < 5 and round_number < 2:
                    item["complete"] = False

                else:
                    item["complete"] = True

                item["category"] = category_names[f"{item['round']}_{item['category']}"]

                item["show"] = show
                item["date"] = date

                get_external_media(item=item, category=category_number)

                item["answer"] = str(item["answer"])

                results.append(item)

    return results


### HELPER FUNCTIONS
def pjs(function: str) -> tuple:
    """ A simple wrapper function around the super useful pyjsparser library. This steps through all of the AST tree
    of the library to only return the HTML element in the function.
    """
    if function == "":
        raise NoInputSuppliedError("The javascript function supplied was empty")

    try:
        arguments = parse(function)["body"][0]["expression"]["arguments"]

        return BeautifulSoup(arguments[0]["value"], "lxml"), BeautifulSoup(arguments[2]["value"], "lxml")

    except (KeyError, IndexError):
        raise ParsingError("The javascript with the clues/answers failed to parse")


def resource_id(url: str) -> str:
    if type(url) != str:
        raise TypeError("variable must be a string")

    return url.split("=")[-1]


def generate_headers(length: int) -> list:
    if length > 14:
        raise ParsingError()

    return [f"{round_}_{category}" for round_ in range(0, 3) for category in range(0, 6)][:length]


def get_external_media(item: dict, category: int) -> None:
    files = item["answer"].find_all("a")

    base = "{show:05d}_{round}_{category}_{value}".format(
        show=item["show"], round=item["round"], category=category, value=item["value"]
    )

    for key, file in zip(string.ascii_lowercase, files):
        url_path = file.get("href")

        if url_path == "":
            raise ParsingError(f"The external file for a clue (id: {base}{key} has no url")

        url = urlparse.urljoin(f"{BASE_URL}/media", url_path)

        EXTERNAL_LINKS.append((f"{base}{key}", url))
