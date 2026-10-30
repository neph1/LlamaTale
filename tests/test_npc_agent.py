import json
import types

from tale import mud_context
from tale.base import Location
from tale.llm import llm_cache
from tale.llm.LivingNpc import LivingNpc
from tale.llm.event_memory import EventMemory
from tale.llm.npc_agent import NpcAgent


class TestEventMemory():

    def test_observe_and_observed_events(self):
        memory = EventMemory()
        h1 = memory.observe('first event')
        h2 = memory.observe('second event')
        assert memory.events == [h1, h2]
        assert memory.observed_events() == 'first event<break>second event'
        assert memory.observed_events(1) == 'second event'

    def test_observe_caps_events(self):
        memory = EventMemory(max_events=3)
        for i in range(5):
            memory.observe(f'event {i}')
        assert len(memory.events) == 3
        assert memory.observed_events() == 'event 2<break>event 3<break>event 4'

    def test_action_history_capped_and_recent(self):
        memory = EventMemory(max_actions=3)
        for i in range(5):
            memory.add_action(f'action {i}')
        assert memory.action_history == ['action 2', 'action 3', 'action 4']
        assert memory.recent_actions(2) == ['action 3', 'action 4']
        assert EventMemory().recent_actions(5) == []

    def test_plan_and_next_planned(self):
        memory = EventMemory()
        assert memory.next_planned() is None
        memory.plan('single')
        memory.plan(['a', 'b'])
        memory.plan([])
        assert memory.next_planned() == 'single'
        assert memory.next_planned() == 'a'
        assert memory.next_planned() is None

    def test_sentiments(self):
        memory = EventMemory()
        assert memory.get_sentiment('actor') == ''
        assert memory.get_sentiment('actor', 'default') == 'default'
        memory.set_sentiment('actor', 'hostile')
        assert memory.get_sentiment('actor') == 'hostile'

    def test_dump_load_roundtrip(self):
        memory = EventMemory()
        memory.observe('something happened')
        memory.set_sentiment('actor', 'kind')
        memory.add_action('waves')
        memory.plan(['dances'])
        memory.known_locations = {'room': 'description: room.'}
        memory.goal = 'be merry'
        dumped = memory.dump()
        json.dumps(dumped)  # must be JSON-serializable for savegames

        loaded = EventMemory()
        loaded.load(dumped)
        assert loaded.events == memory.events
        assert loaded.sentiments == {'actor': 'kind'}
        assert loaded.action_history == ['waves']
        assert loaded.planned_actions == [['dances']]
        assert loaded.known_locations == {'room': 'description: room.'}
        assert loaded.goal == 'be merry'
        assert loaded.observed_events() == 'something happened'

    def test_load_merges_legacy_conversations_key(self):
        h = llm_cache.cache_event('old conversation')
        memory = EventMemory()
        memory.load({'observed_events': [], 'conversations': [h]})
        assert memory.events == [h]


class StubLlmUtil:
    """Records calls instead of talking to a backend."""

    def __init__(self):
        self.calls = []
        self.free_form_result = []

    def generate_dialogue(self, **kwargs):
        self.calls.append(('generate_dialogue', kwargs))
        return ('a response', 'an item', 'kind')

    def perform_reaction(self, **kwargs):
        self.calls.append(('perform_reaction', kwargs))
        return 'reacts'

    def perform_idle_action(self, **kwargs):
        self.calls.append(('perform_idle_action', kwargs))
        return 'idles'

    def free_form_action(self, **kwargs):
        self.calls.append(('free_form_action', kwargs))
        return self.free_form_result

    def request_follow(self, **kwargs):
        self.calls.append(('request_follow', kwargs))
        return 'follow-response'

    def generate_image(self, name, description=''):
        self.calls.append(('generate_image', {'name': name, 'description': description}))
        return True


class TestNpcAgent():

    def setup_method(self):
        self.stub = StubLlmUtil()
        self.agent = NpcAgent(self.stub)
        self.location = Location("test_room")

    def test_default_llm_util_resolves_from_driver(self):
        sentinel = object()
        mud_context.driver = types.SimpleNamespace(llm_util=sentinel)
        assert NpcAgent().llm_util is sentinel

    def test_injected_llm_util_is_used(self):
        assert self.agent.llm_util is self.stub
        result = self.agent.free_form_action(character_card={}, character_name='npc',
                                             location=self.location, event_history='hist')
        assert result == []
        name, kwargs = self.stub.calls[0]
        assert name == 'free_form_action'
        assert kwargs['character_name'] == 'npc'
        assert kwargs['event_history'] == 'hist'

    def test_generate_dialogue_delegation(self):
        result = self.agent.generate_dialogue(conversation='conv', character_card={}, character_name='npc',
                                              target='player', sentiment='kind',
                                              location_description='a room', short_len=True)
        assert result == ('a response', 'an item', 'kind')
        name, kwargs = self.stub.calls[0]
        assert name == 'generate_dialogue'
        assert kwargs['target'] == 'player'
        assert kwargs['short_len'] is True

    def test_perform_reaction_delegation(self):
        result = self.agent.perform_reaction(action='hits', character_card={}, character_name='npc',
                                             location=self.location, acting_character_name='player',
                                             event_history='h', sentiment='hostile')
        assert result == 'reacts'
        assert self.stub.calls[0][1]['sentiment'] == 'hostile'

    def test_perform_idle_action_delegation(self):
        result = self.agent.perform_idle_action(character_card={}, character_name='npc',
                                                location=self.location, last_action=['a'],
                                                event_history='h', sentiments={'x': 'y'})
        assert result == 'idles'
        assert self.stub.calls[0][1]['sentiments'] == {'x': 'y'}

    def test_request_follow_delegation(self):
        result = self.agent.request_follow(actor='actor', character_name='npc', character_card={},
                                           event_history='h', location=self.location, asker_reason='because')
        assert result == 'follow-response'
        assert self.stub.calls[0][1]['asker_reason'] == 'because'

    def test_generate_image_delegation(self):
        assert self.agent.generate_image('npc', 'a description') is True
        assert self.stub.calls[0] == ('generate_image', {'name': 'npc', 'description': 'a description'})


class TestLivingNpcWiring():
    """LivingNpc routes its LLM calls through .agent and its state through .memory."""

    def test_autonomous_action_goes_through_agent(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        stub = StubLlmUtil()
        npc.agent = NpcAgent(stub)
        location = Location("test_room")
        location.init_inventory([npc])
        assert npc.autonomous_action() is None  # stub plans no actions
        assert stub.calls[0][0] == 'free_form_action'
        assert stub.calls[0][1]['character_name'] == npc.title

    def test_memory_attributes_delegate_to_event_memory(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        h = llm_cache.cache_event('an event')
        npc._observed_events = [h]
        assert npc.memory.events == [h]
        npc.sentiments = {'a': 'b'}
        assert npc.memory.sentiments == {'a': 'b'}
        npc.goal = 'be brave'
        assert npc.memory.goal == 'be brave'
        npc.memory.observe('another event')
        assert npc._observed_events[-1] == llm_cache.cache_event('another event')
        assert npc.get_observed_events(1) == 'another event'

    def test_dump_load_memory_via_npc(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.memory.observe('evt')
        npc.memory.set_sentiment('x', 'hostile')
        npc.memory.goal = 'g'
        dumped = npc.dump_memory()
        json.dumps(dumped)

        other = LivingNpc(name='other', gender='f', age=30, personality='')
        other.load_memory(dumped)
        assert other.memory.events == npc.memory.events
        assert other.sentiments == {'x': 'hostile'}
        assert other.goal == 'g'
