import pytest

import pathlib
import os
import glob


@pytest.yield_fixture(autouse=True, scope="session")
def empty_cache_dir():
    yield

    path = pathlib.Path(os.getcwd(), "tests/files/cache").absolute()

    for file in glob.glob(f"{path}/*"):
        os.remove(file)
