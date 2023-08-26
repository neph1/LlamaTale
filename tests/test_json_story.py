
import tale.parse_utils as parse_utils
from tale import mud_context
from tale.base import Location
from tale.driver_if import IFDriver
from tests.files.test_story.story import Story

class TestJsonStory():

    def test_load_story(self):
        story = Story('tests/files/test_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story/test_story_config.json')))
        mud_context.driver = IFDriver()
        story.init(mud_context.driver)
        assert(story)
        assert(story.config.name == 'Test Story Config 1')
        assert(story.get_location('Cave', 'Cave entrance'))
        assert(story.get_npc('Kobbo'))
        assert(story.get_npc('Kobbo').location.name == 'Royal Grotto')
        assert(story.get_item('Hoodie').location.name == 'Cave entrance')

    def test_add_location(self):
        story = Story('tests/files/test_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story/test_story_config.json')))
        mud_context.driver = IFDriver()
        story.init(mud_context.driver)
        new_location = Location('New Location', 'New Location')
        story.add_location(new_location)
