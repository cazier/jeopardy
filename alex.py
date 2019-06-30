import sqlite3
import random
from pprint import pprint

class Game(object):
    def __init__(self, database_name: str, players: int, size: int):
        self.db = database_name
        self.players = players
        self.round = 1
        self.size = size

        self.score = dict()

    def add_player(self, name: str):
        self.score[name] = 0

    def make_board(self):
        self.board = Board(database_name = self.db, segment = self.round, size = self.size)

        self.board.get_questions()

    def reset(self, reset_score: bool, reset_players: bool):
        if reset_players:
            self.score = dict()

        elif reset_score:
            self.score = {player: 0 for player in self.score.keys()}

    def table(self) -> list:
        content = list()
        for category in self.board.categories:
            category_questions = list()
            for question in category.questions:
                print(type(question))

class Board(object):
    """Class to hold the Jeopardy game board. Contains methods to get categories and questions."""
    def __init__(self, database_name: str, segment: int, size: int):
        self.db = database_name
        self.size = size
        self.round = segment
        self.categories = list()

    def __contains__(self, item):
        if len(self.categories) == 0:
            return False
        else:
            return item[1] in [i.title() for i in self.categories]

    def get_questions(self) -> list:
        questions = list()
        categories = list()

        conn = sqlite3.connect(self.db)
        t = conn.cursor()

        shows = t.execute(u'SELECT show FROM questions').fetchall()
        all_shows = sqlite_cleaned(shows)

        selected_shows = random.sample(all_shows, self.size)
        

        for show in selected_shows:
            categories = t.execute(u'SELECT category FROM questions WHERE \
                segment=? AND show=? AND complete_category=? AND external_media=?',
                (self.round, show, True, False)).fetchall()

            all_categories = sqlite_cleaned(categories)
            category = random.choice(all_categories)
            
            dataset = t.execute(u'SELECT * FROM questions WHERE segment=? AND show=? and category=?',
                (self.round, show, category)).fetchall()

            self.categories.append(Category(dataset))

        self.values = list(self.categories[0].questions.keys())

    def get_categories(self):
        return [name.category for name in self.categories]

    def get_question(self, element: str) -> dict:
        category = element.split(u'_')[0]
        value = element.split(u'_')[1]

        return self.categories[int(category)].questions[int(value)].get()

    def true(self, element: str) -> bool:
        category = element.split(u'_')[0]
        print(category, type(category))
        value = element.split(u'_')[1]
        print(value, type(value))

        return self.categories[int(category)].questions[int(value)].shown        

class Category(object):
    def __init__(self, db_questions: list):
        self.category = db_questions[0][1]
        self.questions = dict()

        for row in db_questions:
            self.add_question(row)

    def __str__(self):
        return self.category

    def __repr__(self):
        return self.category

    def add_question(self, question_info: tuple):
        self.questions[question_info[5]] = Question(question_info)


class Question(object):
    def __init__(self, question_info: tuple):
        self.question = question_info[3].strip(u'\'')
        self.answer = question_info[4].strip(u'\'')
        self.year = question_info[6]
        self.shown = False

    def get(self):
        self.shown = True
        return {u'question': self.question, u'answer': self.answer}


def sqlite_cleaned(items: list) -> list:
    return list(set([item[0] for item in items]))

# board = Board(database_name = u'database.db', segment = 1)
# board.get_questions()

# game = Game(database_name = u'database.db')