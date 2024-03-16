import random
import unittest
from unittest.mock import MagicMock

from pytest import raises

from tale.base import Container, Item, Location
from tale.item_spawner import ItemSpawner
from tale.zone import Zone


class TestItemSpawner():

    def setup_method(self):
        self.items = [Item('item1'), Item('item2'), Item('item3')]
        self.item_probabilities = [0.3, 0.5, 0.2]
        self.zone = Zone(name='test_zone')
        self.container = Container(name='test_container')
        self.max_items = 2
        self.spawner = ItemSpawner(self.items, self.item_probabilities, self.zone, spawn_rate=1, container=self.container, max_items=self.max_items)

    def test_spawn_with_container(self):
        random.choices = MagicMock(return_value=[self.items[1]])
        self.spawner.spawn()
        assert list(self.container.inventory) == [self.items[1]]

    def test_spawn_without_container(self):
        random.choices = MagicMock(return_value=[self.items[0]])
        location = Location(name='test_location')
        self.zone.locations = [location]
        self.spawner.container = None
        self.spawner.spawn()
        assert list(location.items) == [self.items[0]]

    def test_spawn_with_max_items_reached(self):
        random.choices = MagicMock(return_value=[ Item('item3')])
        location = Location(name='test_location')
        location.init_inventory([Item('item1'), Item('item2')])
        self.zone.locations = [location]
        self.spawner.container = None
        self.spawner.spawn()
        assert len(location.items) == 2
        assert Item('item3') not in location.items

    def test_spawn_with_invalid_zone(self):
        random.choices = MagicMock(return_value=[Item('item1')])
        self.zone.locations = []
        self.spawner.container = None
        with raises(IndexError):
            self.spawner.spawn()
