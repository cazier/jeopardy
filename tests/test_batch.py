import pytest


from jeopardy_data.tools import batch
from jeopardy_data import api


def test_get_list_of_seasons(PatchedRequests):
    results = batch.get_list_of_seasons()

    assert len(results) == 19


def test_get_list_of_games(PatchedRequests):
    results = batch.get_list_of_games(season=1)

    assert len(results) == 8


def test_scrape_game(PatchedRequests, complete_file):
    results = batch.scrape_game(game_id=1)

    assert results == complete_file


def test_scrape_multiple_games(PatchedRequests, complete_file, incomplete_file):
    results, errors = batch.scrape_multiple_games(game_ids=["1", "2"], progress=False)

    assert results == complete_file + incomplete_file
    assert errors == []

    results, errors = batch.scrape_multiple_games(game_ids=["1", "2", "3"], progress=True)

    assert results == complete_file + incomplete_file
    assert errors == ["3"]


def test_scrape_multiple_seasons(PatchedRequests, complete_file, incomplete_file):
    results, errors = batch.scrape_multiple_seasons(season_ids=["2"], progress=False)
    assert results == complete_file + incomplete_file


def test_add_database(emptyclient, complete_file):
    complete_file = complete_file[:20]
    results, repeats, errors = batch.add_database(items=complete_file, shortnames=False, progress=False)
    assert results == 20

    results, repeats, errors = batch.add_database(items=complete_file, shortnames=False, progress=False)
    assert repeats == 20

    items = [
        {
            "category": "TRAVEL",
            "value": 0,
            "question": "Visa",
            "external": False,
            "round": 2,
            "complete": True,
            "show": 1,
            "date": "1992-08-13",
        }
    ]

    results, repeats, errors = batch.add_database(items=items, shortnames=False, progress=False)
    assert errors != {}
    assert errors[0]["clue"] == items[0]
