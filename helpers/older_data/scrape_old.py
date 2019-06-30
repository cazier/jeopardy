import requests
from bs4 import BeautifulSoup
import re
import sys
import time


DEBUG = u'='*20

games = list()

ROUNDS = {
    0: u'jeopardy_round',
    1: u'double_jeopardy_round',
    2: u'final_jeopardy_round',
    u'j': 200, u'd': 400,
    u'J': u'Jeopardy!', u'D': u'Double Jeopardy!', u'F': u'Final Jeopardy!', u'T': u'Tiebreaker'}
SHOW = re.compile(r'Show #(\d{1,6}) - (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})')
MONTHS = {
    u'January': u'01',
    u'February': u'02',
    u'March': u'03',
    u'April': u'04',
    u'May': u'05',
    u'June': u'06',
    u'July': u'07',
    u'August': u'08',
    u'September': u'09',
    u'October': u'10',
    u'November': u'11',
    u'December': u'12'}

def get_seasons():
    site = requests.get(u'http://www.j-archive.com/listseasons.php').text
    links = BeautifulSoup(site, u'lxml').find_all(u'a')

    response = [link.get(u'href') for link in links if u'showseason.php' in link.get(u'href')]

    return [u'{base}{link}'.format(base = u'http://www.j-archive.com/', link = link) for link in response][2:]

def get_games(url):
    site = requests.get(url).text
    links = BeautifulSoup(site, u'lxml').find_all(u'a')

    response = [link.get(u'href') for link in links if u'showgame.php' in link.get(u'href')]

    return [u'{link}'.format(link = link) for link in response]

# def good_game_check(site):
#     check_for_blanks = [i.text.strip() for i in site.find_all(u'td', class_=u'clue')]
#     for check in check_for_blanks:
#         if len(check) == 0:
#             return False

#     return True

# def category(soups):
#     categories = soups.find_all(u'td', class_=u'category')

#     return [i.text.strip() for i in categories]

# def value(element, segment):
#     if segment == u'jeopardy':
#         return int(element[17]) * 200 * 1

#     elif segment == u'double':
#         return int(element[18]) * 200 * 2

# def cat_load(element, segment, categories):
#     if segment == u'jeopardy':
#         return categories[int(element[15]) - 1]

#     elif segment == u'double':
#         return categories[int(element[16]) - 1]

# def j_question(site_element, categories):
#     element = site_element.find_all(u'div')[0]

#     return {
#         u'answer': answer(element.attrs[u'onmouseout'], 42),
#         u'question': clue(element.attrs[u'onmouseover']),
#         u'value': value(element.attrs[u'onmouseout'], u'jeopardy'),
#         u'category': cat_load(element.attrs[u'onmouseout'], u'jeopardy', categories),
#         u'round': u'Jeopardy!',
#         }

# def d_question(site_element, categories):
#     element = site_element.find_all(u'div')[0]

#     return {
#         u'answer': answer(element.attrs[u'onmouseout'], 44),
#         u'question': clue(element.attrs[u'onmouseover']),
#         u'value': value(element.attrs[u'onmouseout'], u'double'),
#         u'category': cat_load(element.attrs[u'onmouseout'], u'double', categories),
#         u'round': u'Double Jeopardy!',
#         }

# def f_question(site_element):
#     element = site_element.find_all(u'div')[0]

#     return {
#         u'answer': answer(element.attrs[u'onmouseout'], 36),
#         u'question': clue(element.attrs[u'onmouseover']),
#         u'value': u'FJ',
#         u'category': site_element.find_all(u'td', class_=u'category_name')[0].text.strip(),
#         u'round': u'Final Jeopardy!',
#         }

# def get_date_and_show(site):
#     SHOW = re.compile(r'Show #(\d{1,6}) - (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})')

#     info = SHOW.match(site.find_all(u'h1')[0].text)

#     return (info.group(1), u'{year}-{month}-{day}'.format(
#         year = info.group(4),
#         month = MONTHS[info.group(2)],
#         day = str(info.group(3)).zfill(2)))

# def pull_clues(site, element):
#     show_date = get_date_and_show(site)
#     grid = site.find(id=element)
#     cats = category(grid)

#     game = grid.find_all(u'td', class_=u'clue')

#     clues = list()

#     if element == u'final_jeopardy_round':
#         parts = f_question(grid)
#         parts[u'show_number'] = show_date[0]
#         parts[u'air_date'] = show_date[1]
#         clues.append(parts)

#     else:
#         for thing in game:
#             if element == u'jeopardy_round':
#                 parts = j_question(thing, cats)
#             elif element == u'double_jeopardy_round':
#                 parts = d_question(thing, cats)

#             parts[u'show_number'] = show_date[0]
#             parts[u'air_date'] = show_date[1]

#             clues.append(parts)



#     return clues

# def better_clues(soup):
#     clues = [clue for clue in soup.find_all(u'td', class_=u'clue') if len(clue.find_all(u'table')) > 0]

#     for clue in clues:
#         div = clue.find_all(u'div')[0]

#         responses = {
#             u'question': get_question(div),
#             u'answer': get_answer(div)
#         }

#         print(responses)

#         sys.exit()


#     print(len(clues))

