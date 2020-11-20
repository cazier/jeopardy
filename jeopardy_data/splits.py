import json
import collections


def by_year(data: dict) -> None:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        year: str = set_["d"][:4]
        output[year].append(set_)

    for year, set_ in output.items():
        with open(file=f"by_year/{year}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


def by_show(data: dict) -> None:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        show: int = int(set_["s"])
        output[show].append(set_)

    show_len: int = len(str(max(output.keys()))) + 1

    for show, set_ in output.items():
        show_str: str = str(show).zfill(show_len)

        with open(file=f"by_show/{show_str}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


def by_round(data: dict) -> None:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        round_: str = set_["r"].lower().replace("!", "").replace(" ", "-")
        output[round_].append(set_)

    for round_, set_ in output.items():
        with open(file=f"by_round/{round_}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


def by_external(data: dict) -> None:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        external: str = str(set_["e"]).lower()
        output[external].append(set_)

    for external, set_ in output.items():
        with open(file=f"by_external/{external}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


def by_complete(data: dict) -> None:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        complete: str = str(set_["f"]).lower()
        output[complete].append(set_)

    for complete, set_ in output.items():
        with open(file=f"by_completion/{complete}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


def by_limit(data: dict, limit: int = 50_000) -> None:
    output: dict = collections.defaultdict(list)
    counter: int = 0

    for set_ in data:
        if len(output[counter]) == limit:
            counter += 1

        output[counter].append(set_)

    counter_len: int = len(str(max(output.keys()))) + 1

    for counter, set_ in output.items():
        counter_str: str = str(counter).zfill(counter_len)

        with open(file=f"by_limit/clues.{counter_str}.json", mode="w") as json_file:
            json.dump(obj=set_, fp=json_file, indent="\t")


if __name__ == "__main__":
    with open(file="clues.json", mode="r") as json_file:
        data: dict = json.load(fp=json_file)

    # by_year(data=data)
    by_show(data=data)
    # by_round(data=data)
    # by_external(data=data)
    # by_complete(data=data)
    by_limit(data=data)
