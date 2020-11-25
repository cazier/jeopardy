import pathlib
import json
import os
import random

import pytest
import requests
from bs4 import BeautifulSoup

import jeopardy_data.scraping.scrape as scrape


@pytest.fixture
def PatchedRequests(monkeypatch):
    def localGet(uri, *args, **kwargs):
        file = uri.split("/")[-1].replace("?", "_")

        path = pathlib.Path(os.getcwd(), "tests/files/mock_get", file).absolute()

        if path.exists():
            status_code = 200

            with open(path, "r") as local_file:
                text = local_file.read()

        else:
            status_code = 404

            text = "<html><head></head><body>404 Page Not Found</body></html>"

        mock = type("PatchedRequests", (), {})()
        mock.status_code = status_code
        mock.text = text

        return mock

    monkeypatch.setattr(requests, "get", localGet)


@pytest.fixture
def TestFiles(PatchedRequests):
    scrape.DELAY = 0
    scrape.CACHE = True
    scrape.CACHE_PATH = pathlib.Path(os.getcwd(), "tests/files/cache/").absolute()


@pytest.fixture
def example_org(PatchedRequests):
    scrape.BASE_URL = "https://example.org"
    scrape.DELAY = 0

    return scrape.Webpage(resource="test")


def test_resource_id():
    assert type(scrape.resource_id("")) == str

    with pytest.raises(TypeError):
        scrape.resource_id(0)


def test_webpage_url_creation(example_org):
    assert example_org.url == "https://example.org/test"


def test_webpage_repr(example_org):
    assert str(example_org) == "https://example.org/test"


def test_storage(example_org):
    assert example_org.storage == pathlib.Path("", "test").absolute()


def test_get_download(example_org):
    success, bs = example_org.get()
    assert (success) & (bs.body.text == "Page Definitely Absolutely Found")


def test_get_download_404(example_org):
    page = scrape.Webpage(resource="404")

    success, message = page.get()
    assert (not success) & (message == {"message": "failed to receive webpage data"})


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

    success, message = page.get()

    assert message.text == "Page Loaded From Cache"


def test_get_seasons(TestFiles):
    page = scrape.Webpage(resource="listseasons.php")

    start = random.randint(1, 15)
    stop = random.randint(start + 1, 16)

    _, data = page.get()

    success, message = scrape.get_seasons(page=data, start=start, stop=stop, include_special=False)

    assert success
    assert len(message) == stop - start

    success, message = scrape.get_seasons(page=data, start=start, stop=stop, include_special=True)

    assert success
    assert len(message) == 3 + stop - start


def test_get_seasons_empty():
    page = BeautifulSoup('<html><head></head><body id="content">Empty Seasons</body></html>', "lxml")

    with pytest.raises(scrape.NoItemsFoundError):
        scrape.get_seasons(page=page, start=0, stop=1, include_special=False)


def test_get_seasons_parse_error():
    page = BeautifulSoup('<html><head></head><body>No `id="content"`</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_seasons(page=page, start=0, stop=1, include_special=True)


def test_get_seasons_start_stop():
    page = BeautifulSoup('<html><head></head><body id="content">Empty Seasons</body></html>', "lxml")

    with pytest.raises(SyntaxError):
        scrape.get_seasons(page=page, start=0, stop=0, include_special=True)
        scrape.get_seasons(page=page, start=1, stop=0, include_special=True)


def test_get_games(TestFiles):
    page = scrape.Webpage(resource="showseason.php?season=1")

    _, data = page.get()

    success, message = scrape.get_games(page=data)

    assert success
    assert len(message) == 8


def test_get_games_empty():
    page = BeautifulSoup('<html><head></head><body id="content">Empty Games</body></html>', "lxml")

    with pytest.raises(scrape.NoItemsFoundError):

        scrape.get_games(page=page)


def test_get_games_parse_error():
    page = BeautifulSoup('<html><head></head><body>No `id="content"`</body></html>', "lxml")

    with pytest.raises(scrape.ParsingError):
        scrape.get_games(page=page)


def test_pjs():
    result = scrape.pjs("toggle('', '', 'This is a string')")
    assert result.text == "This is a string"

    result = scrape.pjs("toggle('Only', 'This', 'Matters')")
    assert result.text == "Matters"

    result = scrape.pjs("toggle('', '', '&quot;HTML&quot; escapes are converted')")
    assert result.text == '"HTML" escapes are converted'

    with pytest.raises(scrape.ParsingError):
        result = scrape.pjs("console.log('Other code fails')")
