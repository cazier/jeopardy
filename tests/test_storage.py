from jeopardy import storage


class TestDictStorage:
    room = "ABCD"
    game = "game"

    def test_push(self):
        storage.push(self.room, self.game)

        assert storage.GAMES.get(self.room) == self.game

    def test_pull(self):
        assert storage.pull(self.room) == self.game

    def test_rooms(self):
        assert list(storage.rooms()) == [self.room]
