import requests
from bs4 import BeautifulSoup

import re
import sys
import json
import time


DEBUG = u"=" * 20

ROUNDS = {
    0: u"jeopardy_round",
    1: u"double_jeopardy_round",
    2: u"final_jeopardy_round",
    u"j": 200,
    u"d": 400,
    u"J": u"Jeopardy!",
    u"D": u"Double Jeopardy!",
    u"F": u"Final Jeopardy!",
    u"T": u"Tiebreaker",
}
SHOW = re.compile(
    r".*#(\d{1,6}) - (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})"
)
MONTHS = {
    u"January": u"01",
    u"February": u"02",
    u"March": u"03",
    u"April": u"04",
    u"May": u"05",
    u"June": u"06",
    u"July": u"07",
    u"August": u"08",
    u"September": u"09",
    u"October": u"10",
    u"November": u"11",
    u"December": u"12",
}

IGNORE_SEASONS = [u"http://www.j-archive.com/showseason.php?season=trebekpilots"]


def get_seasons():
    site = requests.get(u"http://www.j-archive.com/listseasons.php").text
    links = BeautifulSoup(site, u"lxml").find_all(u"a")

    response = [link.get(u"href") for link in links if u"showseason.php" in link.get(u"href")]

    seasons = [u"{base}{link}".format(base=u"http://www.j-archive.com/", link=link) for link in response][2:]

    return [season for season in seasons if season not in IGNORE_SEASONS]


def get_games(url):
    site = requests.get(url).text
    links = BeautifulSoup(site, u"lxml").find_all(u"a")

    response = [link.get(u"href") for link in links if u"showgame.php" in link.get(u"href")]

    return [u"{link}".format(link=link) for link in response]


def get_question(element):
    element = element.attrs[u"onmouseout"]

    if element[13].lower() == u"d":
        start = 44

    elif element[13].lower() == u"j":
        start = 42

    elif (element[13].lower() == u"t") or (element[13].lower() == u"f"):
        start = 36

    return element[start:-2]


def get_answer(element):
    element = element.attrs[u"onmouseover"]
    return BeautifulSoup(element, u"lxml").find(u"em").text


def get_specifier(element):
    element = element.find_all(u"td", class_=u"clue_text")[0]
    element = element.attrs[u"id"]
    return {u"category": element[5:-2], u"value": 200 * int(element[-1:]) * len(element[5:-4])}


def string_clean(element):
    return element.replace(u"\\'", u"'").replace(u"<br />", u"\n")


def check_for_external(element):
    return len(element.find_all(class_=u"clue_text")[0].find_all(u"a")) != 0


