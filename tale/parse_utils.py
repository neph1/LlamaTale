from tale.base import Location, Exit, Item, Living
from tale.items.basic import Money, Note
from tale.story import GameMode, MoneyType, TickMethod, StoryConfig
import collections
import json
import sys

def load_json(file_path: str):
    with open(file_path) as f:
        return json.load(f)

def load_locations(json_file: dict):
    """
        Loads locations from supplied json file and generates exits connecting them
        Returns dict of locations, list of exits
    """
    locations = {}
    exits = []
    temp_exits = {}
    parsed_exits = []
    zone = {}
    zone[json_file['name']] = locations
    for loc in json_file['rooms']:
        name = loc['name']
        locations[name] = Location(name, loc['descr'])
        loc_exits = loc['exits']
        for loc_exit in loc_exits:
            temp_exits.setdefault(name,{})[loc_exit['name']] = loc_exit
    for ex in temp_exits:
        from_name = ex
        loc_one = locations[from_name]
        for to_name, value in temp_exits[from_name].items():
            exit_to = value
            exit_from = temp_exits[to_name][from_name]
            if [exit_from, exit_to] in parsed_exits or [exit_to, exit_from] in parsed_exits:
                continue
            loc_two = locations[to_name]
            exits.append(Exit.connect(loc_one, to_name, exit_to['short_desc'], exit_to['long_desc'],
                 loc_two, from_name, exit_from['short_desc'], exit_from['long_desc']))
            parsed_exits.append([exit_from, exit_to])
    return zone, exits


def load_items(json_file: dict, locations = {}):
    """
        Loads and returns a dict of items from a supplied json dict
        Inserts into locations if supplied and has location
    """
    items = {}
    for item in json_file:
        item_type = item['type']
        if item_type == 'Money':
            new_item = init_money(item)
        else:
            module = sys.modules['tale.items.basic']
            clazz = getattr(module, item_type)
            new_item = clazz(name=item['name'], title=item['title'], descr=item['descr'], short_descr=item['short_descr'])
            if isinstance(new_item, Note):
                set_note(new_item, item)
        items[item['name']] = new_item
        if locations and item['location']:
            _insert(new_item, locations, item['location'])
    return items

def load_npcs(json_file: dict, locations = {}):
    """
        Loads npcs and returns a dict from a supplied json dict
        May be custom classes, but be sure the class is available
        Inserts into locations if supplied and has location
    """
    npcs = {}
    for npc in json_file:
        npc_type = npc['type']
        if npc_type == 'Living':
            new_npc = Living(name=npc['name'], gender=npc['gender'], race=npc['race'], title=npc['title'], descr=npc['descr'], short_descr=npc['short_descr'])
        else:
            module = sys.modules['tale.items.basic']
            clazz = getattr(npc_type)
            new_npc = clazz(name=npc['name'], gender=npc['gender'], race=npc['race'], title=npc['title'], descr=npc['descr'], short_descr=npc['short_descr'], args=npc)
        if locations and npc['location']:
            _insert(new_npc, locations, npc['location'])
        npcs[npc['name']] = new_npc
    return npcs

def load_story_config(json_file: dict):
    if json_file['type'] == 'StoryConfig':
        config = StoryConfig()
        config.name = json_file['name']
        config.author = json_file['author']
        config.author_address = json_file['author_address']
        config.version = "1.0"
        supported_modes = []
        for mode in json_file['supported_modes']:
            supported_modes.append(GameMode[mode])
        config.supported_modes = set(supported_modes)
        config.player_name = json_file['player_name']
        config.player_gender = json_file['player_gender']
        config.player_race = json_file['player_race']
        config.playable_races = {"human"}
        config.player_money = json_file['player_money']
        config.money_type = MoneyType[json_file['money_type']]
        config.server_tick_method = TickMethod[json_file['server_tick_method']]
        config.server_tick_time = json_file['server_tick_time']
        config.gametime_to_realtime = json_file['gametime_to_realtime']
        config.display_gametime = json_file['display_gametime']
        config.startlocation_player = json_file['startlocation_player']
        config.startlocation_wizard = json_file['startlocation_wizard']
        config.zones = json_file['zones']
        config.server_mode = GameMode[json_file['server_mode']]
        config.npcs = json_file.get('npcs', '')
        config.items = json_file.get('items', '')
        return config


def _insert(new_item: Item, locations, location: str):
    location_parts = location.split('.')
    for part in location_parts:
        location = locations[part]
        locations = location
    if location:
        location.insert(new_item, None)

def init_money(item: dict):
    return Money(name=item['name'], value=item['value'], title=item['title'], short_descr=item['short_descr'])
    
def set_note(note: Note, item: dict):
    note.text = item['text']
