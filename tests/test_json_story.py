
import datetime
import os
import shutil
from tale.coord import Coord
from tale.items import generic
import tale.parse_utils as parse_utils
from tale import util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.json_story import JsonStory
from tale.mob_spawner import MobSpawner

class TestJsonStory():
    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/world_story/story_config.json')))
    story.init(driver)

    def test_load_story(self):
        assert(self.story)
        assert(self.story.config.name == 'Test Story Config')
        entrance = self.story.get_location('Cave', 'Cave entrance')
        assert(entrance.exits['south'].name == 'royal grotto')
        royal_grotto = self.story.get_location('Cave', 'Royal grotto')
        assert(royal_grotto.exits['north'].name == 'cave entrance')
        kobbo = self.story.get_npc('Kobbo')
        assert(kobbo)
        assert(kobbo.location.name == 'Royal grotto')
        assert(kobbo.stats.hp == 5)
        assert(kobbo.stats.max_hp == 5)
        assert(kobbo.stats.level == 1)
        assert(kobbo.stats.strength == 3)
        assert(kobbo.locate_item('royal sceptre', include_location=False)[0].name == 'royal sceptre')
        found_item = False
        for item in self.story.get_location('Cave', 'Cave entrance').items:
            if item.name == 'hoodie':
                found_item = True
        assert(found_item)

        mob_spawner = self.story.world.mob_spawners[0] # type: MobSpawner
        assert(mob_spawner.mob_type['name'] == 'bat')
        assert(mob_spawner.location.name == 'Cave entrance')
        assert(mob_spawner.spawn_rate == 60)
        assert(mob_spawner.spawn_limit == 5)
        assert(mob_spawner.spawned == 0)

        zone_info = self.story.zone_info('Cave')
        assert(zone_info['description'] == 'A dark cave')
        assert(zone_info['races'] == ['wolf', 'bat'])
        assert(zone_info['items'] == ['torch', 'Sword'])
        assert(zone_info['level'] == 1)
        assert(zone_info['mood'] == -1)

        items = self.story._catalogue.get_items()
        generic_items = generic.generic_items['fantasy']
        assert(len(items) == len(generic_items) + 1)

        item_spawner = self.story.world.item_spawners[0]
        assert(item_spawner.zone.name == 'Cave')
        assert(item_spawner.spawn_rate == 60)
        assert(item_spawner.max_items == 5)
        assert(item_spawner.items[0]['name'] == 'torch')

        assert self.story.day_cycle
        assert self.story.random_events


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

    def test_save_story_as(self):
        old_dir = os.getcwd()
        os.chdir(os.getcwd() + '/stories/test_story/')
        self.story.save('test_story2')
        assert os.path.exists('../test_story2')
        shutil.rmtree('../test_story2', ignore_errors=True)
        assert not os.path.exists('../test_story2')
        os.chdir(old_dir)

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

class TestWorldInfo():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    story = JsonStory('tests/files/anything_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/anything_story/story_config.json')))
    story.init(driver)

    def test_to_json(self):
        location = Location('Test')
        
        world_json = self.story._world.to_json()
        assert len(world_json["mob_spawners"]) == 0
        assert len(world_json["item_spawners"]) == 0

        mob = dict(gender='m', name='human', aggressive=False)
        spawner = MobSpawner(mob, location, spawn_rate=2, spawn_limit=3)
        self.story._world.add_mob_spawner(spawner=spawner)

        world_json = self.story._world.to_json()

        assert len(world_json["mob_spawners"]) == 1
        assert len(world_json["item_spawners"]) == 0
