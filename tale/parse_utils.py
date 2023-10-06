import random
from typing import Union
from tale import lang
from tale.base import Location, Exit, Item, Weapon, Wearable
from tale.coord import Coord
from tale.items.basic import Boxlike, Drink, Food, Health, Money, Note
from tale.npc_defs import StationaryMob, StationaryNpc
from tale.story import GameMode, MoneyType, TickMethod, StoryConfig
from tale.llm.llm_ext import LivingNpc
from tale.weapon_type import WeaponType
from tale.wearable import WearLocation
from tale.zone import Zone
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
    zone = Zone(json_file['name'], description=json_file['description'])
    zone.races = json_file['races']
    zone.items = json_file['items']
    zone.mood = json_file.get('mood', 0)
    zone.level = json_file.get('level', 1)
    zones[json_file['name']] = zone
    for loc in json_file['locations']:
        name = loc['name']
        location = location_from_json(loc)
        locations[name] = location
        zone.add_location(location)
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
    return Location(name=json_object['name'], descr=json_object.get('descr', ''))

def load_items(json_file: [], locations = {}) -> dict:
    """
        Loads and returns a dict of items from a supplied json dict
        Inserts into locations if supplied and has location
    """
    items = {}
    for item in json_file:
        item_type = item.get('type', 'Item')
        
        if item_type == 'Money':
            new_item = _init_money(item)
        elif item_type == 'Health':
            new_item = _init_health(item)
            new_item.healing_effect=item.get('value', 10)
        elif item_type == 'Food':
            new_item = _init_food(item)
            new_item.affect_fullness=item.get('value', 10)
            new_item.poisoned=item.get('poisoned', False)
        elif item_type == 'Weapon':
            new_item = _init_weapon(item)
        elif item_type == 'Drink':
            new_item = _init_drink(item)
            new_item.affect_thirst=item.get('value', 10)
            new_item.poisoned=item.get('poisoned', False)
        elif item_type == 'Container' or item_type == 'Boxlike':
            new_item = _init_boxlike(item)
        elif item_type == 'Wearable':
            new_item = _init_wearable(item)
        else:
            module = sys.modules['tale.items.basic']
            try:
                clazz = getattr(module, item_type)
            except AttributeError:
                try:
                    clazz = getattr(sys.modules['tale.base'], item_type)
                except AttributeError:
                    clazz = getattr(sys.modules['tale.base'], 'Item')
            new_item = clazz(name=item['name'], title=item.get('title', item['name']), descr=item.get('descr', ''), short_descr=item.get('short_descr', ''))
            if isinstance(new_item, Note):
                set_note(new_item, item)
        items[item['name']] = new_item
        if locations and item['location']: 
            _insert(new_item, locations, item['location'])
    return items

def load_npcs(json_file: [], locations = {}) -> dict:
    """
        Loads npcs and returns a dict from a supplied json dict
        May be custom classes, but be sure the class is available
        Inserts into locations if supplied and has location
    """
    npcs = {}
    for npc in json_file:
        npc_type = npc.get('type', 'Mob')
        if npc_type == 'ignore':
            continue
        if npc['name'].startswith('the') or npc['name'].startswith('The'):
                name = npc['name'].replace('the','').replace('The','').strip()
        else:
            name = npc['name']
        if 'npc' in npc_type.lower():
            
            new_npc = StationaryNpc(name=name, 
                                gender=lang.validate_gender_mf(npc.get('gender', 'm')[0]), 
                                race=npc.get('race', 'human').lower(), 
                                title=npc.get('title', name), 
                                descr=npc.get('descr', ''), 
                                short_descr=npc.get('short_descr', npc.get('description', '')), 
                                age=npc.get('age', 0), 
                                personality=npc.get('personality', ''), 
                                occupation=npc.get('occupation', ''))
            new_npc.aliases.add(name.split(' ')[0].lower())
            new_npc.stats.set_weapon_skill(WeaponType.UNARMED, random.randint(10, 30))
            new_npc.stats.level = npc.get('level', 1)
        elif npc_type == 'Mob':

            new_npc = StationaryMob(name=npc['name'], 
                                gender=lang.validate_gender_mf(npc.get('gender', 'm')[0]), 
                                race=npc.get('race', 'human').lower(), 
                                title=npc.get('title', npc['name']), 
                                descr=npc.get('descr', ''), 
                                short_descr=npc.get('short_descr', npc.get('description', '')))
            new_npc.aliases.add(name.split(' ')[0].lower())
            new_npc.stats.set_weapon_skill(WeaponType.UNARMED, random.randint(10, 30))
            new_npc.stats.level = npc.get('level', 1)
        # else:
        #     module = sys.modules['tale.items.basic']
        #     clazz = getattr(module, npc_type)
        #     new_npc = clazz(name=npc['name'], gender=npc['gender'], race=npc['race'], title=npc['title'], descr=npc['descr'], short_descr=npc['short_descr'], args=npc)
        if locations and npc['location']:
            _insert(new_npc, locations, npc['location'])
        npcs[name] = new_npc
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
    if len(location_parts) == 2:
        zone = locations.get(location_parts[0])
        loc = zone.get_location(location_parts[1])
    else:
        loc = locations.get(location)
    if loc:
        loc.insert(new_item, None)

