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
        self.round = 2

        self.score = dict()
        self.buzzers = list()

        self.standing_question = None

        self.wagered_round = dict()

    def add_player(self, name: str):
        self.score[name] = 0

    def make_board(self):
        self.remaining_questions = self.size * 5
        self.remaining_questions = 1
        self.board = Board(database_name = self.db, segment = self.round, size = self.size)

    def reset(self, reset_score: bool, reset_players: bool):
        if reset_players:
            self.score = dict()

        elif reset_score:
            self.score = {player: 0 for player in self.score.keys()}

        else:
            return False

    def round_text(self, next_round: bool = False) -> str:
        if next_round:
            next_round = self.round + 1

        if (not next_round and self.round == 1) or (next_round == 1):
            return '{copyright}!'.format(copyright = self.copyright)

        elif (not next_round and self.round == 2) or (next_round == 2):
            return 'Double {copyright}!'.format(copyright = self.copyright)

        elif (not next_round and self.round == 3) or (next_round == 3):
            return 'Final {copyright}!'.format(copyright = self.copyright)

        elif (not next_round and self.round == 4):
            return 'Tiebreaker {copyright}!'.format(copyright = self.copyright)

        else:
            print(u'An error has occurred....')
            return False

    def next_round(self):
        self.round += 1
        self.make_board()

    def html_board(self) -> str:
        return zip(*[category.questions for category in self.board.categories])

    def get(self, identifier: str):
        self.remaining_questions -= 1
        entry, category, question = identifier.split(u'_')

        if entry == u'q':
            response = self.board.categories[int(category)].questions[int(question)]
            self.standing_question = response.get_question()
            return response.get()

        else: 
            print(u'An error has occurred....')
            return False

    def buzz(self, name: str):
        if name in self.score.keys():
            self.buzzers.append(name)



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
        category_list = [u'']

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

            dataset = [(0, 0, 0, 0, 0, 0, 0, 0, 1)]

            category = u''

            while sum([datum[8] for datum in dataset]) > 0 and category in category_list:
                category = random.choice(all_categories)
                
                dataset = t.execute(u'SELECT * FROM questions WHERE segment=? AND show=? and category=?',
                    (self.round, show, category)).fetchall()

            self.categories.append(Category(dataset, index))

        self.values = [question.value for question in self.categories[0].questions]

    def add_wagers(self):
        if self.round == 1:
            question = (random.randrange(self.size),random.randrange(5))

            self.categories[question[0]].questions[question[1]].wager = True

        elif self.round == 2:
            question_one = (random.randrange(self.size),random.randrange(5))
            question_two = (random.randrange(self.size),random.randrange(5))

            while question_one == question_two:
                question_two = (random.randrange(self.size),random.randrange(5))


            self.categories[question_one[0]].questions[question_one[1]].wager = True
            self.categories[question_two[0]].questions[question_two[1]].wager = True


    def html_board(self):
        return zip(*[i.questions for i in self.categories])

class Category(object):
    def __init__(self, db_questions: list, index: int):
        self.category = db_questions[0][1]
        self.index = index
        self.questions = list()

        for question_index, row in enumerate(db_questions):
            self.add_question(
                question_info = row,
                question_index = question_index)

        self.questions.sort()

    def __str__(self):
        return self.category

    def __repr__(self):
        return self.category

    def add_question(self, question_info: tuple, question_index: int):
        self.questions.append(
            Question(
                question_info = question_info, 
                question_index = question_index,
                category_index = self.index))


class Question(object):
    def __init__(self, question_info: tuple, question_index: int, category_index: int):
        self.category_index = category_index
        self.question_index = question_index
        self.shown = False

        self.wager = False

        self.question = question_info[3].strip(u'\'')
        self.answer = question_info[4].strip(u'\'')
        self.value = question_info[5]
        self.year = question_info[6]

    def __lt__(self, other):
        return self.value < other.value

    def __repr__(self):
        return str(self.value)

    def id(self):
        return u'{category}_{question}'.format(
            category = self.category_index,
            question = self.question_index)

    def get(self):
        self.shown = True

        return {u'question': self.question, u'answer': self.answer}

    def get_question(self):
        return self


def sqlite_cleaned(items: list) -> list:
    return list(set([item[0] for item in items]))

# board = Board(database_name = u'database.db', segment = 1)
# board.get_questions()

# game = Game(database_name = u'database.db')