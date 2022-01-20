import nest_asyncio

nest_asyncio.apply()


import os
import time
import random
import threading

import pytest
from playwright.sync_api import Page, Playwright, BrowserType, sync_playwright

from jeopardy import web, alex, config, sockets

pytestmark = pytest.mark.browser
SHOW = not bool(os.getenv("SHOW", False))


def get_browser(_playwright: Playwright) -> BrowserType:
    name = os.getenv("PLAYWRIGHT_BROWSER_NAME", "firefox")

    return getattr(_playwright, name, "firefox")


BASE_URL = "http://127.0.0.1:5001"


@pytest.fixture(scope="module", autouse=True)
def _run():
    def start():
        app = web.create_app()
        socketio = sockets.socketio
        socketio.init_app(app)
        socketio.run(app, port=5001)

    thread = threading.Thread(target=start)
    thread.daemon = True
    thread.start()

    yield


@pytest.fixture(scope="module")
def players(player1: Page, player2: Page, player3: Page) -> dict[str, Page]:
    return {"Alex": player1, "Brad": player2, "Carl": player3}


# @pytest.fixture(scope='module', autouse=True)
# def _run():
#     path = pathlib.Path().cwd().joinpath('jeopardy', 'web.py')
#     assert path.exists()

#     process = subprocess.Popen(f'PORT=5001 python {str(path)}', shell=True)
#     print(process.pid)
#     yield

#     os.kill(process.pid, signal.SIGTERM)


@pytest.fixture(scope="module")
def playwright():
    p = sync_playwright().start()
    yield p
    p.stop()


@pytest.fixture(scope="module")
def browser_fix(playwright):
    _browser = get_browser(playwright).launch(headless=SHOW)
    yield _browser
    _browser.close()


@pytest.fixture(scope="module")
def host(browser_fix):
    yield browser_fix.new_context().new_page()


@pytest.fixture(scope="module")
def board(browser_fix):
    yield browser_fix.new_context().new_page()


@pytest.fixture(scope="module")
def player1(browser_fix):
    yield browser_fix.new_context().new_page()


@pytest.fixture(scope="module")
def player2(browser_fix):
    yield browser_fix.new_context().new_page()


@pytest.fixture(scope="module")
def player3(browser_fix):
    yield browser_fix.new_context().new_page()


@pytest.mark.incremental
class TestBrowsers:
    def test_index(self, host: Page):
        host.goto(BASE_URL)
        assert host.title() == f"{config.game_name} - Python/WebSocket Trivia!"

        host.click("text='Start a New Game!'")
        assert host.url.endswith("/new/")

        host.go_back()

        host.click("text='Join a Game!'")
        assert host.url.endswith("/join/")

    def test_new(self, host: Page):
        host.goto(f"{BASE_URL}/new/")

        locator = host.locator('css=[name="Start"]')
        assert not locator.is_visible()

    def test_join(self, host: Page):
        host.goto(f"{BASE_URL}/join/")

        locator = host.locator('css=[action="/board/"]')
        assert not locator.is_visible()

        locator = host.locator('css=[action="/host/"]')
        assert not locator.is_visible()

    def test_game_joining(self, host: Page, board: Page, players: dict[str, Page]):
        host.goto(f"{BASE_URL}/new/")
        host.click("text='Let's Get Started!'")

        room = host.locator('css=[id="magic_link"]').text_content().replace("Room:", "").strip()

        for name, page in players.items():
            page.goto(f"{BASE_URL}/join/{room}")
            page.fill('css=[name="name"]', name)
            page.click("#cplayer >> text=Let's Go!")

            page.wait_for_load_state()

            assert name in page.content()
            break

        board.goto(f"{BASE_URL}/join/{room}")
        board.click('text="Board Settings"')
        board.click("#cboard >> text=Let's Go!")

        board.wait_for_load_state()

        assert name in board.content()

        for name, page in list(players.items())[1:]:
            page.goto(f"{BASE_URL}/join/{room}")
            page.fill('css=[name="name"]', name)
            page.click("#cplayer >> text=Let's Go!")

            page.wait_for_load_state()
            assert name in page.content()

            board.wait_for_load_state()
            assert name in board.content()

        for name in players.keys():
            assert name in board.content()
            assert alex.safe_name(name) in board.content()

    def test_game_play(self, host: Page, board: Page, players: dict[str, Page]):
        for category in range(6):
            host.click(f'css=[id="category_{category}"]')
            for set_ in range(5):
                assert host.locator(f'css=[id="q_{category}_{set_}"]').is_visible()

                host.click(f'css=[id="q_{category}_{set_}"]')

                if host.locator("css=[id='wager_round']").is_visible():
                    name, page = random.choice(players)

                    host.click(f"text='{name}'")
                    assert False

                else:
                    host.click("text='Finished Reading!'")

                    for page in players.values():
                        assert "btn-success" in page.locator('css=[id="buzzer"]').get_attribute("class")

                    # Get the _round_status:
                    #  - 0 -> The first player to buzz gets the correct answer
                    #  - 1 -> The second player to buzz gets the correct answer
                    #  - 2 -> The third player to buzz  gets the correct answer
                    #  - 3 -> No player gets the correct answer (the host dimisses)

                    _round_status = random.choice(range(4))

                    print(_round_status)

                    # No one answered
                    if _round_status == 3:
                        host.click("text='Dismiss'")

                        for page in players.values():
                            assert "btn-success" not in page.locator('css=[id="buzzer"]').get_attribute("class")
                            assert "disabled btn-danger" in page.locator('css=[id="buzzer"]').get_attribute("class")

                    else:
                        for index, (name, page) in enumerate(random.sample(list(players.items()), k=len(players))):
                            print(index, name, page)
                            page.click("css=[id='buzzer']")
                            time.sleep(3)

                            assert host.locator("css=[id='player']").text_content().strip() == name

                            if index != _round_status:
                                host.click("css=[id='incorrect_response']")

                            else:
                                host.click("css=[id='correct_response']")
                                break

                    page.click('css=[id="buzzer"]')
                    assert "btn-success" not in page.locator('css=[id="buzzer"]').get_attribute("class")
                    assert "disabled btn-danger" in page.locator('css=[id="buzzer"]').get_attribute("class")

                board.wait_for_load_state()

                for name, page in players.items():
                    player = int(page.locator("css=[id='score']").text_content().strip())
                    print(alex.safe_name(name))
                    print(name)
                    board.pause()
                    assert player == int(board.locator(f"css=[id='{alex.safe_name(name)}']").text_content().strip())

                assert True
