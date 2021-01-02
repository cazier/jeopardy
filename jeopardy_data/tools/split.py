import json
import collections


def perform_split(data: list, qualifier: str, num: int = -1) -> dict:
    output: dict = collections.defaultdict(list)

    for set_ in data:
        if num != -1:
            identifier = set_[qualifier][:num]

        else:
            identifier = set_[qualifier]

        output[identifier].append(set_)

    return output


def by_year(data: list) -> dict:
    if "date" in data[0].keys():
        query = "date"

    elif "d" in data[0].keys():
        query = "d"

    else:
        raise KeyError("The input data appears is missing the key to split by date. Please review your data.")

    return perform_split(data=data, qualifier=query, num=4)


def by_show(data: list) -> dict:
    if "show" in data[0].keys():
        query = "show"

    elif "s" in data[0].keys():
        query = "s"

    else:
        raise KeyError("The input data appears is missing the key to split by show. Please review your data.")

    return perform_split(data=data, qualifier=query)


def by_round(data: list) -> dict:
    if "round" in data[0].keys():
        query = "round"

    elif "r" in data[0].keys():
        query = "r"

    else:
        raise KeyError("The input data appears is missing the key to split by round. Please review your data.")

    return perform_split(data=data, qualifier=query)


def by_external(data: list) -> dict:
    if "external" in data[0].keys():
        query = "external"

    elif "e" in data[0].keys():
        query = "e"

    else:
        raise KeyError("The input data appears is missing the key to split by external. Please review your data.")

    return perform_split(data=data, qualifier=query)


def by_complete(data: list) -> dict:
    if "complete" in data[0].keys():
        query = "complete"

    elif "f" in data[0].keys():
        query = "f"

    else:
        raise KeyError("The input data appears is missing the key to split by complete. Please review your data.")

    return perform_split(data=data, qualifier=query)


def by_limit(data: dict, limit: int = 50_000) -> None:
    if type(limit) != int:
        raise TypeError("limit must be an integer")

    output: dict = collections.defaultdict(list)
    counter = 0

    for set_ in data:
        if len(output[counter]) == limit:
            counter += 1

        output[counter].append(set_)

    return output
