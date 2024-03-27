
import datetime
from tale import _MudContext, util
from tale.base import Item, Living, Location, Remains, Stats
from tale.driver_if import IFDriver
from tale.mob_spawner import MobSpawner

class TestMobSpawnerUnitTests():

    def setup_method(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        _MudContext.driver = driver
        self.mock_location = MockLocation()
        self.spawner = MobSpawner(MockMob(), self.mock_location, spawn_rate=2, spawn_limit=3)

    def test_remove_mob(self):
        self.spawner.spawned = 2
        self.spawner.remove_mob()
        assert self.spawner.spawned == 1


    def test_item_drop(self):
        spawner = MobSpawner(MockMob(), self.mock_location, spawn_rate=2, spawn_limit=3, drop_items=['test item'], drop_item_probabilities=[1])
        remains = MockContainer()
        spawner.remove_mob(remains)
        assert spawner.spawned == -1
        assert remains.item_inserted

# Mock classes for testing
class MockMob:
    def __init__(self, name: str = 'Mock Mob', gender: str = 'n', race: str = 'human'):
        self.do_on_death = None
        self.location = None
        self.gender = gender
        self.name = name
        self.aggressive = False
        self.title = name
        self.description = "Mock Mob"
        self.should_produce_remains = False
        self.stats = Stats.from_race(race)

class MockLocation:
    def __init__(self):
        self.mobs = []
        self.description = "Mock Location"

    def insert(self, mob: Living):
        self.mobs.append(mob)
        mob.location = self

    def tell(self, msg, extra_context):
        pass

class MockContainer:
    def __init__(self):
        self.item_inserted = False

    def insert(self, item, actor: Living):
        self.item_inserted = True

class TestMobSpawner():

    def setup_method(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        _MudContext.driver = driver

    def test_spawn(self):
        location = Location(name="Test Location")
        mob = dict(name="Test Mob", gender='m', race='human', aggressive=False)
        spawner = MobSpawner(mob, location, spawn_rate=2, spawn_limit=3)
        mob = spawner.spawn()
        assert mob
        assert mob.location == location
        assert mob.name == mob.name
        assert mob.aggressive == False
        assert len(location.livings) == 1
        assert spawner.spawned == 1

        mob.do_on_death()

        assert spawner.spawned == 0

        spawner.mob_type['aggressive'] = True

        mob = spawner.spawn()
        assert mob.aggressive == True


    def test_item_drop(self):
        location = Location(name="Test Location")
        mob = Living(name="Test Mob", gender='m')
        test_item = Item(name="Test Item")
        spawner = MobSpawner(mob, location, spawn_rate=2, spawn_limit=3, drop_items=[test_item], drop_item_probabilities=[1])
        remains = Remains('Test Remains')
        spawner.remove_mob(remains)
        assert remains.inventory_size == 1
