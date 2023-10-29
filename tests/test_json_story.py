
import datetime
from tale.coord import Coord
import tale.parse_utils as parse_utils
from tale import mud_context, util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.json_story import JsonStory
from tests.files.test_story.story import Story

class TestJsonStory():
    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/world_story/story_config.json')))
    story.init(driver)

    def test_load_story(self):
        assert(self.story)
        assert(self.story.config.name == 'Test Story Config 1')
        assert(self.story.get_location('Cave', 'Cave entrance'))
        assert(self.story.get_npc('Kobbo'))
        assert(self.story.get_npc('Kobbo').location.name == 'Royal grotto')
        assert(self.story.get_item('hoodie').location.name == 'Cave entrance')
        zone_info = self.story.zone_info('Cave')
        assert(zone_info['description'] == 'A dark cave')
        assert(zone_info['races'] == ['kobold', 'bat', 'giant rat'])
        assert(zone_info['items'] == ['torch', 'sword', 'shield'])
        assert(zone_info['level'] == 1)
        assert(zone_info['mood'] == -1)


    def test_add_location(self):
        new_location = Location('New Location', 'New Location')
        new_location.world_location = Coord(0,0,0)
        self.story.add_location(new_location)

    def test_find_location(self):
        location = self.story.find_location('Cave entrance')
        assert(location)
        assert(location.name == 'Cave entrance')

    def test_save_story(self):
        self.story.save()
