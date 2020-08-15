import sqlite3
import json
import operator

ROUNDS = {u'Jeopardy!': 1, u'Double Jeopardy!': 2, u'Final Jeopardy!': 3, u'Tiebreaker': 4}
DB_NAME = u'data/database.db'
JSON_NAME = u'helpers/database/clues.json'

def format_row(data: dict) -> tuple:
    num = int(data[u'show_number'])
    question = data[u'question']
    answer = data[u'answer']

    if data[u'value'] == u'$0':
        value = 0
    else:
        value = int(data[u'value'].replace(u'$', u'').replace(u',', u''))

    segment = ROUNDS[data[u'round']]

    category = data[u'category']
    year = int(data[u'air_date'][:4])

    complete_category = data[u'complete_category']
    external_media = data[u'has_external_media']

    return (num, category, segment, answer, question, value, year, complete_category, external_media)

def create_table(database_name: str, question_set: str) -> None:
    with open(question_set, u'r') as data:
        pretty = json.load(data)

    dataset = [format_row(i) for i in pretty]
    dataset.sort(key=operator.itemgetter(0, 2, 1, 5))

    conn = sqlite3.connect(database_name)
    c = conn.cursor()

    c.execute('''CREATE TABLE show_data
              (show INT, category TEXT, segment INT, answer TEXT, question TEXT, value INT, year INT, complete_category BOOLEAN, external_media BOOLEAN)''')

    c.executemany(u'INSERT INTO show_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', dataset)

    conn.commit()
    conn.close()

create_table(DB_NAME, JSON_NAME)

