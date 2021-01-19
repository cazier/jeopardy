import os
import uuid

game_version = 1.0
api_version = 1

game_name = "Jeopardy"
currency = "$"

secret_key = os.getenv(key="SECRET_KEY", default="correctbatteryhorsestaple")


debug = True
sets = 2
start_round = 0

api_endpoint = f"http://127.0.0.1:5000/api/v{api_version}/game"
api_db = os.getenv(key="DB_FILE", default="sample.db")

access_key = uuid.uuid4().hex

if not debug:
    print(f"+{'-' * 46}+")
    print("| ACCESS KEY:", access_key, "|")
    print(f"+{'-' * 46}+")
