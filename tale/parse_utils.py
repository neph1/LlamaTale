from typing import Union
from tale.base import Location, Exit, Item, Living
from tale.items.basic import Money, Note
from tale.story import GameMode, MoneyType, TickMethod, StoryConfig
from tale.llm_ext import LivingNpc
import json
import re
import sys

def load_json(file_path: str):
    with open(file_path) as f:
        return json.load(f, strict=False)

def load_locations(json_file: dict):
    """
        Loads locations from supplied json file and generates exits connecting them
        Returns dict of locations, list of exits
    """
    locations = {}
    exits = []
    temp_exits = {}
    parsed_exits = []
    zones = {}
    zone = {}
    zone['name'] = json_file['name']
    zone['description'] = json_file['description']
    zone['races'] = json_file['races']
    zone['items'] = json_file['items']
    zone['locations'] = locations
    zones[json_file['name']] = zone
    for loc in json_file['rooms']:
        name = loc['name']
        locations[name] = location_from_json(loc)
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
    return zones, exits


def location_from_json(json_object: dict):
    return Location(name=json_object['name'], descr=json_object['descr'])

def load_items(json_file: [], locations = {}):
    """
        Loads and returns a dict of items from a supplied json dict
        Inserts into locations if supplied and has location
    """
    # TODO: add support for wearables
    items = {}
    for item in json_file:
        item_type = item.get('type', 'Item')
        
        if item_type == 'Money':
            new_item = init_money(item)
        else:
            module = sys.modules['tale.items.basic']
            try:
                clazz = getattr(module, item_type)
            except AttributeError:
                if item_type == 'Wearable':
                    clazz = getattr(sys.modules['tale.base'], 'Wearable')
                elif item_type == 'Weapon':
                    clazz = getattr(sys.modules['tale.base'], 'Weapon')
                else:
                    clazz = getattr(sys.modules['tale.base'], 'Item')
            new_item = clazz(name=item['name'], title=item.get('title', item['name']), descr=item.get('descr', ''), short_descr=item.get('short_descr', ''))
            if isinstance(new_item, Note):
                set_note(new_item, item)
        items[item['name']] = new_item
        if locations and item['location']: 
            _insert(new_item, locations, item['location'])
    return items

def load_npcs(json_file: [], locations = {}):
    """
        Loads npcs and returns a dict from a supplied json dict
        May be custom classes, but be sure the class is available
        Inserts into locations if supplied and has location
    """
    npcs = {}
    for npc in json_file:
        npc_type = npc.get('type', 'LivingNpc')
        if npc_type == 'LivingNpc':
            new_npc = LivingNpc(name=npc['name'], 
                                gender=npc.get('gender'.lower(), 'm'), 
                                race=npc.get('race'.lower(), 'human'), 
                                title=npc.get('title', ''), 
                                descr=npc.get('descr', ''), 
                                short_descr=npc.get('short_descr', npc.get('description', '')), 
                                age=npc.get('age', 0), 
                                personality=npc.get('personality', ''), 
                                occupation=npc.get('occupation', ''))
        # else:
        #     module = sys.modules['tale.items.basic']
        #     clazz = getattr(module, npc_type)
        #     new_npc = clazz(name=npc['name'], gender=npc['gender'], race=npc['race'], title=npc['title'], descr=npc['descr'], short_descr=npc['short_descr'], args=npc)
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
        if 'locations' in location:
            locations = location['locations']
    if location:
        location.insert(new_item, None)

def init_money(item: dict):
    return Money(name=item['name'], value=item['value'], title=item['title'], short_descr=item['short_descr'])
    
def set_note(note: Note, item: dict):
    note.text = item['text']

def remove_special_chars(message: str):
    re.sub('[^A-Za-z0-9 .,_\-\'\"]+', '', message)
    return message
        
def trim_response(message: str):
    enders = ['.', '!', '?', '`', '*', '"', ')', '}', '`', ']']
    lastChar = 0
    for c in enders:
        last = message.rfind(c)
        if last > lastChar:
            lastChar = last
    return message[:lastChar+1]

def sanitize_json(result: str):
    """ Removes special chars from json string. Some common, and some 'creative' ones. """
    # .replace('}}', '}')
    # .replace('""', '"')
    result = result.replace('\\"', '"').replace('"\\n"', '","').replace('\\n', '').replace('}\n{', '},{').replace('}{', '},{').replace('\\r', '').replace('\\t', '').replace('"{', '{').replace('}"', '}').replace('"\\', '"').replace('\\”', '"').replace('" "', '","').replace(':,',':')
    print('sanitized json: ' + result)
    return result

def _convert_name(name: str):
    return name.lower().replace(' ', '_')

# These are related to LLM generated content

def connect_location_to_exit(location_to: Location, location_from: Location, exit_from: Exit):
    """ Creates an exit back from location_to to location_from
        Will try to use the opposite direction, if possible"""
    try:
        exit_back = location_to.exits[location_from.name]
    except KeyError:
        directions = [location_from.name]
        for dir in [exit_from.name, exit_from.aliases]:
            opposite = opposite_direction(dir)
            if opposite != None:
                directions.append(opposite)
                break

        exit_back = Exit(directions=directions, 
                         target_location=location_from, 
                         short_descr=f'You can see {location_from.name}') # need exit descs
    location_to.add_exits([exit_back])

def opposite_direction(direction: str):
    """ Returns the opposite direction of the supplied direction. Thanks copilot!"""
    if direction == 'north':
        return 'south'
    if direction == 'south':
        return 'north'
    if direction == 'east':
        return 'west'
    if direction == 'west':
        return 'east'
    if direction == 'up':
        return 'down'
    if direction == 'down':
        return 'up'
    if direction == 'in':
        return 'out'
    if direction == 'out':
        return 'in'
    return None

def parse_generated_exits(json_result: dict, exit_location_name: str, location: Location):
    """
        Parses a json dict for new locations and exits
        Returns list of new locations and exits
    """
    new_locations = []
    exits = []
    for exit in json_result['exits']:
        if exit['name'] != exit_location_name:
            # create location
            new_location = Location(exit['name'].lower())
            new_location.built = False
            new_location.generated = True
            exit_back = Exit(directions=location.name, 
                    target_location=location, 
                    short_descr=f'You can see {location.name}') # need exit descs
            new_location.add_exits([exit_back])
            exit_to = Exit(directions=new_location.name, 
                            target_location=new_location, 
                            short_descr=exit.get('short_descr', ''), 
                            enter_msg=exit.get('enter_msg', ''))
            exits.append(exit_to)
            new_locations.append(new_location)
    return new_locations, exits