class Game:
    def __init__(self, soup):
        self.site = soup

        self.questions = list()

        self.category_sanity_check()

        self.get_game_info()

        self.get_categories()
        self.get_questions()

        self.check_category_completeness()

    def category_sanity_check(self):
        if (len(self.site.find(id=ROUNDS[0]).find_all(u"td", class_=u"category_name")) != 6) or (
            len(self.site.find(id=ROUNDS[1]).find_all(u"td", class_=u"category_name")) != 6
        ):
            print(u"Incorrect number of categories!")
            import sys

            sys.exit()

    def get_game_info(self):
        h1 = self.site.find(id=u"game_title").text
        info = SHOW.match(h1)

        self.number = info.group(1)

        self.date = u"{year}-{month}-{day}".format(
            year=info.group(4), month=MONTHS[info.group(2)], day=str(info.group(3)).zfill(2)
        )

    def get_categories(self):
        category_elements = self.site.find_all(u"td", class_=u"category_name")
        self.categories = {
            u"J_1": category_elements[0].text.strip(),
            u"J_2": category_elements[1].text.strip(),
            u"J_3": category_elements[2].text.strip(),
            u"J_4": category_elements[3].text.strip(),
            u"J_5": category_elements[4].text.strip(),
            u"J_6": category_elements[5].text.strip(),
            u"DJ_1": category_elements[6].text.strip(),
            u"DJ_2": category_elements[7].text.strip(),
            u"DJ_3": category_elements[8].text.strip(),
            u"DJ_4": category_elements[9].text.strip(),
            u"DJ_5": category_elements[10].text.strip(),
            u"DJ_6": category_elements[11].text.strip(),
            u"FJ": category_elements[12].text.strip(),
        }

        if len(category_elements) == 14:
            self.categories[u"TB"] = category_elements[13].text.strip()

    def get_questions(self):
        clues = [clue for clue in self.site.find_all(u"td", class_=u"clue") if len(clue.find_all(u"table")) > 0]

        for clue in clues:
            if clue.parent.parent.parent.attrs[u"id"] != ROUNDS[2]:
                specifier = get_specifier(clue)
                div = clue.find_all(u"div")[0]

            else:
                div = clue.parent.parent.find_all(u"div")[0]
                specifier = {u"category": div.attrs[u"onclick"][18:20], u"value": 0}

            response = {
                u"category": string_clean(self.categories[specifier[u"category"]]),
                u"air_date": self.date,
                u"question": string_clean(get_question(div)),
                u"value": u"${value}".format(value=specifier[u"value"]),
                u"answer": string_clean(get_answer(div)),
                u"round": ROUNDS[specifier[u"category"][0]],
                u"show_number": self.number,
                u"has_external_media": check_for_external(clue),
            }
            self.questions.append(response)

    def check_category_completeness(self):
        for question in self.questions:
            if (len([q for q in self.questions if q[u"category"] == question[u"category"]]) == 5) and (
                (question[u"round"] == u"Jeopardy!") or (question[u"round"] == u"Double Jeopardy!")
            ):
                question[u"complete_category"] = True

            elif (question[u"round"] == u"Final Jeopardy!") or (question[u"round"] == u"Tiebreaker"):
                question[u"complete_category"] = u"True"

            else:
                question[u"complete_category"] = False


def save_and_quit(clues, seasons, games, completed_games, errored_games):
    games = [game for game in games if game not in completed_games]
    if len(clues) != 0:
        with open(u"clues.json", u"w") as json_file:
            json.dump(clues, json_file, indent=True)

    with open(u"games.json", u"w") as json_file:
        json.dump(
            {
                u"completed_games": completed_games,
                u"pending_games": games,
                u"seasons": seasons,
                u"errored_games": errored_games,
            },
            json_file,
            indent=True,
        )


if __name__ == u"__main__":
    seasons = list()
    games = list()
    clues = list()
    pulled_games = list()
    errored_games = list()

    print(u"Getting seasons")
    if len(seasons) == 0:
        seasons = get_seasons()

    update_games = input(u"Do you want to update the list of games? (yN) ").lower()
    if update_games.lower() == u"y":
        print(u"Getting games")
        if len(games) == 0:
            for season in seasons:
                games += get_games(season)

    else:
        with open(u"games.json", "r") as json_file:
            a = json.load(json_file)

        games = a[u"pending_games"]
        completed_games = a[u"completed_games"]
        errored_games = a[u"errored_games"]

    try:

        for url in games:
            print(
                u"({completed}/{remaining}) Getting game id: {url}".format(
                    completed=str(len(pulled_games)).zfill(4), remaining=str(len(games)).zfill(4), url=url
                )
            )
            try:
                if url not in pulled_games:
                    response = Game(BeautifulSoup(requests.get(url).content, u"lxml")).questions

                    if len(response) > 10:
                        clues += response
                        pulled_games.append(url)

                    else:
                        print(u"An error occured with {url}".format(url=url))

                else:
                    pass

            except:
                print(u"An error occured with {url}".format(url=url))
                continuity = input(
                    u"Would you like to (s)ave the existing files, (a)dd the link to an 'error' list, or (q)uit without doing anything? "
                ).lower()

                if continuity == u"a":
                    errored_games.append(url)

                elif continuity == u"s":
                    save_and_quit(clues, seasons, games, pulled_games, errored_games)

                elif continuity == u"q":
                    sys.exit()

                else:
                    errored_games.append(url)

            time.sleep(0.5)

    except KeyboardInterrupt:
        save_and_quit(clues, seasons, games, pulled_games, errored_games)

    save_and_quit(clues, seasons, games, pulled_games, errored_games)
