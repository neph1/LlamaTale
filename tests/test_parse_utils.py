import pytest
from tale import mud_context, util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.story import GameMode, MoneyType
import tale.parse_utils as parse_utils


class TestParseUtils():
    
    def test_load_json(self):
        assert(parse_utils.load_json("tests/files/test.json"))
        
    def test_load_locations(self):
        room_json = parse_utils.load_json("tests/files/test_locations.json")
        locations, exits = parse_utils.load_locations(room_json)
        assert(locations['test house']['test room'])
        assert(locations['test house']['test room 2'])
        assert(exits[0].__repr__().startswith("(<base.Exit to 'test room 2'"))

    def test_load_items(self):
        locations = {}
        locations['Room 1'] = Location('Room 1', 'A small room perfect for testing')
        locations['House 1'] = {}
        locations['House 1']['Room 2'] = Location('Room 2', 'Another testing room')
        mud_context.driver = IFDriver()
        mud_context.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        items_json = parse_utils.load_json("tests/files/test_items.json")
        items = parse_utils.load_items(items_json, locations)
        assert(len(items) == 4)
        item = items['Box 1']
        assert(item.title == 'Box 1')
        assert(item.short_description == 'A small bejewelled box')
        assert(item.location == locations['Room 1'])
        item = items['Note 1']
        assert(item.text == 'This is a note')
        item = items['Money 1']
        assert(item.value == 100)
        assert(item.location == locations['House 1']['Room 2'])
        assert(items['Hoodie'])
        
    def test_load_npcs(self):
        locations = {}
        locations['Royal grotto'] = Location('Royal grotto', 'A small grotto, fit for a kobold king')
        npcs_json = parse_utils.load_json("tests/files/test_npcs.json")
        npcs = parse_utils.load_npcs(npcs_json, locations)
        assert(len(npcs) == 1)
        npc = npcs['Kobbo']
        assert(npc.title == 'Kobbo the King')
        assert(npc.location == locations['Royal grotto'])
        
    def test_load_story_config(self):
        config_json = parse_utils.load_json("tests/files/test_story_config.json")
        config = parse_utils.load_story_config(config_json)
        assert(config)
        assert(config.name == 'Test Story Config 1')
        assert(config.money_type == MoneyType.NOTHING)
        assert(config.supported_modes == {GameMode.IF})
        assert(config.zones == ["test zone"])
        
        
