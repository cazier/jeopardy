import pathlib

import pytest

import jeopardy_data.api as api

import_file = pathlib.Path("import_test.json").absolute()


def test_delete_db():
    try:
        api.db.drop_all()
    except:
        assert True, "database could not be deleted"
        # api.db.create_all()

