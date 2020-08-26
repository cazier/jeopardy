import requests
from bs4 import BeautifulSoup, element
from pyjsparser import parse

import time
import re
import string
import datetime
from collections import defaultdict

SHOW_DATE_MATCH = re.compile(r"^Show #(\d{0,6}) - (.*)$")


class Links(object):
    def __init__(self, type_: str = "", identifier: str = "", url: str = "") -> None:
        if type_ == "season":
            self.url = f"http://www.j-archive.com/showseason.php?season={identifier}"

        else:
            self.url = url

    def __repr__(self) -> str:
        return self.url

    def get(self):
        return BeautifulSoup(requests.get(self.url).text, "lxml")


class Season(object):
    def __init__(self, identifier: str) -> None:
        self.special: bool = not identifier.isnumeric()
        self.url = Links(url=f"http://www.j-archive.com/showseason.php?season={identifier}")

        time.sleep(0.5)
        self.data = self.url.get().table
        
        self.games = [game.get("href") for game in self.data.find_all("a") if "game_id" in game.get("href")]


class Game(object):
    def __init__(self, url: str) -> None:
        self.url = Links(url=url)

        self.data = self.url.get()
        self.board: defaultdict = defaultdict(dict)
        self.show = -1
        self.json: list = list()

        self.get_show_and_date()
        self.get_categories()
        self.get_clues()

        self.schema()

    def __repr__(self):
        return f"<GAME URL:{self.url} SHOW: {self.show}>"

    def schema(self):
        for round_, categories in self.board.items():
            for _, category in categories.items():
                for value, clue in category["clues"].items():
                    self.json.append(
                        {
                            "show": self.show,
                            "date": self.date,
                            "category": category["name"],
                            "complete": category["complete"],
                            "answer": clue["answer"],
                            "question": clue["question"],
                            "external": clue["external"],
                            "value": value,
                            "round": round_,
                        }
                    )

    def get_show_and_date(self):
        """Using the div with the ID matching "game_title, match to the above compiled regex string. It contains
        the show number, and the date the show aired, using a number of written out, English words for the day
        of the week and of the month.
        
        Prior to saving the results, convert the show string into an `int`, and the date string into a `datetime`
        """
        [(s, d)] = SHOW_DATE_MATCH.findall(self.data.find(id="game_title").text)

        self.show = int(s)
        self.date = datetime.datetime.strptime(d, "%A, %B %d, %Y").date().isoformat()

    def get_categories(self):
        """Extract the categories from each round of the game. This assumes there are 6 categories in each game,
        which appears to have been the case since the original Trebek run of the show.

        Using a combination of integer division (floor) and modulo, fill out the dictionary for each round with
        the category name, the assumption that it is complete (which can be "corrected" later) and an empty
        `defaultdict` for the clues.
        """
        for num, category in enumerate(self.data.find_all("td", class_="category_name")):
            self.board[num // 6][num % 6] = {
                "name": category.text,
                "complete": True,
                "clues": defaultdict(dict),
            }

    def get_clues(self) -> None:
        """Start pulling out the question data!
        """

        # The variable `ROUND_MAP` has a "legend" for the HTML IDs or class names in which the data is stored
        ROUND_MAP = (
            ("jeopardy_round", "round", "clue"),
            ("double_jeopardy_round", "round", "clue"),
            ("final_jeopardy_round", "final_round", "category"),
        )

        # So iterating over each of the items in the legend, corresponding to the rounds in Jeopardy!
        for self.round_, r_name in enumerate(ROUND_MAP):

            # Use each table that has the game board for each round. Note that Final Jeopardy! and any Tiebreaker
            # rounds (for instance in game #7709) are within the same "final_jeopardy" `div`. They're in separate
            # tables within that div, but which both use the same class name "final_round"
            for count, board in enumerate(self.data.find("div", id=r_name[0]).find_all("table", class_=r_name[1])):

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

    def get_clue_data(self) -> dict:
        """Extracts the clue information (primarily from some JS code on the web page) and sets both the `external` and
        `complete flags as needed.
        """

        # Prep default flags
        external, complete = (False, True)

        # Check to see if the square has a question on the square. In particular on some of the older boards, or whenever
        # the game runs "long" there may be some incomplete boards. If the clue data is available though:
        if self.clue.find("div", onmouseout=True) is not None:

            # Extract the answer element from the JS function `onmouseout`
            answer = pjs(self.clue.find("div").get("onmouseout"))

            # Extract the question element from the JS function `onmouseover`
            question = pjs(self.clue.find("div").get("onmouseover")).find("em", class_="correct_response")

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


def pjs(function: str):
    """ A simple wrapper function around the super useful pyjsparser library. This steps through all of the AST tree
    of the library to only return the HTML element in the function.
    """
    return BeautifulSoup(parse(function)["body"][0]["expression"]["arguments"][2]["value"], "lxml")
