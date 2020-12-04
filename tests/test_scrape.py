import pathlib
import json
import os
import operator

import pytest
from bs4 import BeautifulSoup

from jeopardy_data.tools import scrape


@pytest.fixture
def TestFiles(PatchedRequests):
    scrape.CACHE = True
    scrape.CACHE_PATH = pathlib.Path(os.getcwd(), "tests/files/cache/").absolute()


@pytest.fixture
def example_org(PatchedRequests):
    scrape.BASE_URL = "https://example.org"

    return scrape.Webpage(resource="test")


def test_pjs():
    a, b = scrape.pjs("toggle('', '', 'This is a string')")
    assert (a.text == "") & (b.text == "This is a string")

    results = scrape.pjs("toggle('True', 'False', 'True')")
    assert all(i.text == "True" for i in results)

    _, result = scrape.pjs("toggle('', '', '&quot;HTML&quot; escapes are converted')")
    assert result.text == '"HTML" escapes are converted'

    with pytest.raises(scrape.ParsingError, match=r".*javascript.*failed to parse.*"):
        scrape.pjs("console.log('Javascript with less than three arguments fails')")

    with pytest.raises(scrape.NoInputSuppliedError, match=r".*javascript.*"):
        scrape.pjs("")  # As do empty strings


def test_resource_id():
    assert type(scrape.resource_id("")) == str

    with pytest.raises(TypeError):
        scrape.resource_id(0)


def test_generate_headers():
    assert ["0_0", "0_1", "0_2", "0_3"] == scrape.generate_headers(4)

    with pytest.raises(scrape.ParsingError):
        scrape.generate_headers(15)


def test_webpage_url_creation(example_org):
    assert example_org.url == "https://example.org/test"


def test_webpage_repr(example_org):
    assert str(example_org) == "https://example.org/test"


def test_storage(example_org):
    assert example_org.storage == pathlib.Path("", "test").absolute()


def test_get_download(example_org):
    bs = example_org.get()
    assert bs.body.text == "Page Definitely Absolutely Found"


def test_get_download_404(example_org):
    with pytest.raises(scrape.NetworkError):
        page = scrape.Webpage(resource="404").get()


def test_empty_resource():
    with pytest.raises(ValueError):
        page = scrape.Webpage(resource="")


def test_trailing_slash():
    scrape.BASE_URL = "https://example.org"
    soup_without = scrape.Webpage(resource="test")

    scrape.BASE_URL = "https://example.org/"
    soup_with = scrape.Webpage(resource="test")

    assert soup_without.url == soup_with.url


def test_cache_save(TestFiles, empty_cache_after_test):
    page = scrape.Webpage(resource="test")

    assert not pathlib.Path(scrape.CACHE_PATH, "test").exists()
    page.get()
    assert pathlib.Path(scrape.CACHE_PATH, "test").exists()


def test_cache_load(TestFiles, empty_cache_after_test):
    page = scrape.Webpage(resource="test")

    assert not pathlib.Path(scrape.CACHE_PATH, "test").exists()
    page.get()
    assert pathlib.Path(scrape.CACHE_PATH, "test").exists()

    with open(pathlib.Path(scrape.CACHE_PATH, "test"), "w") as test_file:
        test_file.write("<html><head></head><body>Page Loaded From Cache</body></html>")

    message = page.get()

    assert message.text == "Page Loaded From Cache"


def test_get_seasons(TestFiles):
    page = scrape.Webpage(resource="listseasons.php")

    data = page.get()

    message = scrape.get_seasons(page=data)

    assert len(message) == 19


def test_empty_pages():
    page = BeautifulSoup('<html><head></head><body id="content">Empty Page</body></html>', "lxml")

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_seasons(page=page)

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_games(page=page)

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_clues(page=page)


