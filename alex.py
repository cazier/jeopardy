import sqlite3
import random
import itertools
import datetime

import requests

import config

if config.debug:
    from pprint import pprint


class Game(object):
    """Class definining the game itself, containing each player and the board itself. """

    def __init__(self, size: int, room: str):
        self.size: int = size
        self.game_name: str = config.game_name
        self.room = room

        self.round: int = config.round_

        self.score = Scoreboard()

        self.buzz_order: list = list()

        self.current_set = None

        if config.debug:
            self.add_player("Alex")
            self.add_player("Brad")
            self.add_player("Carl")

            self.score.players["Alex"]["score"] = 1500
            self.score.players["Brad"]["score"] = 500
            self.score.players["Carl"]["score"] = 750

    def add_player(self, name: str):
        """Add a player to the game with a starting score of zero (0).

        Required Arguments:

        name (str) -- The player's name
        """
        self.score.add(name)

    def make_board(self):
        """Create a game board.

        This will track the number of question/answer sets in each round, and runs the function `self.board.add_wagers()`
        to ensure the "Daily Doubles" are placed around the board.
        """
        self.remaining_content = config.sets if config.debug else self.size * 5

        self.board = Board(segment=self.round, size=self.size)

        self.board.add_wagers()

    def reset(self, reset_score: bool = False, reset_players: bool = False):
        """Reset the game to play again!

        Required Arguments:

        `reset_score` (bool) -- Keep the players, but set score to zero. (Basically, rematch)
        `reset_players` (bool) -- Reset both players and score (Basically, a whole new game)
        """
        if reset_players:
            self.score.reset(type_="players")

        elif reset_score:
            self.score.reset(type_="score")

        self.round = 0

    def round_text(self, upcoming: bool = False) -> str:
        """Return the text describing the title of the, by default, current round.

        Optional arguments:

        `upcoming` (bool) -- Setting to display the future round title (default `False`)

        """
        display_round = self.round + 1 if upcoming else self.round

        if display_round == 0:
            return "{copyright}!".format(copyright=self.game_name)

        elif display_round == 1:
            return "Double {copyright}!".format(copyright=self.game_name)

        elif display_round == 2:
            return "Final {copyright}!".format(copyright=self.game_name)

        elif display_round == 3:
            return "Tiebreaker {copyright}!".format(copyright=self.game_name)

        else:
            return "An error has occurred...."

    def start_next_round(self):
        """Increment the round counter and remake the board with `self.make_board()`"""

        self.round += 1
        self.make_board()

    def html_board(self):
        """Using `zip()` return the game board, transposed, as needed to make the HTML representation"""
        return zip(*[category.sets for category in self.board.categories])

    def get(self, identifier: str):
        """Returns the `Content` object referred to by a specific identifier. Additionally ensures the remaining
        content counter is decremented, as required to play.

        Required Arguments:

        identifier (str) -- A three piece identifier that specifies the content to return
        """
        self.remaining_content -= 1
        entry, category, value = identifier.split("_")

        if entry == "q":
            print(self.board.categories[0].sets, value)
            response = self.board.categories[int(category)].sets[int(value)]
            self.current_set = response.get_content()
            return response.get()

        else:
            print("An error has occurred....")
            return False

    def buzz(self, name: str):
        """Method tracking that a player has "buzzed in". Because the method `.appends()` the player name,
        the game uses the `index` -1 to get the _first_ buzzer.

        Required Arguments:

        name (str) -- The name of the player that buzzed in.
        """
        if name in self.score:
            self.buzz_order.append(name)

    def heading(self) -> str:
        if self.round <= 2:
            return "Daily Double!"

        else:
            return "Final Jeopardy!"


