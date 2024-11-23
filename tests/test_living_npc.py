import json

import responses
from tale import mud_context

from tale.llm import llm_cache
from tale.base import Exit, Item, Living, Location, ParseResult, Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.llm.item_handling_result import ItemHandlingResult
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.skills.magic import MagicType
from tale.skills.skills import SkillType
from tale.skills.weapon_type import WeaponType
from tale.wearable import WearLocation
from tests.supportstuff import FakeDriver, MsgTraceNPC

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
        assert('goal' in json_card.keys())
        assert(eval(json_card['wielding']) == knife.to_dict())

        npc.wielding = None
        card = npc.character_card
        json_card = json.loads(card)
        assert(eval(json_card['wielding']) == npc.stats.unarmed_attack.to_dict())


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

    def test_parse_occupation(self):
        npc = LivingNpc(name='test', gender='m', age=42, occupation='warrior', parse_occupation=True)

        assert npc.occupation == 'warrior' 

        assert npc.stats.weapon_skills.get(WeaponType.ONE_HANDED) > 0
        assert npc.stats.weapon_skills.get(WeaponType.TWO_HANDED) > 0

        npc = LivingNpc(name='test', gender='m', age=42, occupation='ranger', parse_occupation=True)

        assert npc.stats.weapon_skills.get(WeaponType.ONE_HANDED_RANGED) > 0
        assert npc.stats.weapon_skills.get(WeaponType.TWO_HANDED_RANGED) > 0

        npc = LivingNpc(name='test', gender='m', age=42, occupation='healer', parse_occupation=True)

        assert npc.stats.magic_skills.get(MagicType.HEAL) > 0

        npc = LivingNpc(name='test', gender='m', age=42, occupation='wizard', parse_occupation=True)

        assert npc.stats.magic_skills.get(MagicType.BOLT) > 0

        npc = LivingNpc(name='test', gender='m', age=42, occupation='thief', parse_occupation=True)

        assert npc.stats.skills.get(SkillType.PICK_LOCK) > 0
        assert npc.stats.skills.get(SkillType.HIDE) > 0
        assert npc.stats.skills.get(SkillType.SEARCH) > 0

        npc = LivingNpc(name='test', gender='m', age=42, occupation='thief')

        assert npc.stats.skills.get(SkillType.PICK_LOCK) == 0
        assert npc.stats.skills.get(SkillType.HIDE) == 0
        assert npc.stats.skills.get(SkillType.SEARCH) == 0
        
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
        'API_PASSWORD': ''
    }
    driver = FakeDriver()
    driver.story = DynamicStory()
    llm_util = LlmUtil(IoUtil(config=dummy_config, backend_config=dummy_backend_config)) # type: LlmUtil
    llm_util.backend = dummy_config['BACKEND']
    driver.llm_util = llm_util
    story = DynamicStory()
    driver.story = story
    mud_context.config = story.config
    #mud_context.driver = driver

    def setup_method(self):
        self.location = Location("test_room")
        self.npc = LivingNpc(name='test', gender='f', age=35, personality='')
        self.npc2 = LivingNpc(name="actor", gender='f', age=42, personality='')
        self.msg_trace_npc = MsgTraceNPC("fritz", "m", race="human")
        self.location.init_inventory([self.npc, self.npc2, self.msg_trace_npc])

    @responses.activate
    def test_do_say(self):
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"response": "Hello there, how can I assist you today?", "sentiment":"kind"}'}]}, status=200)
        self.npc.do_say(what_happened='something', actor=self.npc2)
        assert(self.npc.sentiments['actor'] == 'kind')
        assert(len(self.npc._observed_events) == 2)
        assert ["test : Hello there, how can I assist you today?\n\n"] == self.msg_trace_npc.messages

    @responses.activate
    def test_idle_action(self):
        mud_context.config.server_tick_method = 'TIMER'
        self.npc.autonomous = False
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"sits down on a chair"'}]}, status=200)
        self.llm_util._character.io_util.response = []
        action = self.npc.idle_action()
        assert(action == 'sits down on a chair')
        assert(llm_cache.get_events(self.npc2._observed_events) == 'test : sits down on a chair\n\n')
        assert ["test : sits down on a chair\n\n"] == self.msg_trace_npc.messages

    @responses.activate
    def test_do_react(self):
        mud_context.config.server_tick_method = 'TIMER'
        action = ParseResult(verb='idle-action', unparsed='something happened', who_list=[self.npc])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"test happens back!"'}]}, status=200)
        self.npc.notify_action(action, self.npc2)
        assert(llm_cache.get_events(self.npc2._observed_events) == 'test : test happens back\n\n')
        assert ["test : test happens back\n\n"] == self.msg_trace_npc.messages

    @responses.activate
    def test_do_react_deferred_exists(self):
        action = ParseResult(verb='reaction', unparsed='something happened', who_list=[self.npc])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'"test happens back!"'}]}, status=200)
        self.npc.notify_action(action, self.npc2)
        # doesn't react first time because already has reacted
        assert(self.npc.deferred_actions == set())
        assert [] == self.msg_trace_npc.messages

        action = ParseResult(verb='reaction', unparsed='something happened again', who_list=[self.npc])

        self.npc.notify_action(action, self.npc2)
        assert(llm_cache.get_events(self.npc._observed_events) == 'something happened<break>something happened again')

    def test_take_action(self):
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        self.location.insert(item)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"take", "item":"test item"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == 'test takes test item')
        assert(self.npc.search_item('test item', include_location=False))

    def test_give_action(self):
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        self.npc.init_inventory([item])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"give", "item":"test item", "target":"actor"}'}]}, status=200)
        self.npc.autonomous_action()
        assert self.npc.search_item('test item', include_location=False) == None
        assert(self.npc2.search_item('test item', include_location=False))
        assert ["test : Test gives test item to test\n"] == self.msg_trace_npc.messages

    def test_move_action(self):
        # Add your test code here
        pass

    @responses.activate
    def test_take_action(self):
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        self.location.insert(item)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"take", "item":"test item"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == 'test takes test item')
        assert(self.npc.search_item('test item', include_location=False))

    @responses.activate
    def test_give_action(self):
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        self.npc.init_inventory([item])
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"give", "item":"test item", "target":"actor"}'}]}, status=200)
        self.npc.autonomous_action()
        assert self.npc.search_item('test item', include_location=False) == None
        assert(self.npc2.search_item('test item', include_location=False))
        assert ["test : Test gives test item to test\n\n"] == self.msg_trace_npc.messages

    @responses.activate
    def test_move_action(self):
        location2 = Location("room 2")
        Exit.connect(self.location, 'room 2', '', None,
            location2, 'room 1', '', None)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"move", "target":"room 2"}'}]}, status=200)
        self.npc.autonomous_action()
        assert(self.npc.location == location2)
        assert ["Test leaves towards room 2."] == self.msg_trace_npc.messages

    @responses.activate
    def test_attack(self):
        giant_rat = Living(name='rat', gender='m')
        self.location.insert(giant_rat)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"attack", "text":"take that, you filthy animal!", "target":"rat"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == 'test attacks rat') # TODO: only receives one message due to change of how targeted actions are handled

    @responses.activate
    def test_say(self):
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"say", "text":"How are you doing?", "target":"actor"}'}]}, status=200)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"response":"Fine."}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == '')  # TODO: receives no message due to change of how targeted actions are handled

    @responses.activate
    def test_hide(self):
        self.npc.stats.skills.set(SkillType.HIDE, 100)
        self.npc.stats.action_points = 1
        self.npc.location.remove(self.npc2, self.npc2)
        self.npc.location.remove(self.msg_trace_npc, self.msg_trace_npc)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"hide", "text":"this looks dangerous!"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == '"this looks dangerous!"')
        assert(self.npc.hidden)

    @responses.activate
    def test_unhide(self):
        self.npc.hidden = True
        self.npc.stats.action_points = 1
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"unhide"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert ['test reveals themselves'] == self.msg_trace_npc.messages
        assert not self.npc.hidden
        
    @responses.activate
    def test_search(self):
        self.npc.stats.skills.set(SkillType.SEARCH, 100)
        self.npc.stats.action_points = 1
        self.npc2.hidden = True
        self.npc2.stats.skills.set(SkillType.HIDE, 0)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'{"action":"search"}'}]}, status=200)
        actions = self.npc.autonomous_action()
        assert(actions == '')
        assert not self.npc2.hidden
        assert ["test searches for something.", "test reveals actor"] == self.msg_trace_npc.messages
