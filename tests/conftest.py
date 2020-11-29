import pytest


import os
import json
import shutil
import pathlib


@pytest.fixture(autouse=True, scope="session")
def empty_cache_upon_completion():
    yield

    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def empty_cache_after_test():
    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    if path.exists():
        shutil.rmtree(path=path)

    else:
        path.mkdir(parents=True)


@pytest.fixture
def test_data():
    with open("tests/files/complete.json", "r") as sample_file:
        data = json.load(sample_file)

    with open("tests/files/incomplete.json", "r") as sample_file:
        data.extend(json.load(sample_file))

    return data
