import datetime
import json
import tale.llm.llm_cache as llm_cache
from tale import mud_context, weapon_type
from tale import zone
from tale import util
from tale.base import Item, Location, Weapon
from tale.coord import Coord
from tale.json_story import JsonStory
from tale.llm.llm_utils import LlmUtil
from tale.npc_defs import StationaryMob
from tale.races import UnarmedAttack
from tale.util import MoneyFormatterFantasy
from tale.zone import Zone
from tests.supportstuff import FakeIoUtil
import tale.parse_utils as parse_utils
from tale.driver_if import IFDriver

class TestLlmUtils():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    test_text_valid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":"user"}, "sentiment":"cheerful"}'

    test_text_valid_no_to = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":""}}'

    test_text_invalid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"", "from":"bartender", "to":"user"}}'

    test_text_invalid_2 = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"", "to":"user"}}'

    actual_response_empty_result = '{   "thoughts": "No items were given, taken, dropped or put.",  "results": {}  }\n'

    actual_response_3 = '{\n    "thoughts": "\ud83d\ude0d Norhardt feels that he is close to finding something important after a long and dangerous journey through rough terrain and harsh weather, and it consumes him fully.",\n    "result": {\n        "item": "map",\n        "from": "Norhardt",\t\n        "to": "Arto"\n    }\n}'
    
    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story_config_empty.json')))
    
    story.init(driver)

    def test_validate_item_response_valid(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["to"] and result["item"])

    def test_validate_item_response_valid_no_to(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid_no_to), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["item"] and not result["to"] )


    def test_validate_item_response_no_item(self):
        items = json.loads('["ale"]')
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.test_text_invalid), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_no_from(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_invalid_2), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_invalid_item(self):
        items = json.loads('["water"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(not valid)
    
    def test_read_items(self):
        character_card = "[Norhardt; gender: m; age: 56; occupation: ; personality: An experienced explorer ; appearance: A grizzled old man, with parch; items:map]"
        items_array = character_card.split('items:')[1].split(']')[0]
        #items = json.loads(items_array)
        assert('map' in items_array)

    def test_generate_item_prompt(self):
        prompt = self.llm_util._character.generate_item_prompt('pre prompt', 'items', 'character1', 'character2')
        assert(prompt)

    def test_handle_response_no_result(self):
        response = '{"thoughts":"The character Norhardt did not give anything listed. The character Arto took nothing. But the author mentioned that they saw something big and fury near where they were walking so likely this creature got dropped there."}'
        result = json.loads(response)
        assert(result)

    def test_validate_response_empty_result(self):
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.actual_response_empty_result), 'Norhardt', 'Arto', 'map')
        assert(not valid)
        assert(not result)

    def test_actual_response_3(self):
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.actual_response_3), 'Norhardt', 'Arto', 'map')
        assert(valid)
        assert(result)
        
    def test_validate_sentiment(self):
        sentiment = self.llm_util._character.validate_sentiment(json.loads(self.test_text_valid))
        assert(sentiment == 'cheerful')

    def test_evoke(self):
        evoke_string = 'test response'
        self.llm_util.io_util = FakeIoUtil(response=evoke_string)
        self.llm_util.set_story(self.story)
        result = self.llm_util.evoke(message='test evoke', player_io=None)
        assert(result)
        assert(llm_cache.get_looks([llm_cache.generate_hash('test evoke')]) == evoke_string)

    def test_generate_character(self):
        character_string = json.dumps(parse_utils.load_json('tests/files/test_character.json'))
        self.llm_util._character.io_util = FakeIoUtil(response = character_string)
        result = self.llm_util._character.generate_character(story_type='a test story')
        assert(result)


    def test_perform_idle_action(self):
        # mostly testing that prompt works
        self.llm_util.set_story(self.story)
        self.llm_util._character.io_util.response = 'Walk to the left'
        location = Location(name='Test Location')
        actions = self.llm_util.perform_idle_action(character_name='Norhardt', location = location, character_card= '{}', sentiments= {}, last_action= '')
        assert(actions == 'Walk to the left\n')

    def test_perform_travel_action(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = 'West'
        result = self.llm_util._character.perform_travel_action(character_name='Norhardt', location = Location(name='Test Location'), character_card= '{}', locations= [], directions= [])
        assert(result == 'West')

    def test_generate_dialogue(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = ['{"response":"Hello there", "sentiment":"cheerful", "give":"ale"}']
        result, item, sentiment = self.llm_util._character.generate_dialogue(conversation='test conversation', 
                                                            character_card='{}', 
                                                            character_name='Norhardt', 
                                                            target='Arto', 
                                                            target_description='{}', 
                                                            sentiment='cheerful', 
                                                            location_description='{}')
        assert(result == 'Hello there')
        assert(item == 'ale')
        assert(sentiment == 'cheerful')

        
    def test_generate_dialogue_json(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = ["{\n  \"response\": \"Autumn greets Test character with a warm smile, her golden hair shining in the sunlight. She returns the greeting, her voice filled with kindness, \'Hello there, how can I assist you today?\'\"\n}"]
        result, item, sentiment = self.llm_util._character.generate_dialogue(conversation='test conversation', 
                                                            character_card='{}', 
                                                            character_name='Norhardt', 
                                                            target='Arto', 
                                                            target_description='{}', 
                                                            sentiment='cheerful', 
                                                            location_description='{}')
        assert(result.startswith("Autumn greets Test character")) 
        assert(item == None)
        assert(sentiment == None)




class TestWorldBuilding():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    generated_location = '{"name": "Outside", "description": "A barren wasteland of snow and ice stretches as far as the eye can see. The wind howls through the mountains like a chorus of banshees, threatening to sweep away any unfortunate soul caught outside without shelter.", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": [{"name":"wolf", "body":"Creature", "unarmed_attack":"BITE", "hp":10, "level":10}]}'
    
    generated_location_extra = '{"Outside": { "description": "A barren wasteland of snow and ice stretches", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": []}}'
    
    generated_zone = '{"name":"Test Zone", "description":"A test zone", "level":10, "mood":-2, "races":["human", "elf", "dwarf"], "items":["sword", "shield"]}'
    
    story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story_config_empty.json')))
    story.config.world_mood = 0
    story.config.world_info = "A test world"
    story.init(driver)

    def test_validate_location(self):
        location = Location(name='Outside')
        location.built = False
        locations, exits, npcs = self.llm_util._world_building._validate_location(json.loads(self.generated_location), location_to_build=location, exit_location_name='Entrance')
        location.add_exits(exits)
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(location.livings) == 1) # wolf
        assert(len(locations) == 2)
        assert(locations[0].name == 'North Pass')
        assert(locations[1].name == 'South Peak')

    def test_validate_location_with_world_objects(self):
        location = Location(name='Outside')
        location.built = False
        loc = json.loads(self.generated_location)
        loc["npcs"] = ["wolf"]
        world_creatures = [{"name": "wolf", "body": "Creature", "unarmed_attack": "BITE", "hp":10, "level":10}]
        locations, exits, npcs = self.llm_util._world_building._validate_location(loc, location_to_build=location, exit_location_name='Entrance', world_creatures=world_creatures)
        location.add_exits(exits)
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(location.livings) == 1) # wolf
        assert(len(locations) == 2)
        assert(locations[0].name == 'North Pass')
        assert(locations[1].name == 'South Peak')

    def test_generate_start_location(self):
        self.llm_util._world_building.io_util.response='{"name": "Greenhaven", "exits": [{"direction": "north", "name": "Misty Meadows", "description": "A lush and misty area filled with rolling hills and sparkling streams. The air is crisp and refreshing, and the gentle chirping of birds can be heard throughout."}, {"direction": "south", "name": "Riverdale", "description": "A bustling town nestled near a winding river. The smell of freshly baked bread and roasting meats fills the air, and the sound of laughter and chatter can be heard from the local tavern."}, {"direction": "east", "name": "Forest of Shadows", "description": "A dark and eerie forest filled with twisted trees and mysterious creatures. The air is thick with an ominous energy, and the rustling of leaves can be heard in the distance."}], "items": [], "npcs": []}'
        location = Location(name='', descr='on a small road outside a village')
        new_locations, exits, npcs = self.llm_util._world_building.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',)
        location = Location(name=location.name, descr=location.description)
        assert(location.name == 'Greenhaven')
        assert(location.title == 'Greenhaven')
        assert(location.description == 'on a small road outside a village')
        assert(exits[0].name == 'misty meadows')
        assert(exits[1].name == 'riverdale')
        assert(new_locations[0].name == 'Misty Meadows')
        assert(new_locations[1].name == 'Riverdale')

    
    def test_generate_start_zone(self):
        # mostly for coverage
        self.llm_util._world_building.io_util.response = self.generated_zone

        result = self.llm_util._world_building.generate_start_zone(location_desc='',
                                                   story_type='',
                                                   story_context='',
                                                   world_info={"info":"", "world_mood":0})
        assert(result.name == 'Test Zone')
        assert(result.races == ['human', 'elf', 'dwarf'])

    def test_generate_world_items(self):
        self.llm_util._world_building.io_util.response = '{"items":[{"name": "sword", "type": "Weapon","value": 100}, {"name": "shield", "type": "Armor", "value": 60}]}'
        result = self.llm_util._world_building.generate_world_items(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(result) == 2)
        sword = result[0]
        assert(sword['name'] == 'sword')
        shield = result[1]
        assert(shield['name'] == 'shield')

    def test_generate_world_creatures(self):
        # mostly for coverage
        self.llm_util._world_building.io_util.response = '{"creatures":[{"name": "dragon", "body": "Creature", "unarmed_attack": "BITE", "hp":100, "level":10}]}'
        result = self.llm_util._world_building.generate_world_creatures(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(result) == 1)
        dragon = result[0]
        assert(dragon["name"] == 'dragon')
        assert(dragon["hp"] == 100)
        assert(dragon["level"] == 10)
        assert(dragon["unarmed_attack"] == UnarmedAttack.BITE.name)


    def test_get_neighbor_or_generate_zone(self):
        """ Tests the get_neighbor_or_generate_zone method of llm_utils.
        """
        self.llm_util._world_building.io_util.response = self.generated_zone
        zone = Zone('Current zone', description='This is the current zone')
        zone.neighbors['east'] = Zone('East zone', description='This is the east zone')
        
        # near location, returning current zone
        current_location = Location(name='Test Location')
        current_location.world_location = Coord(0, 0, 0)
        target_location = Location(name='Target Location')
        target_location.world_location = Coord(1, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # far location, neighbor exists, returning east zone
        current_location.world_location = Coord(10, 0, 0)
        target_location.world_location = Coord(11, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the east zone')
        
        # far location, neighbor does not exist, generating new zone
        self.llm_util.io_util.response = self.generated_zone
        self.llm_util.set_story(self.story)
        current_location.world_location = Coord(-10, 0, 0)
        target_location.world_location = Coord(-11, 0, 0)
        new_zone = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location)
        assert(self.story.get_zone(new_zone.name))
        assert(new_zone.get_info()['description'] == 'A test zone')

        # test add a zone with same name
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # test with non valid json
        self.llm_util.io_util.response = '{"name":test}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')

        # test with valid json but not valid zone
        self.llm_util.io_util.response = '{}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')


    def test_build_location(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location
        self.llm_util.set_story(self.story)
        
        new_locations, exits, npcs = self.llm_util.build_location(location, exit_location_name, zone_info={})
        assert(len(new_locations) == 2)

    def test_build_location_extra_json(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location_extra
        self.llm_util.set_story(self.story)
        new_locations, exits, npcs = self.llm_util.build_location(location, exit_location_name, zone_info={})
        assert(len(new_locations) == 2)

    def test_validate_zone(self):
        center = Coord(5, 0, 0)
        zone = self.llm_util._world_building.validate_zone(json.loads(self.generated_zone), center=center)
        assert(zone)
        assert(zone.name == 'Test Zone')
        assert(zone.description == 'A test zone')
        assert(zone.races == ['human', 'elf', 'dwarf'])
        assert(zone.items == ['sword', 'shield'])
        assert(zone.center == center)
        assert(zone.level == 10)
        assert(zone.mood == -2)

    def test_validate_items(self):
        items = [{"name": "sword", "type": "Weapon", "value": 100}, {"type": "Armor", "value": 60}, {"name": "boots"}]
        valid = self.llm_util._world_building._validate_items(items)
        assert(len(valid) == 2)
        sword = valid[0]
        assert(sword['name'])
        assert(sword['name'] == 'sword')
        assert(sword['type'] == 'Weapon')
        boots = valid[1]
        assert(boots['name'] == 'boots')
        assert(boots['type'] == 'Other')
        
    def test_issue_1_build_location(self):
        z = zone.from_json(json.loads('{   "name": "Whispering Meadows",   "description": "Whispering Meadows is a serene and idyllic area nestled within Eldervale. It is a sprawling expanse of lush green meadows, dotted with colorful wildflowers swaying gently in the breeze. The sweet fragrance of blooming lavender fills the air, creating an enchanting atmosphere. The meadows are home to a variety of friendly creatures, and the soothing whispers of the wind carry tales of peace and harmony. With its tranquil beauty, Whispering Meadows provides the perfect backdrop for a cosy social and farming experience.",   "races": ["Fairie", "Centaur", "Unicorn", "Pixie", "Sylph"],   "items": ["Enchanted Seeds (plantable)", "Harvesting Scythe", "Rainbow Fruit Basket", "Magic Beehive", "Fairy Lantern"],   "mood": "friendly",   "level": 1 }'))
        
        location = Location(name='Whispering Meadows')
        exit_location_name = 'Harvest Grove'
        self.llm_util._world_building.io_util.response = '{"description": "Whispering Meadows is a serene and idyllic area nestled within Eldervale. It is a sprawling expanse of lush green meadows, dotted with colorful wildflowers swaying gently in the breeze. The sweet fragrance of blooming lavender fills the air, creating an enchanting atmosphere. The meadows are home to a variety of friendly creatures, and the soothing whispers of the wind carry tales of peace and harmony. With its tranquil beauty, Whispering Meadows provides the perfect backdrop for a cosy social and farming experience.",   "exits": [     {       "direction": "North",       "name": "Harvest Grove",       "short_descr": "A hidden pathway leads to the Harvest Grove, where trees bear fruits of extraordinary flavors."     },     {       "direction": "East",       "name": "Glimmering Glade",       "short_descr": "A shimmering path leads to the Glimmering Glade, where fireflies illuminate secrets of the woods."     },     {       "direction": "West",       "name": "Twilight Meadow",       "short_descr": "A mysterious trail leads to the Twilight Meadow, where moonlight reveals hidden wonders to explorers."     }   ],   "items": [     "Enchanted Seeds (plantable)",     "Harvesting Scythe",     "Rainbow Fruit Basket",     "Magic Beehive",     "Fairy Lantern",     "Mystical Herb Pouch",     "Whispering Wind Chime",     "Dreamcatcher Necklace"   ],   "npcs": [     {       "name": "Amelia",       "sentiment": "friendly",       "race": "Pixie",       "gender": "f",       "level": 3,       "description": "A mischievous Pixie with wings shimmering in various hues. She loves to play pranks but has a heart of gold."     },     {       "name": "Basil",       "sentiment": "friendly",       "race": "Centaur",       "gender": "m",       "level": 5,       "description": "A gentle Centaur with a serene disposition. He imparts wisdom with every gallop and nurtures plants with care."     },     {       "name": "Celeste",       "sentiment": "friendly",       "race": "Fairie",       "gender": "n",       "level": 4,       "description": "A gracious Fairie with shimmering wings that radiate ethereal light. She ensures the beauty of Whispering Meadows remains eternal."     }   ] }'
        self.llm_util.set_story(self.story)
        new_locations, exits, npcs = self.llm_util.build_location(location, exit_location_name, zone_info=z.get_info())
        assert(len(new_locations) == 2)

    def test_chatgpt_generated_story(self):
        mud_context.driver.moneyfmt = MoneyFormatterFantasy()
        item_response = '{   "items": [     {       "name": "Enchanted Rose",       "type": "Other",       "short_descr": "A magical rose that never withers",       "level": 1,       "value": 50     },     {       "name": "Tea Set",       "type": "Wearable",       "short_descr": "A delightful tea set for elegant gatherings",       "level": 2,       "value": 80     },     {       "name": "Winged Boots",       "type": "Wearable",       "short_descr": "Boots that allow the wearer to fly short distances",       "level": 3,       "value": 120     },     {       "name": "Pixie\'s Elixir",       "type": "Health",       "short_descr": "A revitalizing potion that restores health",       "level": 4,       "value": 150     },     {       "name": "Jester\'s Hat",       "type": "Wearable",       "short_descr": "A colorful hat that brings joy and laughter",       "level": 5,       "value": 200     },     {       "name": "Rainbow Wand",       "type": "Weapon",       "short_descr": "A wand that shoots dazzling rainbow projectiles",       "level": 6,       "value": 250     },     {       "name": "Golden Oz Coin",       "type": "Money",       "short_descr": "A rare and valuable coin from the Land of Oz",       "level": 7,       "value": 300     }   ] }'
        creature_response = '{"creatures": [   {"name": "Whisperwing",    "body": "Small dragon",    "mass": 10,    "hp": 50,    "level": 3,    "unarmed_attack": "CLAWS",    "short_descr": "A colorful dragon with feathered wings and a mischievous personality."},    {"name": "Glowbug",    "body": "Bioluminescent insect",    "mass": 1,    "hp": 10,    "level": 1,    "unarmed_attack": "BITE",    "short_descr": "A tiny insect that emits a soft, soothing glow in the dark."},    {"name": "Fluffpuff",    "body": "Fluffy creature",    "mass": 5,    "hp": 25,    "level": 2,    "unarmed_attack": "TAIL",    "short_descr": "A round, fluffy creature with a cuddly appearance and a playful nature."},    {"name": "Coralite",    "body": "Coral-like sea creature",    "mass": 20,    "hp": 75,    "level": 4,    "unarmed_attack": "TENTACLES",    "short_descr": "A graceful creature that dwells in underwater caves, adorned with vibrant coral-like formations."},    {"name": "Whiskerbeast",    "body": "Feline creature",    "mass": 15,    "hp": 60,    "level": 3,    "unarmed_attack": "CLAWS",    "short_descr": "A playful and agile creature with long, fluffy whiskers and a shimmering fur coat."} ]}'
        zone_desc = '{   "name": "Cozy Meadows",   "description": "A tranquil expanse of lush green meadows, dotted with colorful wildflowers and tall, swaying grass. The air is filled with the sweet fragrance of nature, inviting weary wanderers to rest and enjoy the serene surroundings. Sunlight filters through the canopy of trees, casting golden rays upon the meadows and creating a picturesque setting for picnics and leisurely strolls. Squirrels chase each other playfully, and birds sing melodious tunes from the branches above. It\'s a perfect place to unwind and find respite from the troubles of the world.",   "races": ["whisperwing", "glowbug", "fluffpuff", "coralite", "whiskerbeast"],   "items": {     "enchanted rose": "flower",     "tea set": "utensils",     "winged boots": "footwear",     "pixie\'s elixir": "potion",     "jester\'s hat": "headgear"   },   "mood": "friendly",   "level": 1 }'
        location_desc = '{   "description": "A gentle transition between the lush meadows and the enchanting forests, Meadow\'s Edge is a place where tranquility meets adventure. Tall grass sways in the breeze, beckoning explorers to venture further. The air carries the sweet scent of wildflowers, creating a blissful harmony with nature\'s orchestra.",   "exits": [     {"direction": "North", "name": "Whispering Grove", "short_descr": "A mystical grove filled with ancient whispering trees."},     {"direction": "East", "name": "Butterfly Meadow", "short_descr": "A haven for delicate butterflies, fluttering amidst colorful blooms."},     {"direction": "West", "name": "Sunlit Glade", "short_descr": "A sun-dappled glade where rays of light dance upon the moss-covered ground."}   ],   "items": [     {"name": "Songbird Feather", "type": "treasure"},     {"name": "Dewdrop Pendant", "type": "accessory"},     {"name": "Meadowlark Whistle", "type": "instrument"}   ],   "npcs": [     {"name": "Flora", "sentiment": "friendly", "race": "whisperwing", "gender": "f", "level": 2, "description": "A graceful whisperwing with iridescent wings, known for her soothing melodies."},     {"name": "Bramble", "sentiment": "neutral", "race": "fluffpuff", "gender": "m", "level": 3, "description": "A mischievous fluffpuff with a twinkle in his eye, able to shape-shift into various plants."},     {"name": "Corvus", "sentiment": "hostile", "race": "whiskerbeast", "gender": "m", "level": 5, "description": "A fierce whiskerbeast with sleek black fur, his piercing gaze holds a hint of danger."}   ] }'
        location_desc_2 = '{     "description": "A gentle slope leads to Meadow\'s Edge, where wildflowers stretch out as far as the eye can see. Butterflies dance between the blades of grass, creating a kaleidoscope of colors. A babbling brook runs alongside, inviting visitors to dip their toes in its crystal-clear water.",     "exits": [         {"direction": "North", "name": "Whispering Woods", "short_descr": "A mysterious forest filled with ancient trees that whisper secrets to those who dare to listen."},         {"direction": "East", "name": "Glowing Glade", "short_descr": "An enchanted clearing bathed in a soft, ethereal glow, where fireflies dance in mesmerizing patterns."},         {"direction": "South", "name": "Fluffy Fields", "short_descr": "Rolling hills covered in plush tufts of grass, where fluffy sheep graze peacefully under the watchful eye of their shepherd."}     ],     "items": [],     "npcs": [] }'
        location = Location(name='Meadow\'s Edge')
        exit_location_name = 'Sunflower Way'
        self.llm_util.set_story(self.story)
        self.llm_util._world_building.io_util.response = [item_response, creature_response, zone_desc, location_desc, location_desc_2]
        world_items = self.llm_util._world_building.generate_world_items(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(world_items) > 0)

        world_creatures = self.llm_util._world_building.generate_world_creatures(story_context='', 
                                                   story_type='',
                                                   world_mood=0,
                                                   world_info='')
        assert(len(world_creatures) > 0)
        
        world_info = {'world_description': '', 'world_mood': 2, 'world_items': world_items, 'world_creatures': world_creatures}
        zone = self.llm_util._world_building.generate_start_zone(location_desc='',
                                                   story_type='',
                                                   story_context='',
                                                   world_info=world_info)
        assert(zone)
        new_locations, exits, npcs = self.llm_util.build_location(location, exit_location_name, zone_info=zone.get_info(), world_creatures=world_creatures, world_items=world_items)
        assert(len(new_locations) > 0)
        assert(len(exits) > 0)
        assert(len(location.items) == 3)
        assert(len(location.livings) == 3)

        location2 = Location(name='Fluffy Fields')
        exit_location_name2 = 'Meadow\'s Edge'


        new_locations, exits, npcs = self.llm_util.build_location(location2, exit_location_name2, zone_info=zone.get_info(), world_creatures=world_creatures, world_items=world_items)
        assert(len(new_locations) > 0)
        assert(len(exits) > 0)

    def test_generate_random_spawn(self):
        location = Location(name='Outside')
        self.llm_util._world_building.io_util.response = '{"items":["sword"], "npcs":[{"name": "grumpy dwarf", "level":10, "race": "dwarf"}], "mobs":["wolf"]}'

        world_items = [{'name':'sword', 'type': 'Weapon', 'value': 100}]
        world_creatures = [{'name': 'wolf', 'body': 'Creature', 'unarmed_attack': 'BITE', 'hp':10, 'level':10}]
        zone_info = zone.from_json(json.loads(self.generated_zone)).get_info()

        self.llm_util._world_building.generate_random_spawn(location, 
                                                            zone_info=zone_info,
                                                            story_context=self.story.config.context,
                                                            story_type=self.story.config.type,
                                                            world_info='',
                                                            world_creatures=world_creatures,
                                                            world_items=world_items)
        assert(location.items.pop().name == 'sword')
        assert(location.search_living('grumpy') is not None)
        assert(location.search_living('wolf') is not None)

    def test_generate_random_spawn_empty_world_lists(self):
        # will not generate anything if world lists are empty, for now.
        location = Location(name='Outside')
        self.llm_util._world_building.io_util.response = '{"items":["sword"], "npcs":[{"name": "grumpy dwarf", "level":10, "race": "dwarf"}], "mobs":["wolf"]}'

        world_items = []
        world_creatures = []
        zone_info = zone.from_json(json.loads(self.generated_zone)).get_info()

        self.llm_util._world_building.generate_random_spawn(location, 
                                                            zone_info=zone_info,
                                                            story_context=self.story.config.context,
                                                            story_type=self.story.config.type,
                                                            world_info='',
                                                            world_creatures=world_creatures,
                                                            world_items=world_items)
        assert(len(location.items) == 0)
        assert(location.search_living('grumpy') is not None)
        assert(location.search_living('wolf') is None)

    def test_issue_overwriting_exits(self):
        """ User walks west and enters Rocky Cliffs, When returning east, the exits are overwritten."""
        self.llm_util._world_building.io_util.response=['{"name": "Forest Path", "exits": [{"direction": "north", "name": "Mystic Woods", "short_descr": "A dense, misty forest teeming with ancient magic."}, {"direction": "south", "name": "Blooming Meadow", "short_descr": "A lush, vibrant meadow filled with wildflowers and gentle creatures."}, {"direction": "west", "name": "Rocky Cliffs", "short_descr": "A rugged, rocky terrain with breathtaking views of the surrounding landscape."}], "items": [{"name": "enchanted forest amulet", "type": "Wearable", "description": "A shimmering amulet infused with the magic of the forest, granting the wearer a moderate boost to their defense and resistance to harm."}], "npcs": [{"name": "Florabug", "sentiment": "neutral", "race": "florabug", "gender": "m", "level": 5, "description": "A friendly, curious creature who loves to make new friends."}]}',
                                                        '{"description": "A picturesque beach with soft, golden sand and crystal clear waters. The sun shines bright overhead, casting a warm glow over the area. The air is filled with the sound of gentle waves and the cries of seagulls. A few scattered palm trees provide shade and a sense of tranquility.", "exits": [{"direction": "north", "name": "Coastal Caves", "short_descr": "A network of dark, damp caves hidden behind the sandy shores."}, {"direction": "south", "name": "Rocky Cliffs", "short_descr": "A rugged, rocky coastline with steep drop-offs and hidden sea creatures."}, {"direction": "east", "name": "Mermaid\'s Grotto", "short_descr": "A hidden underwater cave system, rumored to be home to magical sea creatures."}], "items": [], "npcs": []}']
        location = Location(name='', descr='on a small road outside a forest')
        new_locations, exits, npcs = self.llm_util._world_building.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',)
        
        location = Location(name=location.name, descr=location.description)
        
        assert((len(exits) == 3))
        assert((len(new_locations) == 3))
        location.add_exits(exits)
        assert((len(location.exits) == 6))
        rocky_cliffs = new_locations[2] # type: Location
        assert(rocky_cliffs.name == 'Rocky Cliffs')

        new_locations, exits, npcs2 = self.llm_util._world_building.build_location(rocky_cliffs, 
                                                                            'Rocky Cliffs', 
                                                                            story_type='',
                                                                            story_context='',
                                                                            world_info='',
                                                                            zone_info={})
        rocky_cliffs.add_exits(exits)
        assert((len(rocky_cliffs.exits) == 6))
        assert((len(new_locations) == 2))

    def test_generate_note_lore(self):
        self.llm_util._quest_building.io_util.response = 'A long lost tale of a hero who saved the world from a great evil.'
        lore = self.llm_util._world_building.generate_note_lore(story_context='', story_type='', world_info='', zone_info='')
        assert(lore.startswith('A long lost tale'))


class TestQuestBuilding():

    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    def test_generate_note_quest(self):
        self.llm_util._quest_building.io_util.response = '{"name": "Test Quest",  "reason": "A test quest", "target":"Arto", "type":"talk"}'
        quest = self.llm_util._quest_building.generate_note_quest(story_context='', story_type='', world_info='', zone_info='')
        assert(quest.name == 'Test Quest')
        assert(quest.reason == 'A test quest')
        assert(quest.target == 'Arto')

        