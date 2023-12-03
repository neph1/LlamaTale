
import datetime
from tale.coord import Coord
from tale.items import generic
import tale.parse_utils as parse_utils
from tale import util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.json_story import JsonStory

class TestJsonStory():
    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/world_story/story_config.json')))
    story.init(driver)

    def test_load_story(self):
        assert(self.story)
        assert(self.story.config.name == 'Test Story Config 1')
        entrance = self.story.get_location('Cave', 'Cave entrance')
        assert(entrance.exits['south'].name == 'royal grotto')
        royal_grotto = self.story.get_location('Cave', 'Royal grotto')
        assert(royal_grotto.exits['north'].name == 'cave entrance')
        npc = self.story.get_npc('Kobbo')
        assert(npc)
        assert(npc.location.name == 'Royal grotto')
        assert(npc.stats.hp == 5)
        assert(npc.stats.max_hp == 5)
        assert(npc.stats.level == 1)
        assert(npc.stats.strength == 3)
        assert(self.story.get_item('hoodie').location.name == 'Cave entrance')
        zone_info = self.story.zone_info('Cave')
        assert(zone_info['description'] == 'A dark cave')
        assert(zone_info['races'] == ['kobold', 'bat', 'giant rat'])
        assert(zone_info['items'] == ['torch', 'sword', 'shield'])
        assert(zone_info['level'] == 1)
        assert(zone_info['mood'] == -1)

        items = self.story._catalogue.get_items()
        generic_items = generic.generic_items['fantasy']
        assert(len(items) == len(generic_items))
        assert(self.story._catalogue.get_items() == generic.generic_items['fantasy'])


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

class TestAnythingStory():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)

    def test_load_anything_story(self):
        story_name = 'anything_story'
        story = JsonStory(f'tests/files/{story_name}/', parse_utils.load_story_config(parse_utils.load_json(f'tests/files/{story_name}/story_config.json')))
        story.init(self.driver)

        assert(story)
        assert(story.config.name == 'A Tale of Anything')
        assert(story.config.startlocation_player == 'Abandoned gas station')
        assert(story.config.type == 'a post apocalyptic survival and gathering story')
        assert(story.config.world_info == 'a barren landscape devastated by nuclear blasts. populated by zombie like mutants and irradiated animals. scattered with remnants of civilization')
        assert(story.config.world_mood == -1)
        assert(story.config.context == 'this is where the story background should go')

        assert(len(story._zones) == 1)
        zone = story._zones['The Cursed Swamp']
        assert(zone)
        assert(len(zone.locations) == 4)
        assert(zone.name == 'The Cursed Swamp')
        assert(zone.level == 5)
        assert(zone.mood == -5)

        gas_station = story.get_location('The Cursed Swamp', 'Abandoned gas station')
        assert(gas_station)
        assert(gas_station.name == 'Abandoned gas station')
        assert(gas_station.description == 'an abandoned gas station')
        assert(gas_station.world_location.as_tuple() == (0,0,0))
        assert(gas_station.built == True)
        assert(len(gas_station.exits) == 6)
        assert(gas_station.exits['toxic swamp'])
        assert(gas_station.exits['south'])
        assert(gas_station.exits['deserted town'])
        assert(gas_station.exits['north'])
        assert(gas_station.exits['radiation ridge'])
        assert(gas_station.exits['west'])
        toxic_swamp = story.get_location('The Cursed Swamp', 'Toxic swamp')
        assert(toxic_swamp)
        assert(toxic_swamp.built == False)
        assert(toxic_swamp.world_location.as_tuple() == (0,-1,0))
        deserted_town = story.get_location('The Cursed Swamp', 'Deserted town')
        assert(deserted_town)
        assert(deserted_town.built == False)
        assert(deserted_town.world_location.as_tuple() == (0,1,0))
        radiation_ridge = story.get_location('The Cursed Swamp', 'Radiation ridge')
        assert(radiation_ridge)
        assert(radiation_ridge.built == False)
        assert(radiation_ridge.world_location.as_tuple() == (-1,0,0))


        print(story.get_catalogue.get_items())

        assert(len(story.get_catalogue.get_items()) == 8 + len(generic.generic_items.get(''))) # 8 story items + generic items
        assert(len(story.get_catalogue.get_creatures()) == 5)