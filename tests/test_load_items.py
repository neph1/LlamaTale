import json
from tale import load_items, parse_utils, util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.story import MoneyType
from tale.wearable import WearLocation
from tale.zone import Zone
from tale import mud_context


class TestLoadItems:

    def test_load_items(self):
        zones = {}
        zones['Room 1'] = Location('Room 1', 'A small room perfect for testing')
        zones['House 1'] = Zone('House 1')
        zones['House 1'].add_location(Location('Room 2', 'Another testing room'))
        mud_context.driver = IFDriver()
        mud_context.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        items_json = parse_utils.load_json("tests/files/test_items.json")
        items = load_items.load_items(items_json, zones)
        assert(len(items) == 4)
        item = items['Box 1']
        assert(item.title == 'Box 1')
        assert(item.short_description == 'A small bejewelled box')
        assert(item.location == zones['Room 1'])
        item = items['Note 1']
        assert(item.text == 'This is a note')
        item = items['Money 1']
        assert(item.value == 100)
        assert(item.location == zones['House 1'].get_location('Room 2'))
        assert(items['Hoodie'])

    def test_load_generated_items(self):
        items_string_no_loc = '{"items": [{"name":"Woolly gloves", "type":"Wearable"}]}'
        items = json.loads(items_string_no_loc)
        assert(len(items) == 1)
        loaded_items = load_items.load_items(items['items'])
        assert(len(loaded_items) == 1)
        assert(loaded_items['Woolly gloves'])
        assert(loaded_items['Woolly gloves'].wear_location == WearLocation.TORSO)

        items_string_with_loc = '{"items": [{"name":"Woolly gloves", "type":"Wearable", "wear_location":"HANDS"}]}'

        items = json.loads(items_string_with_loc)
        assert(len(items) == 1)
        loaded_items = load_items.load_items(items['items'])
        assert(len(loaded_items) == 1)
        assert(loaded_items['Woolly gloves'])
        assert(loaded_items['Woolly gloves'].wear_location == WearLocation.HANDS)