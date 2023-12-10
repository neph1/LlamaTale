import json
import pytest
from tale.base import Item, Location
from tale.coord import Coord
from tale.llm.LivingNpc import LivingNpc
from tale.llm.item_handling_result import ItemHandlingResult
from tale.llm.llm_ext import DynamicStory
from tale.player import Player
from tale.wearable import WearLocation
from tale.zone import Zone

class TestLivingNpc():

    drink = Item("ale", "jug of ale", descr="Looks and smells like strong ale.")

    def test_character_card(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        drink = Item("ale", "jug of ale", descr="Looks and smells like strong ale.")
        npc.init_inventory([drink])
        item = npc.search_item("ale")
        assert(item)
        desc = npc.character_card
        assert('ale' in desc)

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
        npc.init_inventory([self.drink])
        card = npc.character_card
        assert('ale' in card)
        json_card = json.loads(card)
        assert(json_card['name'] == 'test')
        assert(json_card['items'][0] == 'ale')

    def test_wearing(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        hat = Item("hat", "hat", descr="A big hat.")
        npc.set_wearable(hat, wear_location=WearLocation.HEAD)
        assert npc.get_wearable( WearLocation.HEAD) == hat
        assert list(npc.get_worn_items()) == [hat]

    def test_memory(self):
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        from tale.llm import llm_cache
        npc._observed_events = [llm_cache.cache_event('test_event'), llm_cache.cache_event('test_event 2')]
        npc._conversations = [llm_cache.cache_tell('test_tell'), llm_cache.cache_tell('test_tell_2'),llm_cache.cache_tell('test_tell_3')]
        npc.sentiments = {'test': 'neutral'}
        memories_json = npc.dump_memory()
        memories = json.loads(json.dumps(memories_json))


        npc_clean = LivingNpc(name='test', gender='m', age=42, personality='')
        npc_clean.load_memory(memories)

        assert(memories['known_locations'] == {})
        assert(memories['observed_events'] == list(npc_clean._observed_events))
        assert(memories['conversations'] == npc_clean._conversations)
        assert(memories['sentiments'] == npc_clean.sentiments)

        assert(llm_cache.get_events(npc_clean._observed_events) == 'test_event, test_event 2')
        assert(llm_cache.get_tells(npc_clean._conversations) == 'test_tell<break>test_tell_2<break>test_tell_3')


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