class Scoreboard(object):
    def __init__(self):
        self.players: dict = dict()
        self.num = 0
        self.wagerer = None

    def __contains__(self, item: str) -> bool:
        return item in self.players.keys()

    def add(self, other: str) -> bool:
        if other not in self:
            self.players[other] = {"score": 0, "wager": {"amount": 0, "question": ""}}

            return True

        else:
            return False

    def __len__(self) -> int:
        return len(self.players.keys())

    def __getitem__(self, player: str) -> int:
        return self.players[player]["score"]

    def __setitem__(self, player: str, wager: tuple) -> None:
        k, v = wager

        self.players[player]["wager"][k] = v

        self.num += 1

    def emit(self) -> dict:
        return {i: self.players[i]["score"] for i in self.players.keys()}

    def keys(self) -> list:
        return list(self.players.keys())

    def sort(self, **kwargs) -> list:
        return [i[0] for i in sorted(self.players.items(), key=lambda k: k[1]["score"], **kwargs)]

    def wager(self, player: str) -> dict:
        return {
            **self.players[player]["wager"],
            "player": player,
            "score": self[player],
        }

    def reset(self, type_: str) -> None:
        # TODO: This won't work, for score, because the wager dictionary has been refactored.
        #       Need to fix this, and possibly (ideally), clean up this super deep dict traversal
        if type_ == "players":
            self.players = dict()

        elif type_ == "score":
            self.players = {i: {"score": 0, "wager": 0} for i in self.players}

    def update(self, game, correct: int) -> None:
        if self.wagerer is None:
            player = game.buzz_order[-1]

            value = ((game.current_set.value + 1) * (game.round + 1) * 200) * (-1 + (2 * correct))

        else:
            player = self.wagerer
            value = self.players[player]["wager"]["amount"] * (-1 + (2 * correct))

        self.players[player]["score"] += value

        self.players[player]["wager"]["amount"] = 0
        self.wagerer = None


class Board(object):
    """Class to hold the Jeopardy game board. Contains methods to get categories and content."""

    def __init__(self, segment: int, size: int):
        self.size: int = size if segment < 3 else 1
        self.round: int = segment
        self.categories: list = list()

        self.new_content()

    def new_content(self, **kwargs) -> None:
        game = requests.get(config.api_endpoint, data=kwargs).json()

        for index, details in enumerate(game):
            self.categories.append(Category(index=index, name=details["category"]["name"], sets=details["sets"]))

    def add_wagers(self) -> None:
        """Randomly assign the "Daily Double" to the correct number of sets per round."""
        doubles = itertools.product(range(len(self.categories)), range(len(self.categories[0].sets)))

        for daily_double in random.sample(list(doubles), [0, 1, 2, 0, 0][self.round]):
            if config.debug:
                daily_double = (0, 0)

            self.categories[daily_double[0]].sets[daily_double[1]].wager = True


class Category(object):
    """Class to hold one of the categories (ostensibly columns) on a Jeopardy game board."""

    def __init__(self, name: str, index: int, sets: list):
        self.category = name
        self.index = index
        self.sets: list = list()

        for set_ in sets:
            self.sets.append(Content(details=set_, category_index=index))

        self.sets.sort()

    def __str__(self):
        """Creates a string representation of the category, returning just the title"""
        return self.category

    def __repr__(self):
        """Duplicates `__str__`"""
        return str(self)


class Content(object):
    """Class to hold a single answer/question set"""

    def __init__(self, details: dict, category_index: int):
        self.category_index = category_index
        self.shown = False

        self.wager = False

        self.answer = details["answer"]
        self.question = details["question"]
        self.value = details["value"]
        self.year = datetime.datetime.fromisoformat(details["date"]).strftime("%Y")

    def __lt__(self, other):
        return self.value < other.value

    # def __str__(self):
    #     """Creates a string representation of the set's value"""
    #     return str(self.value)

    # def __repr__(self):
    #     """Duplicates `__str__`"""
    #     return str(self)

    def id(self):
        """Returns the unique identifier of the set"""
        return f"{self.category_index}_{self.value}"

    def get(self):
        """Gets the set, as done within the Jinja loading of the webpage"""
        self.shown = True

        return {
            "question": self.question,
            "answer": self.answer,
            "wager": self.wager,
        }

    def get_content(self):
        """Gets the set, as done within the Jinja loading of the webpage"""
        return self
