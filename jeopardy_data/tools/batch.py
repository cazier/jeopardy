import tqdm

from . import scrape

try:
    from api import database

except ModuleNotFoundError:
    from jeopardy_data.api import database


def get_list_of_seasons() -> list:
    seasons = scrape.Webpage(resource=f"listseasons.php").get()

    results = scrape.get_seasons(page=seasons)

    return results


def get_list_of_games(season: str) -> list:
    games = scrape.Webpage(resource=f"showseason.php?season={season}").get()

    results = scrape.get_games(page=games)

    return results


def scrape_game(game_id: str) -> list:
    game = scrape.Webpage(resource=f"showgame.php?game_id={game_id}").get()

    results = scrape.get_board(page=game)

    return results


def scrape_multiple_games(game_ids: list, progress: bool) -> tuple:
    results, errors = list(), list()

    for game in display(progress=progress)(game_ids):
        try:
            data = scrape_game(game_id=game)

            results.extend(data)

        except (scrape.ParsingError, scrape.NetworkError, scrape.NoItemsFoundError):
            errors.append(game)

    return results, errors


def display(progress: bool):
    if progress:
        return tqdm.tqdm

    else:
        return lambda k: k


def scrape_season(season_id: str, progress: bool) -> tuple:
    game_ids = get_list_of_games(season=season_id)

    return scrape_multiple_games(game_ids=game_ids, progress=progress)


def add_database(items: list, progress: bool, shortnames: bool) -> tuple:
    results, repeats = 0, 0
    errors = list()

    for clue in display(progress=progress)(items):
        try:
            database.add(clue_data=clue, uses_shortnames=shortnames)
            results += 1

        except (database.MissingDataError, database.BadDataError) as e:
            errors.append({"message": e.message, "clue": clue})

        except database.SetAlreadyExistsError:
            repeats += 1

    return results, repeats, errors

