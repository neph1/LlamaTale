import json

import responses
from tale import mud_context
import tale

from tale.llm import llm_cache
from tale.base import Exit, Item, Living, Location, ParseResult, Weapon
from tale.coord import Coord
from tale.llm.LivingNpc import LivingNpc
from tale.llm.item_handling_result import ItemHandlingResult
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.wearable import WearLocation
from tale.zone import Zone
from tests.supportstuff import FakeDriver
class TestLivingNpc():

    drink = Item("ale", "jug of ale", descr="Looks and smells like strong ale.")
    story = DynamicStory()
    mud_context.config = story.config

    def test_handle_item_result_player(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.init_inventory([self.drink])

        player = Player(name='player', gender='m')
        location.init_inventory([npc, player])
        item_result = ItemHandlingResult(item='ale', to='player', from_='test')

        npc.handle_item_result(item_result, player)
        assert(not npc.search_item('ale'))
        assert(player.search_item('ale'))

    def test_handle_item_result_user(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.init_inventory([self.drink])

        player = Player(name='player', gender='m')
        location.init_inventory([npc, player])
        item_result = ItemHandlingResult(item='ale', to='user', from_='test')

        npc.handle_item_result(item_result, player)
        assert(not npc.search_item('ale', include_location=False))
        assert(player.search_item('ale', include_location=False))

    def test_handle_item_result_drop(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.init_inventory([self.drink])

        player = Player(name='player', gender='m')
        location.init_inventory([npc, player])
        item_result = ItemHandlingResult(item='ale', to='', from_='test')

        npc.handle_item_result(item_result, player)

        assert(not npc.search_item('ale', include_location=False))
        assert(self.drink.location == location)

    def test_character_card(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        knife = Weapon("knife", "knife", descr="A sharp knife.")
        npc.wielding = knife
        npc.init_inventory([self.drink, knife])
        card = npc.character_card
        assert('ale' in card)
        json_card = json.loads(card)
        assert(json_card['name'] == 'test')
        assert('ale' in json_card['items'])
        assert('knife' in json_card['items'])
        assert(eval(json_card['wielding']) == knife.to_dict())

    def test_wearing(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        hat = Item("hat", "hat", descr="A big hat.")
        npc.set_wearable(hat, wear_location=WearLocation.HEAD)
        assert npc.get_wearable( WearLocation.HEAD) == hat
        assert list(npc.get_worn_items()) == [hat]

        location = npc.get_wearable_location(hat.name)
        assert location == WearLocation.HEAD

        npc.set_wearable(None, wear_location=WearLocation.HEAD)
        assert npc.get_wearable(WearLocation.HEAD) == None

    def test_memory(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        
        npc._observed_events = [llm_cache.cache_event('test_event'), llm_cache.cache_event('test_event 2')]
        npc.sentiments = {'test': 'neutral'}
        memories_json = npc.dump_memory()
        memories = json.loads(json.dumps(memories_json))


        npc_clean = LivingNpc(name='test', gender='m', age=42, personality='')
        npc_clean.load_memory(memories)

        assert(memories['known_locations'] == {})
        assert(memories['observed_events'] == list(npc_clean._observed_events))
        assert(memories['sentiments'] == npc_clean.sentiments)

        assert(llm_cache.get_events(npc_clean._observed_events) == 'test_event<break>test_event 2')

    def test_avatar_not_exists(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        has_avatar = npc.avatar == 'test'
        assert not has_avatar

    def test_get_observed_events(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc._observed_events = [llm_cache.cache_event('test_event'), llm_cache.cache_event('test_event 2')]
        assert(npc.get_observed_events(1) == 'test_event 2')
        assert(npc.get_observed_events(2) == 'test_event<break>test_event 2')


    # def test_avatar_exists(self):
    #     shutil.copyfile("./tests/files/test.jpg", "./tale/web/resources/test.jpg")
    #     npc = LivingNpc(name='test', gender='m', age=42, personality='')
    #     has_avatar = npc.avatar == 'test'
    #     os.remove("./tale/web/resources/test.jpg")
    #     assert has_avatar

class TestLivingNpcActions():

    dummy_config = {
        'BACKEND': 'kobold_cpp',
        'USER_START': '',
        'USER_END': '',
        'DIALOGUE_PROMPT': '',
    }

    dummy_backend_config = {
        'URL': 'http://localhost:5001',
        'ENDPOINT': '/api/v1/generate',
        'STREAM': False,
        'STREAM_ENDPOINT': '',
        'DATA_ENDPOINT': '',
        'OPENAI_HEADERS': '',
        'OPENAI_API_KEY': '',
        'OPENAI_JSON_FORMAT': '',
    }
    driver = FakeDriver()
    driver.story = DynamicStory()
    llm_util = LlmUtil(IoUtil(config=dummy_config, backend_config=dummy_backend_config)) # type: LlmUtil
    llm_util.backend = dummy_config['BACKEND']
    driver.llm_util = llm_util
    story = DynamicStory()
    driver.story = story
    mud_context.config = story.config
    mud_context.driver = driver
    mud_context.config.server_tick_method = 'TIMER'

    @responses.activate
    def test_do_say(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc2 = LivingNpc(name="actor", gender='f', age=42, personality='')
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"response": "Hello there, how can I assist you today?", "sentiment":"kind"}'}]}, status=200)
        npc.do_say(what_happened='something', actor=npc2)
        assert(npc.sentiments['actor'] == 'kind')
        assert(len(npc._observed_events) == 2)

    @responses.activate
    def test_idle_action(self):
        
        npc = LivingNpc(name='test', gender='f', age=35, personality='')
        npc.autonomous = False
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"sits down on a chair"'}]}, status=200)
        self.llm_util._character.io_util.response = []
        action = npc.idle_action()
        assert(action == 'sits down on a chair\n')
        assert(npc.deferred_actions.pop() == 'test : sits down on a chair\n')

    @responses.activate
    def test_do_react(self):
        npc = LivingNpc(name='test', gender='m', age=44, personality='')
        npc2 = LivingNpc(name="actor", gender='f', age=32, personality='')
        action = ParseResult(verb='idle-action', unparsed='something happened', who_list=[npc])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"test happens back!"'}]}, status=200)
        npc.notify_action(action, npc2)
        assert(npc.deferred_actions == {'test : test happens back\n'})

    @responses.activate
    def test_do_react_deferred_exists(self):
        action = ParseResult(verb='idle-action', unparsed='something happened', who_info=None)
        npc = LivingNpc(name='test', gender='m', age=44, personality='')
        npc.deferred_actions = {'test : existing action\n'}
        npc2 = LivingNpc(name="actor", gender='f', age=32, personality='')
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"test happens back!"'}]}, status=200)
        npc.notify_action(action, npc2)
        assert(npc.deferred_actions == {'test : existing action\n'})

    @responses.activate
    def test_take_action(self):
        location = Location("test_room")
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        location.init_inventory([item])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"take", "item":"test item"}'}]}, status=200)
        npc = LivingNpc(name='test', gender='f', age=37, personality='')
        npc.move(location)
        assert(npc.location == location)
        actions = npc.autonomous_action()
        assert(actions == 'test takes test item')
        assert(npc.search_item('test item', include_location=False))

    @responses.activate
    def test_give_action(self):
        location = Location("test_room")
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        npc = LivingNpc(name='test', gender='f', age=37, personality='')
        npc.init_inventory([item])
        npc2 = LivingNpc(name="actor", gender='f', age=32, personality='')
        location.init_inventory([npc, npc2])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"give", "item":"test item", "target":"actor"}'}]}, status=200)
        npc.autonomous_action()
        assert npc.search_item('test item', include_location=False) == None
        assert(npc2.search_item('test item', include_location=False))

    @responses.activate
    def test_move_action(self):
        location = Location("room 1")
        location2 = Location("room 2")
        npc = LivingNpc(name='test', gender='f', age=27, personality='')
        location.init_inventory([npc])
        Exit.connect(location, 'room 2', '', None,
            location2, 'room 1', '', None)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"move", "target":"room 2"}'}]}, status=200)
        npc.autonomous_action()
        assert(npc.location == location2)

    @responses.activate
    def test_attack(self):
        location = Location("arena")
        npc = LivingNpc(name='test', gender='f', age=27, personality='')
        giant_rat = Living(name='rat', gender='m')
        location.init_inventory([npc, giant_rat])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"attack", "text":"take that, you filthy animal!", "target":"rat"}'}]}, status=200)
        actions = npc.autonomous_action()
        assert(actions == '"take that, you filthy animal!"\ntest attacks rat')

    @responses.activate
    def test_say(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='f', age=27, personality='')
        npc2 = LivingNpc(name="actor", gender='f', age=32, personality='')
        location.init_inventory([npc, npc2])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"say", "text":"How are you doing?", "target":"actor"}'}]}, status=200)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"response":"Fine."}'}]}, status=200)
        actions = npc.autonomous_action()
        assert(actions == '"How are you doing?"')
        

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