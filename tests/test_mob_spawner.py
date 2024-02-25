from tale.base import Living, Location
from tale.llm.contexts.BaseContext import BaseContext
from tale.spawner import MobSpawner
from tale.util import Context
from tests.supportstuff import FakeDriver


class TestMobSpawnerUnitTests():

    def setup_method(self):
        self.mock_location = MockLocation()
        self.spawner = MobSpawner(MockMob(), self.mock_location, spawn_rate=2, spawn_limit=3)

    def test_spawn(self):
        mob = self.spawner.spawn()
        assert mob
        assert mob.location == self.mock_location
        assert self.spawner.spawned == 1

    def test_spawn_limit(self):
        for _ in range(4):
            self.spawner.spawn()
        assert self.spawner.spawned == 3

    def test_remove_mob(self):
        self.spawner.spawned = 2
        self.spawner.remove_mob()
        assert self.spawner.spawned == 1


# Mock classes for testing
class MockMob:
    def __init__(self, name: str = 'Mock Mob', gender: str = 'n'):
        self.do_on_death = None
        self.location = None
        self.gender = gender
        self.name = name

class MockLocation:
    def __init__(self):
        self.mobs = []

    def insert(self, mob):
        self.mobs.append(mob)
        mob.location = self


class TestMobSpawner():

    ctx = Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
    location = Location(name="Test Location")

    mob = Living(name="Test Mob", gender='m')

    def test_spawn(self):
        spawner = MobSpawner(self.mob, self.location, spawn_rate=2, spawn_limit=3)
        mob = spawner.spawn()
        assert mob
        assert mob.location == self.location
        assert mob.name == self.mob.name
        assert len(self.location.livings) == 1
        assert spawner.spawned == 1

        mob.do_on_death(ctx=self.ctx)

        assert spawner.spawned == 0