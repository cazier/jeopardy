import json
import time

import pathlib


def web_add(url: str, clue_data: dict, shortnames: bool = True):
    import requests

    def key(key: str) -> str:
        if shortnames:
            return clue_data[key[0].lower() if key.lower() != "complete" else "f"]

        return clue_data[key]

    data = {
        k: key(k) for k in ("date", "category", "show", "round", "answer", "question", "value", "external", "complete")
    }

    requests.post(url=url, json=data)


def store_initial_games(seasons: list) -> None:
    with open("status.json", "w") as json_file:
        json.dump(
            {
                "error": [],
                "success": [],
                "pending": [game_url for season in seasons for game_url in season.games],
                "out_clues": [],
            },
            json_file,
            indent="\t",
        )


def download_external_files(filename: str, output: str = "media", delay: float = 0.5):
    import requests
    import shutil
    from io import BytesIO

    output_path = pathlib.Path(output)

    if not output_path.exists():
        output_path.mkdir()

    with open(file=filename, mode="r") as downloads_file:
        urls: list = [[line.split()[0], line.split()[1]] for line in downloads_file.readlines()]

    for (filename, url) in urls[:3]:
        data = requests.get(url=url)

        if data.status_code == 200:
            filename += pathlib.Path(url).suffix

            with open(file=pathlib.Path(output_path, filename), mode="wb") as external_file:
                shutil.copyfileobj(fsrc=BytesIO(initial_bytes=data.content), fdst=external_file)

        time.sleep(delay)


def add(filename: str, method: str, progress: bool, url: str = "", shortnames: bool = True):
    if progress:
        from tqdm import tqdm
    
    else:
        tqdm = lambda k: k

    import glob

    ROUNDS = {"Jeopardy!": 0, "Double Jeopardy!": 1, "Final Jeopardy!": 2, "Tiebreaker": 4}

    for file in tqdm(glob.glob(filename)):
        with open(file=file, mode="r") as json_file:
            file = json.load(json_file)

        for set_ in tqdm(file):
            set_["v"] = int(set_["v"].replace("$", ""))
            set_["r"] = ROUNDS[set_["r"]]

            if method == "db":
                from api.database import add
                add(clue_data=set_, uses_shortnames=shortnames)

            elif method == "web":
                web_add(url=url, clue_data=set_, shortnames=shortnames)

            else:
                raise NotImplementedError


# if __name__ == "__main__":
#     add(filename="../json/by_year/*.json", method="db")