# def better_categories(soup):
    categories = soup.find_all(u'td', class_ = u'category_name')
    responses = {
            u'J_1': categories[0].text.strip(),
            u'J_2': categories[1].text.strip(),
            u'J_3': categories[2].text.strip(),
            u'J_4': categories[3].text.strip(),
            u'J_5': categories[4].text.strip(),
            u'J_6': categories[5].text.strip(),
            u'DJ_1': categories[6].text.strip(),
            u'DJ_2': categories[7].text.strip(),
            u'DJ_3': categories[8].text.strip(),
            u'DJ_4': categories[9].text.strip(),
            u'DJ_5': categories[10].text.strip(),
            u'DJ_6': categories[11].text.strip(),
            u'FJ': categories[12].text.strip(),
            }

    if len(categories) == 14:
        responses[u'TB'] = categories[13].text.strip()

    return responses


# seasons = get_seasons()


# for season in seasons:
#     games += get_games(season)
# print(games)
# print(len(games))
# sys.exit()
# clues = list()

# games = [u'http://www.j-archive.com/showgame.php?game_id=2172']

class Game():
    def __init__(self, soup):
        self.site = soup

        self.questions = list()

        self.category_sanity_check()

        self.get_game_info()

        self.get_categories()
        self.get_questions()

        self.check_category_completeness()

    def category_sanity_check(self):
        if (len(self.site.find(id=ROUNDS[0]).find_all(u'td', class_ = u'category_name')) != 6) or \
            (len(self.site.find(id=ROUNDS[1]).find_all(u'td', class_ = u'category_name')) != 6):
            print(u'Incorrect number of categories!')
            import sys
            sys.exit()

    def get_game_info(self):
        h1 = self.site.find(id=u'game_title').text
        info = SHOW.match(h1)

        self.number = info.group(1)

        self.date = u'{year}-{month}-{day}'.format(
            year = info.group(4),
            month = MONTHS[info.group(2)],
            day = str(info.group(3)).zfill(2))

    def get_categories(self):
        category_elements = self.site.find_all(u'td', class_ = u'category_name')
        self.categories = {
                u'J_1': category_elements[0].text.strip(),
                u'J_2': category_elements[1].text.strip(),
                u'J_3': category_elements[2].text.strip(),
                u'J_4': category_elements[3].text.strip(),
                u'J_5': category_elements[4].text.strip(),
                u'J_6': category_elements[5].text.strip(),
                u'DJ_1': category_elements[6].text.strip(),
                u'DJ_2': category_elements[7].text.strip(),
                u'DJ_3': category_elements[8].text.strip(),
                u'DJ_4': category_elements[9].text.strip(),
                u'DJ_5': category_elements[10].text.strip(),
                u'DJ_6': category_elements[11].text.strip(),
                u'FJ': category_elements[12].text.strip(),
                }

        if len(category_elements) == 14:
            self.categories[u'TB'] = category_elements[13].text.strip()

    def get_questions(self):
        clues = [clue for clue in self.site.find_all(u'td', class_=u'clue') if len(clue.find_all(u'table')) > 0]

        for clue in clues:
            if clue.parent.parent.parent.attrs[u'id'] != ROUNDS[2]:
                specifier = get_specifier(clue)
                div = clue.find_all(u'div')[0]

            else:
                div = clue.parent.parent.find_all(u'div')[0]
                specifier = {u'category': div.attrs[u'onclick'][18:20], u'value': 0}

            response = {
                u'category': string_clean(self.categories[specifier[u'category']]),
                u'air_date': self.date,
                u'question': string_clean(get_question(div)),
                u'value': u'${value}'.format(value = specifier[u'value']),
                u'answer': string_clean(get_answer(div)),
                u'round': ROUNDS[specifier[u'category'][0]],
                u'show_number': self.number,
                u'has_external_media': check_for_external(clue)
            }
            self.questions.append(response)

    def check_category_completeness(self):
        for question in self.questions:
            if (len([q for q in self.questions if q[u'category'] == question[u'category']]) == 5) and (
                (question[u'round'] == u'Jeopardy!') or (question[u'round'] == u'Double Jeopardy!')):
                question[u'complete_category'] = True

            elif (question[u'round'] == u'Final Jeopardy!') or (question[u'round'] == u'Tiebreaker'):
                question[u'complete_category'] = u'N/A'

            else:
                question[u'complete_category'] = False


def get_question(element):
    element = element.attrs[u'onmouseout']

    if element[13].lower() == u'd':
        start = 44

    elif element[13].lower() == u'j':
        start = 42

    elif (element[13].lower() == u't') or (element[13].lower() == u'f'):
        start = 36

    return element[start: -2]

def get_answer(element):
    element = element.attrs[u'onmouseover']
    return BeautifulSoup(element, u'lxml').find(u'em').text

def get_specifier(element):
    element = element.find_all(u'td', class_=u'clue_text')[0]
    element = element.attrs[u'id']
    return {u'category': element[5:-2], u'value': 200 * int(element[-1:]) * len(element[5:-4])}

def string_clean(element):
    return element.replace(u'\\\'', u'\'')

def check_for_external(element):
    return len(element.find_all(class_=u'clue_text')[0].find_all(u'a')) != 0


with open(u'missing_squares.html', 'r') as html_file:
# with open(u'tiebreaker.html', 'r') as html_file:
    # site = BeautifulSoup(requests.get(u'http://www.j-archive.com/showgame.php?game_id=2172').content, u'lxml')
    site = BeautifulSoup(html_file.read(), u'lxml')
    print(html_file.read())


a = Game(site)
from pprint import pprint

if __name__ == u'__main__':
	print(u'hello')