import pathlib
import json
import os

import pytest
import requests

import jeopardy_data.scraping.scrape as scrape


@pytest.fixture
def PatchedRequests(monkeypatch):
    standard = requests.get

    def localGet(uri, *args, **kwargs):
        import time
        file = uri.split("/")[-1]

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
    
    monkeypatch.setattr(requests, 'get', localGet)

@pytest.fixture
def example_org(PatchedRequests):
    scrape.BASE_URL = "https://example.org"
    scrape.DELAY = 0

    return scrape.Webpage(resource="test")

def test_webpage_url_creation(example_org):
    assert example_org.url == "https://example.org/test"

def test_webpage_repr(example_org):
    assert str(example_org) == "https://example.org/test"

def test_storage(example_org):
    assert example_org.storage == pathlib.Path("", "test").absolute()

def test_get_download(example_org):
    success, bs = example_org.get()
    assert success & (bs.body.text == '"Page Definitely Absolutely Found"')

def test_caching(PatchedRequests):
    scrape.CACHE = True
    scrape.CACHE_PATH = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    page = scrape.Webpage(resource="test")

    assert not pathlib.Path(scrape.CACHE_PATH, "test").exists()
    page.get()
    assert pathlib.Path(scrape.CACHE_PATH, "test").exists()


def test_get_download_404(PatchedRequests):
    page = scrape.Webpage(resource="404")

    success, message = page.get()
    assert not success & (message == {"message": "failed to receive webpage data"})
