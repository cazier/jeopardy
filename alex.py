import sqlite3
import random
import itertools

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

        self.current_question = None

        if config.debug:
            self.add_player("Alex")
            self.add_player("Brad")
            # self.add_player("Carl")

            self.score.players["Alex"]["score"] = 1500
            self.score.players["Brad"]["score"] = 500
            # self.score.players["Carl"]["score"] = 750

    def add_player(self, name: str):
        """Add a player to the game with a starting score of zero (0).

        Required Arguments:

        name (str) -- The player's name
        """
        self.score << name

    def make_board(self):
        """Create a game board.

        This will track the number of questions in each round, and runs the function `self.board.add_wagers()`
        to ensure the "Daily Doubles" are placed around the board.
        """
        self.remaining_questions = config.questions if config.debug else self.size * 5

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

        self.round = 1

    def round_text(self, upcoming: bool = False) -> str:
        """Return the text describing the title of the, by default, current round.

        Optional arguments:

        `upcoming` (bool) -- Setting to display the future round title (default `False`)

        """
        display_round = self.round + 1 if upcoming else self.round

        if display_round == 1:
            return "{copyright}!".format(copyright=self.game_name)

        elif display_round == 2:
            return "Double {copyright}!".format(copyright=self.game_name)

        elif display_round == 3:
            return "Final {copyright}!".format(copyright=self.game_name)

        elif display_round == 4:
            return "Tiebreaker {copyright}!".format(copyright=self.game_name)

        else:
            return "An error has occurred...."

    def start_next_round(self):
        """Increment the round counter and remake the board with `self.make_board()`"""

        self.round += 1
        self.make_board()

    def html_board(self):
        """Using `zip()` return the game board, transposed, as needed to make the HTML representation"""
        return zip(*[category.questions for category in self.board.categories])

    def get(self, identifier: str):
        """Returns the question object referred to by a specific identifier. Additionally ensures the remaining
        question counter is decremented, as required to play.

        Required Arguments:

        identifier (str) -- A three piece identifier that specifies the question to return
        """
        self.remaining_questions -= 1
        entry, category, question = identifier.split("_")

        if entry == "q":
            response = self.board.categories[int(category)].questions[int(question)]
            self.current_question = response.get_question()
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

    def __lshift__(self, other: str) -> bool:
        if other not in self:
            self.players[other] = {"score": 0, "wager": {"amount": 0, "answer": ""}}

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
        return [
            i[0]
            for i in sorted(self.players.items(), key=lambda k: k[1]["score"], **kwargs)
        ]

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
            value = game.current_question.value * (-1 + (2 * correct))

        else:
            player = self.wagerer
            value = self.players[player]["wager"]["amount"] * (-1 + (2 * correct))

        self.players[player]["score"] += value

        self.players[player]["wager"]["amount"] = 0
        self.wagerer = None


