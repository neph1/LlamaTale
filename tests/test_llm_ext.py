import json
import pytest
from tale.base import Item, Location
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.player import Player

class TestLlmExt():

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
        item_result = json.loads('{"from":"test", "to":"player", "item":"ale"}')

        npc.handle_item_result(item_result, player)
        assert(not npc.search_item('ale'))
        assert(player.search_item('ale'))

    def test_handle_item_result_user(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.init_inventory([self.drink])

        player = Player(name='player', gender='m')
        location.init_inventory([npc, player])
        item_result = json.loads('{"from":"test", "to":"user", "item":"ale"}')

        npc.handle_item_result(item_result, player)
        assert(not npc.search_item('ale', include_location=False))
        assert(player.search_item('ale', include_location=False))

    def test_handle_item_result_drop(self):
        location = Location("test_room")
        npc = LivingNpc(name='test', gender='m', age=42, personality='')
        npc.init_inventory([self.drink])

        player = Player(name='player', gender='m')
        location.init_inventory([npc, player])
        item_result = json.loads('{"from":"test", "to":"", "item":"ale"}')

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