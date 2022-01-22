import os
import time
import random
import threading

import pytest
from playwright.sync_api import Page, Playwright, BrowserType, sync_playwright

from jeopardy import web, alex, config, sockets

BASE_URL = "http://192.168.1.220:5001"


@pytest.fixture(scope="module", autouse=True)
def _run():
    def start():
        config.buzzer_time = 0.1
        app = web.create_app()
        socketio = sockets.socketio
        socketio.init_app(app)
        socketio.run(app, host="0.0.0.0", port=5001)

    thread = threading.Thread(target=start)
    thread.daemon = True
    thread.start()

    yield


@pytest.fixture(scope="module")
def players(player1: Page, player2: Page, player3: Page) -> dict[str, Page]:
    return {"Alex": player1, "Brad": player2, "Carl": player3}


@pytest.fixture(scope="module")
def playwright():
    p = sync_playwright().start()
    yield p
    p.stop()


@pytest.fixture(scope="module")
def browser_fix(playwright):
    _browser = get_browser(playwright).launch()
    # _browser = get_browser(playwright).connect('ws://192.168.1.171:55000/page')
    yield _browser
    _browser.close()


@pytest.fixture(scope="module")
def host(playwright: Playwright, browser_fix):
    phone = playwright.devices["iPhone XR"]
    yield browser_fix.new_context(**phone).new_page()


@pytest.fixture(scope="module")
def board(browser_fix):
    yield browser_fix.new_context(viewport={"width": 1440, "height": 450}).new_page()


@pytest.fixture(scope="module")
def player1(playwright: Playwright, browser_fix):
    phone = playwright.devices["iPhone XR"]
    yield browser_fix.new_context(**phone).new_page()


@pytest.fixture(scope="module")
def player2(playwright: Playwright, browser_fix):
    phone = playwright.devices["iPhone XR"]
    yield browser_fix.new_context(**phone).new_page()


@pytest.fixture(scope="module")
def player3(playwright: Playwright, browser_fix):
    phone = playwright.devices["iPhone XR"]
    yield browser_fix.new_context(**phone).new_page()


def get_browser(_playwright: Playwright) -> BrowserType:
    name = os.getenv("PLAYWRIGHT_BROWSER_NAME", "chromium")

    return getattr(_playwright, name, "chromium")


def pid(id: str) -> str:
    return f"css=[id='{id}']"


