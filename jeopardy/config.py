import os
import uuid

api_version = 1

game_name = "Jeopardy"
currency = "$"

secret_key = os.getenv(key="SECRET_KEY", default="correctbatteryhorsestaple")


debug = False
sets = 2
start_round = 0

api_endpoint = "http://127.0.0.1:5001/game"

access_key = uuid.uuid4().hex

if not debug:
    print(f"+{'-' * 46}+")
    print("| ACCESS KEY:", access_key, "|")
    print(f"+{'-' * 46}+")
