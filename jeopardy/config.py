import os
import pathlib

### GAME SETTINGS ###
game_version = 1.0
api_version = 1

game_name = "Jeopardy"
currency = "$"

secret_key = os.getenv(key="SECRET_KEY", default="correctbatteryhorsestaple")

port = os.getenv(key="PORT", default="5000")

url: str | list[str] = "*"

if env_url := os.getenv(key="APP_URL"):
    url = env_url.split(",")

api_endpoint = os.getenv(key="API_ENDPOINT", default=f"http://127.0.0.1:{port}/api/v{api_version}/game")

db_file = pathlib.Path(os.getenv(key="DB_FILE", default="sample.db")).absolute()

if not db_file.exists():
    import sys

    sys.exit("A database file must be provided to begin.")

else:
    api_db = f"sqlite:///{db_file}"

buzzer_time = 2

### DEBUG SETTINGS ###
debug = bool(os.getenv(key="DEBUG", default=False))

sets = 2
start_round = 0
