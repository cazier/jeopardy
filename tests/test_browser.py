import os
import time
import random
import multiprocessing

import faker
import pytest
from playwright.sync_api import Page, Browser, Playwright, BrowserType, sync_playwright

from jeopardy import web, alex, config, sockets

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5001")
LAUNCH = not os.getenv("BASE_URL")

fake = faker.Faker()


@pytest.fixture(scope="module", autouse=True)
def _run():
    def start(port: int):
        config.buzzer_time = 0.1
        app = web.create_app()
        socketio = sockets.socketio
        socketio.init_app(app)
        socketio.run(app, host="0.0.0.0", port=port)

    # Two background processes are run for the backend server, because the eventlet.monkey_patch does not get performed
    # during pytest runs. In "normal" usage, the single server process is acceptable as eventlet handles the async stuff
    api = multiprocessing.Process(name="api", target=start, args=(5000,), daemon=True)
    api.start()

    game = multiprocessing.Process(name="game", target=start, args=(5001,), daemon=True)
    game.start()

    # Adding a one-time delay to ensure each of the api/game processes have completely started.
    time.sleep(10)

    yield


@pytest.fixture(scope="module")
def players(player1: Page, player2: Page, player3: Page) -> dict[str, Page]:
    return {fake.name(): player1, fake.name(): player2, fake.name(): player3}


@pytest.fixture(scope="module")
def playwright() -> Playwright:
    import pathlib

    artifacts = pathlib.Path.cwd().joinpath("artifacts")

    for final in ("host", "board", "player1", "player2", "player3"):
        artifacts = artifacts.joinpath(final)
        artifacts.mkdir(parents=True, exist_ok=True)

        for file in artifacts.glob("*.webm"):
            file.unlink()

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def browser_fix(playwright: Playwright) -> Browser:
    if LAUNCH:
        _browser = get_browser(playwright).launch()
    else:
        _browser = get_browser(playwright).connect(os.getenv("CONNECT_URL"))

    yield _browser

    _browser.close()


@pytest.fixture(scope="module")
def host(browser_fix: Browser):
    browser = browser_fix.new_context(record_video_dir="artifacts/host")
    yield browser.new_page()
    browser.close()


@pytest.fixture(scope="module")
def board(browser_fix: Browser):
    browser = browser_fix.new_context(record_video_dir="artifacts/board")
    yield browser.new_page()
    browser.close()


@pytest.fixture(scope="module")
def player1(browser_fix: Browser):
    browser = browser_fix.new_context(record_video_dir="artifacts/player1")
    yield browser.new_page()
    browser.close()


@pytest.fixture(scope="module")
def player2(browser_fix: Browser):
    browser = browser_fix.new_context(record_video_dir="artifacts/player2")
    yield browser.new_page()
    browser.close()


@pytest.fixture(scope="module")
def player3(browser_fix: Browser):
    browser = browser_fix.new_context(record_video_dir="artifacts/player3")
    yield browser.new_page()
    browser.close()


def get_browser(_playwright: Playwright) -> BrowserType:
    name = os.getenv("PLAYWRIGHT_BROWSER_NAME", "chromium")

    return getattr(_playwright, name, "chromium")


def pid(id: str) -> str:
    return f"css=[id='{id}']"


def js_id_equality(id: str, value: str) -> str:
    return f"document.getElementById('{id}').textContent == '{value}'"


def js_has_class(id: str, value: str) -> str:
    return f"document.getElementById('{id}').classList.contains('{value}')"


@pytest.mark.browser
# @pytest.mark.incremental
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
            host.wait_for_timeout(2000)

            for category in range(6):
                host.locator(pid(f"category_{category}")).wait_for(state="visible")

                try:
                    host.click(pid(f"category_{category}"))

                # Fix for occasional double click on category reveal
                except:  # noqa: E722
                    host.evaluate(f"$('#content_{category}').collapse('show')")

                for set_ in range(5):
                    host.locator(pid(f"q_{category}_{set_}")).wait_for(state="visible")
                    host.click(pid(f"q_{category}_{set_}"))

                    host.locator(pid("master-modal")).wait_for(state="visible")

                    if host.locator(pid("wager_round")).is_visible():
                        name, page = random.choice(list(players.items()))

                        host.click(f"text='{name}'")

                        for other_name, other_page in players.items():
                            if other_name != name:
                                assert other_page.locator(pid("wager_amount")).is_hidden()

                        score = int(page.locator(pid("score")).text_content().strip())
                        wager = (max(score, 1000) // 100) * 100

                        page.fill(pid("wager_value"), str(wager))
                        page.click("text='Submit!'")

                        # Fix for the time the modal stayed up after clicking submit
                        if page.locator(pid("master-modal")).is_visible:
                            page.evaluate("$('#master-modal').modal('hide')")

                        host.locator(pid("wager_footer")).wait_for(state="visible")

                        result = random.choice(["correct_wager", "incorrect_wager"])
                        host.click(pid(f"{result}"))

                    else:
                        host.click("text='Finished Reading!'")

                        for page in players.values():
                            page.wait_for_function(js_has_class("buzzer", "btn-success"))
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

                            for page in players.values():
                                page.wait_for_function(js_has_class("buzzer", "btn-danger"))

                                assert "btn-success" not in page.locator(pid("buzzer")).get_attribute("class")
                                assert "disabled btn-danger" in page.locator(pid("buzzer")).get_attribute("class")

                        else:
                            guess_order = random.sample(list(players.items()), k=len(players))
                            for index, (name, page) in enumerate(guess_order):
                                for other_name, other_page in guess_order[:index]:
                                    assert "btn-success" not in other_page.locator(pid("buzzer")).get_attribute("class")
                                    assert "disabled btn-danger" in other_page.locator(pid("buzzer")).get_attribute(
                                        "class"
                                    )

                                page.click(pid("buzzer"))
                                host.wait_for_function(js_id_equality("player", name))

                                assert host.locator(pid("player")).text_content().strip() == name

                                if index != _round_status:
                                    host.click(pid("incorrect_response"))

                                else:
                                    host.click(pid("correct_response"))
                                    break

                    host.wait_for_timeout(200)

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

            host.wait_for_function(js_has_class(alex.safe_name(name), "btn-success"))

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

            host.wait_for_function(js_has_class(alex.safe_name(name), "btn-success"))

            assert "btn-success" in host.locator(pid(alex.safe_name(name))).get_attribute("class")
            assert "btn-danger" not in host.locator(pid(alex.safe_name(name))).get_attribute("class")

        host.locator(pid("show_responses")).wait_for(state="visible")
        host.click(pid("show_responses"))

        host.locator(pid("final_reveal")).wait_for(state="visible")

        for name, scoring in sorted(reveal_prep.items(), key=lambda k: k[1]["pre"]):
            for screen in (host, board):
                host.wait_for_function(js_id_equality("player", name))

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

        winner = sorted(reveal_prep.items(), key=lambda k: k[1]["final"])[-1]

        for page in (host, board, players[winner[0]]):
            page.wait_for_function("document.location.pathname.indexOf('results') > 0")

            assert page.url.endswith("/results/")

        for page in players.values():
            assert page.url.endswith("/results/")
