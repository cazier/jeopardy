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

        self.round = 2

        self.score: dict = dict()
        self.buzz_order: list = list()

        self.current_question = None

        if config.debug:
            self.add_player("Alex")
            self.add_player("Brad")
            self.add_player("Carl")

    def add_player(self, name: str):
        """Add a player to the game with a starting score of zero (0).

        Required Arguments:

        name (str) -- The player's name
        """
        self.score[name] = 0

    def make_board(self):
        """Create a game board.

        This will track the number of questions in each round, and runs the function `self.board.add_wagers()`
        to ensure the "Daily Doubles" are placed around the board.
        """
        self.remaining_questions = 1 if config.debug else self.size * 5

        self.board = Board(segment=self.round, size=self.size)

        self.wagered_round = dict()

        self.board.add_wagers()

    def reset(self, reset_score: bool, reset_players: bool):
        """Reset the game to play again!

        Required Arguments:

        `reset_score` (bool) -- Keep the players, but set score to zero. (Basically, rematch)
        `reset_players` (bool) -- Reset both players and score (Basically, a whole new game)
        """
        if reset_players:
            self.score = dict()
            self.round = 1

        elif reset_score:
            self.score = {player: 0 for player in self.score.keys()}
            self.round = 1

        else:
            return False

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
        if name in self.score.keys():
            self.buzz_order.append(name)


class Board(object):
    """Class to hold the Jeopardy game board. Contains methods to get categories and questions."""

    def __init__(self, segment: int, size: int):
        self.db: str = config.database
        self.size: int = size if segment < 3 else 1
        self.round: int = segment
        self.categories: list = list()

        self.get_questions()

    # def __contains__(self, item):
    #     if len(self.categories) == 0:
    #         return False
    #     else:
    #         return item[1] in [i.title() for i in self.categories]

    def get_questions(self) -> None:
        """Create a datastructure storing the categories and questions associated with each round of gameplay.
        This function should perform a number of steps to prevent the appearance of incomplete categories, or 
        external content.
        """
        conn = sqlite3.connect(self.db)
        t = conn.cursor()

        # Pull a list of all the show numbers in the question database, and randomly select one show for each category
        # of gameplay. As such, in game, each category will be representing a different actually show number.
        shows = t.execute("SELECT show FROM questions").fetchall()
        selected_shows = random.sample(sqlite_cleaned(shows), self.size)

        # For each aired show/episode, get a list containing all of the category titles. By design this should
        # only choose categories that are complete (i.e., have 5 questions in the database) and have no external
        # media (i.e., links/hrefs/images)
        for index, show in enumerate(selected_shows):
            categories = t.execute(
                "SELECT category FROM questions WHERE \
                segment=? AND show=? AND complete_category=? AND external_media=?",
                (self.round, show, True, False),
            ).fetchall()

            print(categories)
            categories = sqlite_cleaned(categories)
            print(categories)
            input()

            # Loop over the list of categories to generate a new dataset of questions for each. The while loop
            # will repeat in the event external media is still found, or an incomplete category is found.
            dataset: list = list()
            while sum([q[8] for q in dataset]) > 0 or sum([q[7] for q in dataset]) < 5:

                # Technically, this can error out, if all of the categories in the game are incomplete... However,
                # the included database should already include enough protection against this... 😬
                category = categories.pop(random.randrange(len(categories)))

                # Finally, fetch all of the questions associated with the specifically checked category and show
                dataset = t.execute(
                    "SELECT * FROM questions WHERE segment=? AND show=? and category=?",
                    (self.round, show, category),
                ).fetchall()

            # If the while loop has been successfully broken out of, add those questions to the game storage.
            self.categories.append(Category(dataset, index))

    def add_wagers(self) -> None:
        """Randomly assign the "Daily Double" to the correct number of questions per round."""
        doubles = list(itertools.product(range(self.size), range(6)))
        print(doubles)
        print(self.categories)
        input()

        for daily_double in random.sample(doubles, self.round):
            if config.debug:
                print(f"{'=' * 10}\n{daily_double}\n{'=' * 10}")

            self.categories[daily_double[0]].questions[daily_double[1]].wager = True

    # def html_board(self):
    #     return zip(*[i.questions for i in self.categories])


class Category(object):
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
        return self.category

    def __repr__(self):
        return self.category

    def add_question(self, question_info: tuple, question_index: int):
        self.questions.append(
            Question(
                question_info=question_info,
                question_index=question_index,
                category_index=self.index,
            )
        )


class Question(object):
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

    def __repr__(self):
        return str(self.value)

    def id(self):
        return "{category}_{question}".format(
            category=self.category_index, question=self.question_index
        )

    def get(self):
        self.shown = True

        return {
            "question": self.question,
            "answer": self.answer,
            "wager": self.wager,
        }

    def get_question(self):
        return self


def sqlite_cleaned(items: list) -> list:
    return list(set([item[0] for item in items]))


# board = Board(database_name = u'database.db', segment = 1)
# board.get_questions()

# game = Game(database_name = u'database.db')