class Board(object):
    """Class to hold the Jeopardy game board. Contains methods to get categories and questions."""

    def __init__(self, segment: int, size: int):
        self.db: str = config.database
        self.size: int = size if segment < 3 else 1
        self.round: int = segment
        self.categories: list = list()

        self.get_questions()

    def get_questions(self) -> None:
        """Create a datastructure storing the categories and questions associated with each round of gameplay.
        This function should perform a number of steps to prevent the appearance of incomplete categories, or 
        external content.
        """
        conn = sqlite3.connect(self.db)
        t = conn.cursor()

        # Pull a list of all the show numbers in the question database, and randomly select one show for each category
        # of gameplay. As such, in game, each category will be representing a different actually show number.
        selected_shows = random.sample(
            sqlite_cleaned(t.execute("SELECT show FROM questions").fetchall()),
            self.size,
        )

        # For each aired show/episode, get a list containing all of the category titles. By design this should
        # only choose categories that are complete (i.e., have 5 questions in the database) and have no external
        # media (i.e., links/hrefs/images)
        for index, show in enumerate(selected_shows):
            categories = t.execute(
                "SELECT category FROM questions WHERE \
                segment=? AND show=? AND complete_category=? AND external_media=?",
                (self.round, show, True, False),
            ).fetchall()

            categories = sqlite_cleaned(categories)

            # Loop over the list of categories to generate a new dataset of questions for each. The while loop
            # will repeat in the event external media is still found, or an incomplete category is found.
            qs: list = list()
            while sum([q[8] for q in qs]) > 0 or sum([q[7] for q in qs]) < len(
                categories
            ):

                # Technically, this can error out, if all of the categories in the game are incomplete... However,
                # the included database should already include enough protection against this... 😬
                category = categories.pop(random.randrange(len(categories)))

                # Finally, fetch all of the questions associated with the specifically checked category and show
                qs = t.execute(
                    "SELECT * FROM questions WHERE segment=? AND show=? and category=?",
                    (self.round, show, category),
                ).fetchall()

            # If the while loop has been successfully broken out of, add those questions to the game storage.
            self.categories.append(Category(qs, index))

    def add_wagers(self) -> None:
        """Randomly assign the "Daily Double" to the correct number of questions per round."""
        doubles = itertools.product(
            range(len(self.categories)), range(len(self.categories[0].questions))
        )

        for daily_double in random.sample(list(doubles), [0, 1, 2, 0, 0][self.round]):
            if config.debug:
                daily_double = (0, 0)

            self.categories[daily_double[0]].questions[daily_double[1]].wager = True

    # def __contains__(self, item):
    #     if len(self.categories) == 0:
    #         return False
    #     else:
    #         return item[1] in [i.title() for i in self.categories]

    # def html_board(self):
    #     return zip(*[i.questions for i in self.categories])


class Category(object):
    """Class to hold one of the categories (ostensibly columns) on a Jeopardy game board."""

    def __init__(self, db_questions: list, index: int):
        self.category = db_questions[0][1]
        self.index = index
        self.questions: list = list()

        for question_index, question_info in enumerate(db_questions):
            self.add_question(
                question_info=question_info, question_index=question_index
            )

        self.questions.sort()

    def __str__(self):
        """Creates a string representation of the category, returning just the title"""
        return self.category

    def __repr__(self):
        """Duplicates `__str__`"""
        return str(self)

    def add_question(self, question_info: tuple, question_index: int):
        """Add a question to the category, making use of the `Question` class.

        Required Arguments:

        `question_info` (tuple) -- Details about the question (question, answer, value, etc.)
        `question_index` (int) -- The number of the question in terms of the game.
        """
        self.questions.append(
            Question(
                question_info=question_info,
                question_index=question_index,
                category_index=self.index,
            )
        )


class Question(object):
    """Class to hold a single question"""

    def __init__(self, question_info: tuple, question_index: int, category_index: int):
        self.category_index = category_index
        self.question_index = question_index
        self.shown = False

        self.wager = False

        self.question = question_info[3].strip("'")
        self.answer = question_info[4].strip("'")
        self.value = question_info[5]
        self.year = question_info[6]

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        """Creates a string representation of the question's value"""
        return str(self.value)

    def __repr__(self):
        """Duplicates `__str__`"""
        return str(self)

    def id(self):
        """Returns the unique identifier of the question"""
        return f"{self.category_index}_{self.question_index}"

    def get(self):
        """Gets the question, as done within the Jinja loading of the webpage"""
        self.shown = True

        return {
            "question": self.question,
            "answer": self.answer,
            "wager": self.wager,
        }

    def get_question(self):
        """Gets the question, as done within the Jinja loading of the webpage"""
        return self


def sqlite_cleaned(items: list) -> list:
    """A helper function to clean up data pulled from the sqlite database.

    - Required Arguments:

    `items` (list) -- A list with rows from a sqlite database
    """
    return list(set([item[0] for item in items]))
