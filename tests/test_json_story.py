
import tale.parse_utils as parse_utils
from tale import mud_context
from tale.base import Location
from tale.driver_if import IFDriver
from tale.json_story import JsonStory
from tests.files.test_story.story import Story

class TestJsonStory():

    story = JsonStory('tests/files/test_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story/test_story_config.json')))
    story.init(IFDriver())

    def test_load_story(self):
        assert(self.story)
        assert(self.story.config.name == 'Test Story Config 1')
        assert(self.story.get_location('Cave', 'Cave entrance'))
        assert(self.story.get_npc('Kobbo'))
        assert(self.story.get_npc('Kobbo').location.name == 'Royal Grotto')
        assert(self.story.get_item('Hoodie').location.name == 'Cave entrance')
        zone_info = self.story.zone_info('Cave')
        print(zone_info)
        assert(zone_info['description'] == 'A dark cave')
        assert(zone_info['races'] == ['kobold', 'bat', 'giant rat'])
        assert(zone_info['items'] == ['torch', 'sword', 'shield'])


    def test_add_location(self):
        new_location = Location('New Location', 'New Location')
        self.story.add_location(new_location)
