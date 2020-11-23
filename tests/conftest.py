import pytest

import pathlib
import os
import shutil


@pytest.fixture(autouse=True, scope="session")
def empty_cache_upon_completion():
    yield

    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()
    shutil.rmtree(path=path)
    path.mkdir()


@pytest.fixture()
def empty_cache_after_test():
    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()
    shutil.rmtree(path=path)
    path.mkdir()