def _init_money(item: dict):
    return Money(name=item['name'], 
                 value=item.get('value', 10), 
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''))

def _init_health(item: dict):
    return Health(name=item['name'], 
                 value=item.get('value', 10), 
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''),
                 descr=item.get('descr', ''),)

def _init_food(item: dict):
    return Food(name=item['name'], 
                 value=item.get('value', 10),
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''),
                 descr=item.get('descr', ''),)

def _init_weapon(item: dict):
    return Weapon(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    wc=item.get('wc', 1),
                    weapon_type=WeaponType[item.get('weapon_type', WeaponType.UNARMED.name)],
                    base_damage=item.get('base_damage', random.randint(1,3)),
                    bonus_damage=item.get('bonus_damage', 0),
                    weight=item.get('weight', 1),
                    value=item.get('value', 1),) 

def _init_drink(item: dict):
    return Drink(name=item['name'], 
                 value=item.get('value', 10),
                 title=item.get('title', item['name']), 
                 short_descr=item.get('short_descr', ''))

def _init_boxlike(item: dict):
    return Boxlike(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    weight=item.get('weight', 1),
                    value=item.get('value', 1))

def _init_wearable(item: dict):
    wear_location = None
    if WearLocation.has_value(item.get('wear_location', '')):
        wear_location = WearLocation[item['wear_location']]
    return Wearable(name=item['name'],
                    title=item.get('title', item['name']),
                    short_descr=item.get('short_descr', ''),
                    descr=item.get('descr', ''),
                    weight=item.get('weight', 1),
                    wear_location=wear_location,
                    value=item.get('value', 1))
    
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
    result = result.replace('```json', '') #.replace('\\"', '"').replace('"\\n"', '","').replace('\\n', '').replace('}\n{', '},{').replace('}{', '},{').replace('\\r', '').replace('\\t', '').replace('"{', '{').replace('}"', '}').replace('"\\', '"').replace('\\”', '"').replace('" "', '","').replace(':,',':').replace('},]', '}]').replace('},}', '}}')
    result = result.split('```')[0]
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
    occupied_directions = []
    for exit in location.exits.values():
        for dir in exit.names:
            occupied_directions.append(dir)
    for exit in json_result.get('exits', []):
        dir = exit.get('direction', '')
        if not dir:
            continue
        if dir not in occupied_directions:
            occupied_directions.append(dir)
        else:
            dir = _select_non_occupied_direction(occupied_directions)
            occupied_directions.append(dir)
            exit['direction'] = dir
            
    for exit in json_result.get('exits', []):
        if exit.get('name', None) is None:
            # With JSON grammar, exits are sometimes generated without name. So until that is fixed,
            # we'll do a work-around
            description = exit.get('description', 'short_descr')
            if description.startswith('A '):
                description.replace('A ', '')
            exit.name = description.split(' ')[:2]
        if exit['name'] != exit_location_name:
            # create location
            new_location = Location(exit['name'].replace('the ', '').replace('The ', ''))
            
            directions_to = [new_location.name]
            directions_from = [location.name]
            direction = exit.get('direction', '').lower()
            if direction:
                new_location.world_location = coordinates_from_direction(location.world_location, direction)
                directions_to.append(direction)
                directions_from.append(opposite_direction(direction))
            
            new_location.built = False
            new_location.generated = True
            from_description = f'To the {directions_from[1]} you see {location.name}.' if len(directions_from) > 1 else f'You see {location.name}.'
            exit_back = Exit(directions=directions_from, 
                    target_location=location, 
                    short_descr=from_description)
            new_location.add_exits([exit_back])

            to_description = 'To the {direction} you see {location}.'.format(direction=directions_to[1], location=exit.get('short_descr', 'description').lower()) if len(directions_to) > 1 else exit.get('short_descr', 'description')
            exit_to = Exit(directions=directions_to, 
                            target_location=new_location, 
                            short_descr=to_description, 
                            enter_msg=exit.get('enter_msg', ''))
            exits.append(exit_to)
            new_locations.append(new_location)
                
    return new_locations, exits