def test_parse_error_pages():
    page = BeautifulSoup('<html><head></head><body>No `id="content"`</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_seasons(page=page)

    with pytest.raises(scrape.ParsingError):
        scrape.get_games(page=page)


def test_get_seasons_start_stop():
    page = BeautifulSoup('<html><head></head><body id="content">Empty Seasons</body></html>', "lxml")

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_seasons(page=page)


def test_get_games(TestFiles):
    page = scrape.Webpage(resource="showseason.php?season=1")

    data = page.get()

    message = scrape.get_games(page=data)

    assert len(message) == 8


def test_get_clue_data():
    data = BeautifulSoup(
        """<div onmouseout="toggle('clue_J_1_1', 'clue_J_1_1_stuck', 'A')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')">""",
        "lxml",
    )

    expected_results = {
        "category": 0,
        "value": 0,
        "question": "B",
        "answer": BeautifulSoup("A", "lxml"),
        "external": False,
        "round": 0,
    }

    results = scrape.get_clue_data(clue=data)

    assert results == expected_results

    data = BeautifulSoup(
        """<div onmouseout="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;a href=&quot;/&quot;&gt;A&lt;/a&gt;')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')">""",
        "lxml",
    )

    expected_results = {
        "category": 0,
        "value": 0,
        "question": "B",
        "answer": BeautifulSoup('<a href="/">A</a>', "lxml"),
        "external": True,
        "round": 0,
    }

    results = scrape.get_clue_data(clue=data)

    assert results == expected_results

    data = BeautifulSoup(
        """<div onmouseout="toggle('clue_DJ_1_1', 'clue_DJ_1_1_stuck', '&lt;a href=&quot;/&quot;&gt;A&lt;/a&gt;')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')">""",
        "lxml",
    )

    expected_results = {
        "category": 0,
        "value": 0,
        "question": "B",
        "answer": BeautifulSoup('<a href="/">A</a>', "lxml"),
        "external": True,
        "round": 1,
    }

    results = scrape.get_clue_data(clue=data)

    assert results == expected_results

    data = BeautifulSoup(
        """<div onmouseover="toggle('clue_FJ', 'clue_FJ_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')" onmouseout="toggle('clue_FJ', 'clue_FJ_stuck', 'A')">""",
        "lxml",
    )

    expected_results = {
        "category": 0,
        "value": 0,
        "question": "B",
        "answer": BeautifulSoup("A", "lxml"),
        "external": False,
        "round": 2,
    }

    results = scrape.get_clue_data(clue=data)

    assert results == expected_results


def test_get_clue_data_failures():
    data = BeautifulSoup("", "lxml")

    with pytest.raises(scrape.NoInputSuppliedError):
        scrape.get_clue_data(clue=data)

    data = BeautifulSoup(  # CAN'T CONVERT v LETTER "P" TO AN INTEGER
        """<div onmouseout="toggle('clue_J_P_1', 'clue_J_1_1_stuck', 'A')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')">""",
        "lxml",
    )

    with pytest.raises(scrape.ParsingError, match=r".*was malformed.*"):
        scrape.get_clue_data(clue=data)

    data = BeautifulSoup(
        """<div onmouseout="toggle('clue_J_1_1', 'clue_J_1_1_stuck', 'A')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', 'B')">""",
        "lxml",
    )

    with pytest.raises(scrape.ParsingError, match=r".*unable to be parsed.*"):
        scrape.get_clue_data(clue=data)

    data = BeautifulSoup(
        """<div onmouseout="toggle('clue_P_1_1', 'clue_J_1_1_stuck', 'A')" onmouseover="toggle('clue_J_1_1', 'clue_J_1_1_stuck', '&lt;em class=&quot;correct_response&quot;&gt;B&lt;/em&gt;')">""",
        "lxml",
    )

    with pytest.raises(scrape.ParsingError, match=r".*didn't match.*"):
        scrape.get_clue_data(clue=data)


def test_get_clues(PatchedRequests):
    game = scrape.Webpage(resource="showgame.php?game_id=1").get()

    results = scrape.get_clues(page=game)

    assert len(results) == 61


def test_get_game_title(PatchedRequests, complete_file):
    game = scrape.Webpage(resource="showgame.php?game_id=1").get()

    show, date = scrape.get_game_title(page=game)
    values = (complete_file[0]["show"], complete_file[0]["date"])

    assert (show, date) == values

    page = BeautifulSoup("<html><head></head><div>Missing ID</body></html>", "lxml")

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_game_title(page=page)

    page = BeautifulSoup('<html><head></head><div id="game_title">No matches</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_game_title(page=page)

    page = BeautifulSoup('<html><head></head><div id="game_title">Show #1 - Bad Date</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_game_title(page=page)


def test_get_categories(PatchedRequests, complete_file):
    game = scrape.Webpage(resource="showgame.php?game_id=1").get()

    results = scrape.get_categories(page=game)

    values = {set["category"] for set in complete_file}

    assert len(results.items()) == 13
    assert set(results.values()) == values

    page = BeautifulSoup("<html><head></head><td>Missing class</body></html>", "lxml")

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_categories(page=page)

    page = BeautifulSoup('<html><head></head><td class="category_name">DOGS</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_categories(page=page)


def test_get_board(PatchedRequests, complete_file, incomplete_file):
    game = scrape.Webpage(resource="showgame.php?game_id=1").get()
    results = scrape.get_board(page=game)

    results = sorted(results, key=operator.itemgetter("round", "category", "value"))
    complete_file = sorted(complete_file, key=operator.itemgetter("round", "category", "value"))

    assert results == complete_file

    game = scrape.Webpage(resource="showgame.php?game_id=2").get()
    results = scrape.get_board(page=game)

    game = scrape.Webpage(resource="showgame.php?game_id=2").get()
    results = scrape.get_board(page=game)

    results = sorted(results, key=operator.itemgetter("round", "category", "value"))
    incomplete_file = sorted(incomplete_file, key=operator.itemgetter("round", "category", "value"))

    assert results == incomplete_file


def test_get_external_media():
    scrape.EXTERNAL_LINKS = list()
    scrape.BASE_URL = "http://example.org"

    item = {
        "show": 1,
        "round": 0,
        "value": 0,
        "answer": BeautifulSoup('<a href="/media/1992-08-13_J_1.jpg">A</a>', "lxml"),
    }

    scrape.get_external_media(item=item, category=0)

    assert scrape.EXTERNAL_LINKS == [("00001_0_0_0a", "http://example.org/media/1992-08-13_J_1.jpg")]
    scrape.EXTERNAL_LINKS = list()

    item = {
        "show": 1,
        "round": 0,
        "value": 0,
        "answer": BeautifulSoup('<a href="http://example.org/media/1992-08-13_J_1.jpg">A</a>', "lxml"),
    }

    scrape.get_external_media(item=item, category=0)

    assert scrape.EXTERNAL_LINKS == [("00001_0_0_0a", "http://example.org/media/1992-08-13_J_1.jpg")]
    scrape.EXTERNAL_LINKS = list()

    item = {
        "show": 1,
        "round": 0,
        "value": 0,
        "answer": BeautifulSoup(
            '<a href="/media/1992-08-13_J_1.jpg">A</a><a href="/media/1992-08-13_J_2.jpg">B</a>', "lxml"
        ),
    }

    scrape.get_external_media(item=item, category=0)

    assert scrape.EXTERNAL_LINKS == [
        ("00001_0_0_0a", "http://example.org/media/1992-08-13_J_1.jpg"),
        ("00001_0_0_0b", "http://example.org/media/1992-08-13_J_2.jpg"),
    ]
    scrape.EXTERNAL_LINKS = list()

    item = {
        "show": 1,
        "round": 0,
        "value": 0,
        "answer": BeautifulSoup('<a href="">A</a>', "lxml"),
    }

    with pytest.raises(scrape.ParsingError, match=".*has no url"):
        scrape.get_external_media(item=item, category=0)

