import requests
from bs4 import BeautifulSoup
from pyjsparser import parse

import re
import string
import datetime
from pprint import pprint
from collections import defaultdict

LAST_SEASON = 36

SHOW_DATE_MATCH = re.compile(r"^Show #(\d{0,6}) - (.*)$")
ROUND_MATCH = re.compile(r"^clue_([DF]?J|TB)(?:_(\d)_(\d))?")


class Links(object):
    def __init__(self, type_: str, identifier: str = "", url: str = "") -> None:
        if type_ == "season":
            self.url = f"http://www.j-archive.com/showseason.php?season={identifier}"

        elif type_ == "game":
            self.url = url

    def __repr__(self) -> str:
        return self.url

    def get(self):
        return BeautifulSoup(requests.get(self.url).text, "lxml")


class Season(object):
    def __init__(self, identifier: str) -> None:
        self.identifier: str = identifier
        self.special: bool = not identifier.isnumeric()
        self.url = Links(type_="season", identifier=identifier)

        self.data = self.url.get().table

    def get_games(self):
        self.games = [game.get("href") for game in self.data.find_all("a") if "game_id" in game.get("href")]


class Game(object):
    def __init__(self, url: str) -> None:
        self.url = Links(type_="game", url=url)

        self.data = self.url.get()
        self.board: defaultdict = defaultdict(dict)

        self.get_show_and_date()
        self.get_clues()

    def get_show_and_date(self):
        """Using the div with the ID matching "game_title, match to the above compiled regex string. It contains
        the show number, and the date the show aired, using a number of written out, English words for the day
        of the week and of the month.
        
        Prior to saving the results, convert the show string into an `int`, and the date string into a `datetime`
        """
        [(s, d)] = SHOW_DATE_MATCH.findall(self.data.find(id="game_title").text)

        self.show = int(s)
        self.date = datetime.datetime.strptime(d, "%A, %B %d, %Y").date().isoformat()

    def get_clues(self):
        for r_num, r_name in enumerate(("jeopardy_round", "double_jeopardy_round", "final_jeopardy_round"), 1):
            if r_num < 3:
                round_class = "round"
            else:
                round_class = "final_round"

            board = self.data.find("div", id=r_name).find("table", class_=round_class)

            for clue_value, text in enumerate(board.find_all("tr", recursive=False)):
                if clue_value == 0:
                    for column, category in enumerate(text.find_all("td", class_="category_name"), 1):
                        self.board[r_num][column] = {
                            "name": category.text,
                            "complete": True,
                            "clues": defaultdict(dict),
                        }
                else:
                    if r_num < 3:
                        for column, clue in enumerate(text.find_all("td", class_="clue"), 1):
                            if (content := clue.find("div", onmouseout=True)) is not None:
                                question = pjs(content.get("onmouseout"))
                                answer = pjs(clue.find("div", onmouseover=True).get("onmouseover")).find(
                                    "em", class_="correct_response"
                                )
                                external = False

                                if question.a is not None:
                                    external = True
                                    urls = [url.get("href") for url in question.find_all("a")]

                                    get_external_media(round_=f"{self.show}_{r_num}_{column}_{clue_value}", urls=urls)

                            else:
                                self.board[r_num][column]["complete"] = False
                                question = BeautifulSoup("", "lxml")
                                answer = BeautifulSoup("", "lxml")

                            self.board[r_num][column]["clues"][clue_value]["question"] = question.text
                            self.board[r_num][column]["clues"][clue_value]["answer"] = answer.text
                            self.board[r_num][column]["clues"][clue_value]["external"] = external

                    elif r_num >= 3:
                        question = pjs(board.find("div", onmouseout=True).get("onmouseout"))
                        answer = pjs(board.find("div", onmouseover=True).get("onmouseover")).find(
                            "em", class_="correct_response"
                        )
                        external = False

                        if question.a is not None:
                            external = True
                            urls = [url.get("href") for url in question.find_all("a")]

                            get_external_media(round_=f"{self.show}_{r_num}_{column}_{clue_value}", urls=urls)

                        self.board[r_num][1]["clues"][0]["question"] = question.text
                        self.board[r_num][1]["clues"][0]["answer"] = answer.text
                        self.board[r_num][1]["clues"][0]["external"] = external

            # elif r_num == 3:
            #     board = self.data.find("div", id=r_name).find("table", class_="round")

            #     for clue_value, text in enumerate(board.find_all("tr", recursive=False)):
            #         if clue_value == 0:
            #             for column, category in enumerate(text.find_all("td", class_="category_name"), 1):
            #                 self.board[r_num][column] = {
            #                     "name": category.text,
            #                     "complete": True,
            #                     "clues": defaultdict(dict),
            #                 }


def get_external_media(round_: str, urls: list) -> None:
    downloads = [f"curl -O downloads/{round_}{string.ascii_lowercase[i]} {j}\n" for i, j in enumerate(urls)]
    with open("downloads.txt", "a") as file:
        file.writelines(downloads)


def pjs(function: str, index: int = 2):
    return BeautifulSoup(parse(function)["body"][0]["expression"]["arguments"][index]["value"], "lxml")


a = Game(url="http://www.j-archive.com/showgame.php?game_id=5757")
b = Game(url="http://www.j-archive.com/showgame.php?game_id=5922")
# pprint(a.clues)