def _select_non_occupied_direction(occupied_directions: [str]):
    """ Selects a direction that is not occupied by an exit"""
    for dir in ['north', 'south', 'east', 'west']:
        if dir not in occupied_directions:
            return dir
        
def coordinates_from_direction(coord: Coord, direction: str) -> Coord:
    """ Returns coordinates for a new location based on the direction and location"""
    x = coord.x
    y = coord.y
    z = coord.z
    if direction == 'north':
        y = y + 1
    elif direction == 'south':
        y = y - 1
    elif direction == 'east':
        x = x + 1
    elif direction == 'west':
        x = x - 1
    elif direction == 'up':
        z = z + 1
    elif direction == 'down':
        z = z - 1
    elif direction == 'northeast':
        x = x + 1
        y = y + 1
    elif direction == 'northwest':
        x = x - 1
        y = y + 1
    elif direction == 'southeast':
        x = x + 1
        y = y - 1
    elif direction == 'southwest':
        x = x - 1
        y = y - 1
    return Coord(x=x, y=y, z=z)

def direction_from_coordinates(direction: Coord):
    """ Returns a direction based on the coordinates"""
    if direction.x == 1:
        return 'east'
    if direction.x == -1:
        return 'west'
    if direction.y == -1:
        return 'north'
    if direction.y == 1:
        return 'south'
    if direction.z == 1:
        return 'up'
    if direction.z == -1:
        return 'down'
    return None

def mood_string_from_int(mood: int):
    """ Returns a mood string based on the supplied int"""

    base_mood = 'friendly' if mood > 0 else 'hostile' if mood < 0 else 'neutral'
    
    if abs(mood) > 4:
        return f' uttermost {base_mood}'
    if abs(mood) > 3:
        return f' extremely {base_mood}'
    elif abs(mood) > 2:
        return f' very {base_mood}'
    elif abs(mood) > 1:
        return f' {base_mood}'
    else:
        return f' slightly {base_mood}'
    
def mood_string_to_int(mood: str):
    """ Returns an int from a mood description"""
    if mood.startswith('uttermost'):
        return 5 if mood.endswith('friendly') else -5
    if mood.startswith('extremely'):
        return 4 if mood.endswith('friendly') else -4
    if mood.startswith('very'):
        return 3 if mood.endswith('friendly') else -3
    if mood.startswith('friendly'):
        return 2
    if mood.startswith('hostile'):
        return -2
    if mood.startswith('neutral'):
        return 0
    return 1 if mood.endswith('friendly') else -1
    
def replace_items_with_world_items(items: list, world_items: dict) -> list:
    """ Replaces items in a list with world items"""
    new_items = []
    for item in items:
        if isinstance(item, str):
            if item.lower() in world_items.keys():
                new_items.append(world_items[item])
        elif isinstance(item, dict):
            new_items.append(item)
    return new_items

def replace_creature_with_world_creature(creatures: list, world_creatures: dict) -> list:
    """ Replaces creature with world creature"""
    new_creatures = []
    for creature in creatures:
        if isinstance(creature, str):
            if creature.lower() in world_creatures.keys():
                new_creatures.append(world_creatures[creature])
        else:
            new_creatures.append(creature)
    return new_creatures
