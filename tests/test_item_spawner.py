import datetime
import random
import unittest
from unittest.mock import MagicMock

from pytest import raises

from tale import _MudContext, util
from tale.base import Container, Item, Location
from tale.driver_if import IFDriver
from tale.item_spawner import ItemSpawner
from tale.zone import Zone


class TestItemSpawner():

    def setup_method(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        _MudContext.driver = driver
        self.items = {'item1': {'name':'item1'}, 'item2':{'name':'item2'}, 'item3': {'name':'item3'}}
        self.item_probabilities = [0.3, 0.5, 0.2]
        self.zone = Zone(name='test_zone')
        self.container = Container(name='test_container')
        self.max_items = 2
        self.spawner = ItemSpawner(self.items, self.item_probabilities, self.zone, spawn_rate=1, container=self.container, max_items=self.max_items)

    def test_spawn_with_container(self):
        item = list(self.items.values())[0]
        self.spawner._random_item = MagicMock(return_value=item)
        self.spawner.spawn()
        assert list(self.container.inventory)[0].name == item['name']

    def test_spawn_without_container(self):
        item = list(self.items.values())[0]
        self.spawner._random_item = MagicMock(return_value=item)
        location = Location(name='test_location')
        self.zone.add_location(location)
        self.spawner.container = None
        self.spawner.spawn()
        assert list(location.items)[0].name == item['name']

    def test_spawn_with_max_items_reached(self):
        self.spawner._random_item = MagicMock(return_value={'name':'item3'})
        location = Location(name='test_location')
        location.init_inventory([Item('item1'), Item('item2')])
        self.zone.add_location(location)
        self.spawner.container = None
        self.spawner.spawn()
        assert len(location.items) == 2
        assert Item('item3') not in location.items

    def test_spawn_with_invalid_zone(self):
        self.spawner._random_item = MagicMock(return_value={'name':'item1'})
        self.spawner.container = None
        with raises(IndexError):
            self.spawner.spawn()
