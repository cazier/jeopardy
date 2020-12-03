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


# class Pull(object):
#     def __init__(
#         self,
#         start: int = 1,
#         stop: int = 36,
#         include_special: bool = False,
#         initial: bool = False,
#         error_only: bool = False,
#         shortnames: bool = False,
#         method: str = "db",
#     ):
#         self.start = start
#         self.stop = stop
#         self.include_special = include_special
#         self.method = method
#         self.shortnames = shortnames
#         self.json_backup = list()

#         print("Pulling season data")
#         start = time.perf_counter()
#         if error_only:
#             with open("status.json", "r") as json_file:
#                 json_data = json.load(json_file)

#             self.error = list()
#             self.success = json_data["success"]
#             self.pending = json_data["pending"] + json_data["error"]
#             self.outstanding_clues = json_data["out_clues"]

#             self.save(clues=False)
#             initial = False

#         if initial:
#             seasons = get_seasons(start=self.start, stop=self.stop, include_special=self.include_special)
#             store_initial_games(seasons)

#         elapsed = time.perf_counter() - start
#         print(f"Finished pulling season data! Time taken: {elapsed:.2f} seconds")

#         if input("Saved all season data to JSON file. Continue? (yN)").lower() == "y":
#             with open("status.json", "r") as json_file:
#                 json_data = json.load(json_file)

#             self.error = json_data["error"]
#             self.success = json_data["success"]
#             self.pending = json_data["pending"]

#             self.outstanding_clues = json_data["out_clues"]

#             self.scrape()

#     def save(self, clues: bool = True):
#         with open("status.json", "w") as json_file:
#             json.dump(
#                 {
#                     "error": self.error,
#                     "success": self.success,
#                     "pending": self.pending,
#                     "out_clues": self.outstanding_clues,
#                 },
#                 json_file,
#                 indent="\t",
#             )

#         if clues:
#             with open("clue_backup.json", "w") as json_file:
#                 json.dump(self.json_backup, json_file, indent="\t")

#     def scrape(self):
#         print("Starting to scrape game data")
#         while len(self.pending) > 0:
#             start = time.perf_counter()
#             url = self.pending.pop()

#             try:
#                 if url not in self.error and url not in self.success:
#                     clues = Game(url=url)

#                     self.outstanding_clues = clues.json

#                     while len(self.outstanding_clues) > 0:
#                         clue = self.outstanding_clues.pop()

#                         if self.method == "db":
#                             db_add(clue_data=clue, shortnames=self.shortnames)

#                         elif self.method == "web":
#                             web_add(url=self.url, clue_data=clue, shortnames=self.shortnames)

#                         self.json_backup.append(clue)

#             except KeyboardInterrupt:
#                 self.save()
#                 import sys

#                 sys.quit()

#             except:
#                 print(f"An error occurred with game {clues.show}")
#                 self.error.append(url)

#             else:
#                 elapsed = time.perf_counter() - start
#                 print(f"Successfully scraped game {clues.show} Time taken: {elapsed:.2f} seconds")
#                 self.success.append(url)

#                 time.sleep(0.5)

#         self.save()


# if __name__ == "__main__":
#     add(filename="../json/by_year/*.json", method="db")
