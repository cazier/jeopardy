import sqlite3
import random
from pprint import pprint

class Game(object):
    def __init__(self, database_name: str, players: int, size: int, copyright: str, room: str):
        self.db = database_name
        self.players = players
        self.size = size
        self.copyright = copyright
        self.room = room
        
        self.round = 1

        self.score = dict()

    def add_player(self, name: str):
        self.score[name] = 0

    def make_board(self):
        self.board = Board(database_name = self.db, segment = self.round, size = self.size)

    def reset(self, reset_score: bool, reset_players: bool):
        if reset_players:
            self.score = dict()

        elif reset_score:
            self.score = {player: 0 for player in self.score.keys()}

    def round_text(self) -> str:
        if self.round == 1:
            return '{copyright}!'.format(copyright = self.copyright)

        elif self.round == 2:
            return 'Double {copyright}!'.format(copyright = self.copyright)

        elif self.round == 3:
            return 'Final {copyright}!'.format(copyright = self.copyright)

        elif self.round == 4:
            return 'Tiebreaker {copyright}!'.format(copyright = self.copyright)

        else:
            print(u'An error has occurred....')
            return u'Oops...'

    def next_round(self):
        self.round += 1

    def html_board(self) -> str:
        return zip(*[category.questions for category in self.board.categories])


class Board(object):
    """Class to hold the Jeopardy game board. Contains methods to get categories and questions."""
    def __init__(self, database_name: str, segment: int, size: int):
        self.db = database_name
        self.size = size if segment < 3 else 1
        self.round = segment
        self.categories = list()

        self.get_questions()


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
        

        for index, show in enumerate(selected_shows):
            categories = t.execute(u'SELECT category FROM questions WHERE \
                segment=? AND show=? AND complete_category=? AND external_media=?',
                (self.round, show, True, False)).fetchall()

            all_categories = sqlite_cleaned(categories)
            print(u'=====================')
            print(all_categories)
            input()
            category = random.choice(all_categories)
            
            dataset = t.execute(u'SELECT * FROM questions WHERE segment=? AND show=? and category=?',
                (self.round, show, category)).fetchall()

            self.categories.append(Category(dataset, index))

        self.values = [question.value for question in self.categories[0].questions]


    def html_board(self):
        return zip(*[i.questions for i in self.categories])


class Category(object):
    def __init__(self, db_questions: list, index: int):
        self.category = db_questions[0][1]
        self.questions = list()

        for row in db_questions:
            self.add_question(row, index)

        self.questions.sort()

    def __str__(self):
        return self.category

    def __repr__(self):
        return self.category

    def add_question(self, question_info: tuple, index: int):
        self.questions.append(Question(question_info, index))


class Question(object):
    def __init__(self, question_info: tuple, index: int):
        self.index = index
        self.shown = False

        self.question = question_info[3].strip(u'\'')
        self.answer = question_info[4].strip(u'\'')
        self.value = question_info[5]
        self.year = question_info[6]

    def __lt__(self, other):
        return self.value < other.value

    def __repr__(self):
        return str(self.value)

    def id(self):
        return u'{category}_{value}'.format(
            category = self.index,
            value = self.value)

    def get(self):
        self.shown = True
        return {u'question': self.question, u'answer': self.answer}


def sqlite_cleaned(items: list) -> list:
    return list(set([item[0] for item in items]))

# board = Board(database_name = u'database.db', segment = 1)
# board.get_questions()

# game = Game(database_name = u'database.db')