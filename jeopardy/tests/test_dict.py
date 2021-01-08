import help_test
import stores.dict as storage

import pytest


def test_module():
    assert type(storage.GAMES) == dict
    assert len(storage.GAMES) == 0


def test_push():
    storage.push(room=u"ABCD", value=u"TESTDATA")

    assert len(storage.GAMES) == 1
    assert storage.GAMES["ABCD"] == u"TESTDATA"


def test_push_missing_arguments():
    with pytest.raises(TypeError):
        storage.push(value=u"TESTDATA")

    with pytest.raises(TypeError):
        storage.push(room=u"ABCD")

    with pytest.raises(TypeError):
        storage.push()


def test_pull():
    pull = storage.pull(room=u"ABCD")

    assert pull is not None


def test_rooms():
    rooms = storage.rooms()

    assert rooms is not None

