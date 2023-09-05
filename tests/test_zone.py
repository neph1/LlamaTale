""" Tests zone.py """

from tale.base import Location
from tale.coord import Coord
from tale.zone import Zone


class TestZone():

    def test_init(self):
        zone = Zone('test')
        assert zone.name == 'test'
        assert zone.description == ''
        assert zone.level == 1
        assert zone.mood == 0
        assert zone.size == 5
        assert zone.center.x == 0
        assert zone.center.y == 0
        assert zone.center.z == 0
        assert zone.locations == {}
        assert zone.neighbors == {} 
        
    def test_add_location(self):
        zone = Zone('test')
        zone.add_location(Location('test'))
        assert zone.locations['test'].name == 'test'

    def test_get_location(self):
        zone = Zone('test')
        zone.add_location(Location('test'))
        assert zone.get_location('test').name == 'test'

    def test_get_info(self):
        zone = Zone('test')
        zone.description = 'test'
        zone.level = 2
        zone.mood = 3
        zone.races = ['human', 'elf', 'dwarf']
        zone.items = ['sword', 'shield', 'armor']
        assert zone.get_info() == {"description":'test', 
                                   "level":2, 
                                   "mood":3, 
                                   "races": ['human', 'elf', 'dwarf'],
                                   "items":['sword', 'shield', 'armor']}
        
    def test_get_neighbor(self):
        zone = Zone('test')
        zone.neighbors['north'] = Zone('north')
        zone.neighbors['east'] = Zone('east')
        zone.neighbors['south'] = Zone('south')
        zone.neighbors['west'] = Zone('west')
        assert zone.get_neighbor(Coord(0, -1, 0)).name == 'north'
        assert zone.get_neighbor(Coord(1, 0, 0)).name == 'east'
        assert zone.get_neighbor(Coord(0, 1, 0)).name == 'south'
        assert zone.get_neighbor(Coord(-1, 0, 0)).name == 'west'

    def test_on_edge(self):
        zone = Zone('test')
        
        # short distance will never trigger
        distance_short = Coord(3, 0, 0)

        assert zone.on_edge(distance_short, Coord(1, 0, 0)) == False
        assert zone.on_edge(distance_short, Coord(-1, 0, 0)) == False

        # very long distance will always trigger
        distance_long = Coord(11, 0, 0)

        assert zone.on_edge(distance_long, Coord(1, 0, 0)) == True
        assert zone.on_edge(distance_long, Coord(-1, 0, 0)) == True