from tale.base import Location
from tale.coord import Coord
from tale.llm.dynamic_story import DynamicStory


class TestDynamicStory():

    def test_add_location(self):
        story = DynamicStory()
        test_location = Location('test')
        test_location.world_location = Coord(0,0,0)
        story.add_location(test_location)
        assert(story._world._locations['test'] == test_location)
        assert(story._world._grid[(0,0,0)] == test_location)

    def test_add_location_duplicate(self):
        story = DynamicStory()
        test_location = Location('test')
        test_location.world_location = Coord(0,0,0)
        story.add_location(test_location)
        assert(story._world._locations['test'] == test_location)
        assert(story._world._grid[(0,0,0)] == test_location)
        assert(not story.add_location(test_location))

    def test_add_location_to_zone(self):
        story = DynamicStory()
        test_location = Location('test')
        test_location.world_location = Coord(0,0,0)
        test_zone = Zone('zone')
        story.add_zone(test_zone)
        story.add_location(test_location, 'zone')
        assert(story._world._locations['test'] == test_location)
        assert(story._world._grid[(0,0,0)] == test_location)
        assert(story._zones['zone'].locations['test'] == test_location)
        assert(story.get_location(zone='zone', name='test') == test_location)

    def test_find_location_in_zone(self):
        story = DynamicStory()
        test_location = Location('test')
        test_location.world_location = Coord(0,0,0)
        test_zone = Zone('zone')
        story.add_zone(test_zone)
        story.add_location(test_location, 'zone')
        assert(story.find_location('test') == test_location)

    def test_neighbors_for_location(self):
        story = DynamicStory()
        story._locations = dict()
        test_location = Location('test')
        test_location.world_location = Coord(0,0,0)
        north_location = Location('north')
        north_location.world_location = Coord(0,1,0)
        south_location = Location('south')
        south_location.world_location = Coord(0,-1,0)
        east_location = Location('east')
        east_location.world_location = Coord(1,0,0)
        west_location = Location('west')
        west_location.world_location = Coord(-1,0,0)

        story.add_location(test_location)
        story.add_location(north_location)
        story.add_location(south_location)
        story.add_location(east_location)
        story.add_location(west_location)

        neighbors = story.neighbors_for_location(test_location)
        assert(neighbors['north'] == north_location)
        assert(neighbors['south'] == south_location)
        assert(neighbors['east'] == east_location)
        assert(neighbors['west'] == west_location)

    def test_check_setting(self):
        story = DynamicStory()
        assert(story.check_setting('fantasy') == 'fantasy')
        assert(story.check_setting('modern') == 'modern')
        assert(story.check_setting('sci-fi') == 'scifi')
        assert(story.check_setting('steampunk') == '')
        assert(story.check_setting('cyberpunk') == '')
        assert(story.check_setting('western') == '')
