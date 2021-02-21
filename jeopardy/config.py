import os
import uuid
import pathlib

### GAME SETTINGS ###
game_version = 1.0
api_version = 1

game_name = "Jeopardy"
currency = "$"

secret_key = os.getenv(key="SECRET_KEY", default="correctbatteryhorsestaple")

port = os.getenv(key="PORT", default="5000")

if (env_url := os.getenv(key="APP_URL")) is not None:
    url = env_url.split(",")

else:
    url = "*"

api_endpoint = os.getenv(key="API_ENDPOINT", default=f"http://127.0.0.1:5000/api/v{api_version}/game")

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

# access_key = uuid.uuid4().hex
# if not debug:
#     print(f"+{'-' * 46}+")
#     print("| ACCESS KEY:", access_key, "|")
#     print(f"+{'-' * 46}+")
