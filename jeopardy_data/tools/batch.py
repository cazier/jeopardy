import tqdm

from . import scrape


def get_list_of_seasons() -> str:
    seasons = scrape.Webpage(resource=f"listseasons.php").get()

    results = scrape.get_seasons(page=seasons)

    return results


def get_list_of_games(season: str) -> str:
    games = scrape.Webpage(resource=f"showseason.php?season={season}").get()

    results = scrape.get_games(page=games)

    return results


def scrape_game(game_id: str) -> tuple:
    game = scrape.Webpage(resource=f"showgame.php?game_id={game_id}").get()

    results = scrape.get_board(page=game)

    return results


def scrape_multiple_games(game_ids: list, progress: bool = False) -> tuple:
    results, errors = list(), list()

    if progress:
        display = tqdm.tqdm

    else:
        display = lambda k: k

    for game in display(game_ids):
        try:
            data = scrape_game(game_id=game)

            results.append(data)

        except (scrape.ParsingError, scrape.NetworkError, scrape.NoItemsFoundError):
            errors.append(game)

    return results, errors


def scrape_season(season_id: str, progress: bool = False) -> tuple:
    game_ids = get_list_of_games(season=season_id)

    return scrape_multiple_games(game_ids=game_ids, progress=progress)