@pytest.mark.browser
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

        # Match "Start" year field hidden by accordion
        locator = host.locator('css=[name="Start"]')
        assert not locator.is_visible()

    def test_join(self, host: Page):
        host.goto(f"{BASE_URL}/join/")

        # Match "board" action field hidden by accordion (Used when joining a game as the board)
        locator = host.locator('css=[action="/board/"]')
        assert not locator.is_visible()

        # Match "host" action field hidden by accordion (Used when joining a game as the host)
        locator = host.locator('css=[action="/host/"]')
        assert not locator.is_visible()

    def test_game_joining(self, host: Page, board: Page, players: dict[str, Page]):
        host.goto(f"{BASE_URL}/new/")
        host.click("text='Let's Get Started!'")

        (locator := host.locator(pid("magic_link"))).wait_for(state="visible")

        room = locator.text_content().replace("Room:", "").strip()

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
        for _ in range(2):
            for category in range(6):
                host.click(pid(f"category_{category}"))

                for set_ in range(5):
                    assert host.locator(pid(f"q_{category}_{set_}")).is_visible()

                    host.click(pid(f"q_{category}_{set_}"))
                    time.sleep(0.2)

                    if host.locator(pid("wager_round")).is_visible():
                        name, page = random.choice(list(players.items()))

                        host.click(f"text='{name}'")

                        for (other_name, other_page) in players.items():
                            if other_name != name:
                                assert other_page.locator(pid("wager_amount")).is_hidden()

                        score = int(page.locator(pid("score")).text_content().strip())
                        wager = (max(score, 1000) // 100) * 100

                        page.fill(pid("wager_value"), str(wager))
                        page.click("text='Submit!'")

                        host.locator(pid("wager_footer")).wait_for(state="visible")

                        result = random.choice(["correct_wager", "incorrect_wager"])
                        host.click(pid(f"{result}"))

                    else:
                        host.click("text='Finished Reading!'")
                        time.sleep(0.2)

                        for page in players.values():
                            assert "btn-success" in page.locator(pid("buzzer")).get_attribute("class")

                        # Get the _round_status:
                        #  - 0 -> The first player to buzz gets the correct answer
                        #  - 1 -> The second player to buzz gets the correct answer
                        #  - 2 -> The third player to buzz  gets the correct answer
                        #  - 3 -> No player gets the correct answer (the host dimisses)

                        _round_status = random.choice(range(4))

                        # No one answered
                        if _round_status == 3:
                            host.click("text='Dismiss'")
                            time.sleep(0.2)

                            for page in players.values():
                                assert "btn-success" not in page.locator(pid("buzzer")).get_attribute("class")
                                assert "disabled btn-danger" in page.locator(pid("buzzer")).get_attribute("class")

                        else:
                            guess_order = random.sample(list(players.items()), k=len(players))
                            for index, (name, page) in enumerate(guess_order):
                                for (other_name, other_page) in guess_order[:index]:
                                    assert "btn-success" not in other_page.locator(pid("buzzer")).get_attribute(
                                        "class"
                                    )
                                    assert "disabled btn-danger" in other_page.locator(pid("buzzer")).get_attribute(
                                        "class"
                                    )

                                page.click(pid("buzzer"))
                                time.sleep(0.2)

                                assert host.locator(pid("player")).text_content().strip() == name

                                if index != _round_status:
                                    host.click(pid("incorrect_response"))

                                else:
                                    host.click(pid("correct_response"))
                                    break

                    time.sleep(0.2)

                    for name, page in players.items():
                        player_score = int(page.locator(pid("score")).text_content().strip())
                        board_score = int(board.locator(pid(alex.safe_name(name))).text_content().strip())

                        assert player_score == board_score

            host.locator(pid("round_transition")).wait_for(state="visible")
            host.click(pid("start_next_round"))

            host.wait_for_load_state()
            board.wait_for_load_state()

        host.locator(pid("get_wager")).wait_for(state="visible")
        host.click(pid("get_wager"))

        assert not page.locator(pid("show_0")).is_visible()

        reveal_prep = dict()

        for name, page in players.items():
            assert "btn-success" not in host.locator(pid(alex.safe_name(name))).get_attribute("class")
            assert "btn-danger" in host.locator(pid(alex.safe_name(name))).get_attribute("class")

            bg_score = int(page.locator(pid("score")).text_content().strip())
            fg_score = int(page.locator(f"{pid('wager_amount')} >> .score").text_content().strip())

            assert bg_score == fg_score

            wager = (max(fg_score, 1000) // 100) * 100
            page.fill(pid("wager_value"), str(wager))
            page.click("text='Submit!'")

            time.sleep(0.2)

            assert "btn-success" in host.locator(pid(alex.safe_name(name))).get_attribute("class")
            assert "btn-danger" not in host.locator(pid(alex.safe_name(name))).get_attribute("class")

            reveal_prep[name] = {"pre": fg_score, "wager": wager}

        host.locator(pid("show_0")).wait_for(state="visible")

        host.locator(pid("get_questions")).wait_for(state="visible")
        host.click(pid("get_questions"))

        for name, page in players.items():
            assert "btn-success" not in host.locator(pid(alex.safe_name(name))).get_attribute("class")
            assert "btn-danger" in host.locator(pid(alex.safe_name(name))).get_attribute("class")

            page.fill(pid("question_value"), f"{name}'s answer")
            page.click("text='Submit!'")

            time.sleep(0.2)

            assert "btn-success" in host.locator(pid(alex.safe_name(name))).get_attribute("class")
            assert "btn-danger" not in host.locator(pid(alex.safe_name(name))).get_attribute("class")

        host.locator(pid("show_responses")).wait_for(state="visible")
        host.click(pid("show_responses"))

        for (name, scoring) in sorted(reveal_prep.items(), key=lambda k: k[1]["pre"]):
            for screen in (host, board):
                assert screen.locator(pid("player")).text_content() == name
                assert screen.locator(pid("question")).text_content() == f"{name}'s answer"
                assert int(screen.locator(pid("score")).text_content().strip()) == scoring["pre"]

            result = random.choice([("correct_fj", 1), ("incorrect_fj", -1)])
            host.click(pid(f"{result[0]}"))

            final_score = scoring["pre"] + (scoring["wager"] * result[1])
            reveal_prep[name]["final"] = final_score

            assert int(host.locator(pid("amount")).text_content().strip()) == scoring["wager"]
            assert int(host.locator(pid("final_score")).text_content().strip()) == final_score
            assert int(players[name].locator(pid("score")).text_content().strip()) == final_score

            host.click(pid("next"))
            time.sleep(0.2)

        for page in (host, board, *players.values()):
            page.wait_for_load_state()
            assert page.url.endswith("/results/")
