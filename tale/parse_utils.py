import random
from typing import Tuple
from tale import lang
from tale import zone
from tale.base import Location, Exit, Item, Stats, Weapon, Wearable
from tale.coord import Coord
from tale.item_spawner import ItemSpawner
from tale.items.basic import Boxlike, Drink, Food, Health, Money, Note
from tale.llm.LivingNpc import LivingNpc
from tale.npc_defs import StationaryMob, StationaryNpc
from tale.races import BodyType, UnarmedAttack
from tale.mob_spawner import MobSpawner
from tale.story import GameMode, MoneyType, TickMethod, StoryConfig
from tale.weapon_type import WeaponType
from tale.wearable import WearLocation
import json
import re
import sys
import os


def load_json(file_path: str):
    """
        Loads json from supplied file path
        Returns dict
        Fails silently and returns an empty dict if file doesn't exist
    """
    if not os.path.isfile(file_path):
        return {}
    
    with open(file_path) as f:
        return json.load(f, strict=False)

def load_locations(json_file: dict) -> Tuple[dict, list]:
    """
        Loads locations from supplied json file and generates exits connecting them
        Returns dict of locations, list of exits
    """
    locations = {}
    exits = []
    temp_exits = {}
    parsed_exits = []
    zones = {}
    zone1 = zone.from_json(json_file)
    zones[json_file['name']] = zone1
    for loc in json_file['locations']:
        name = loc['name']
        location = location_from_json(loc)
        if loc.get('world_location', None):
            location.world_location = Coord(loc['world_location'][0], loc['world_location'][1], loc['world_location'][2])
        locations[name] = location
        zone1.add_location(location)
        loc_exits = loc['exits']
        for loc_exit in loc_exits:
            temp_exits.setdefault(name,{})[loc_exit['name']] = loc_exit

    for from_name, exits_dict in temp_exits.items():
        from_loc = locations[from_name]
        for to_name, exit_to in exits_dict.items():
            exit_from = temp_exits[to_name][from_name]
            if [exit_from, exit_to] in parsed_exits or [exit_to, exit_from] in parsed_exits:
                continue
            to_loc = locations[to_name]
            
            directions = [to_name]
            
            return_directions = [from_name]
            direction = exit_to.get('direction', '')
            return_direction = exit_from.get('direction', '')
            # doing opposite since exit_to has direction
            if direction or return_direction:
                directions.append(direction or opposite_direction(return_direction))
                return_directions.append(opposite_direction(direction) or return_direction)

            exits.append(Exit.connect(from_loc=from_loc,
                                      directions=directions,
                                      short_descr=exit_to['short_descr'], 
                                      long_descr=exit_to['long_descr'],
                                      to_loc=to_loc,
                                      return_short_descr=exit_from['short_descr'], 
                                      return_long_descr=exit_from['long_descr'],
                                      return_directions=return_directions))
            parsed_exits.append([exit_from, exit_to])
    return zones, exits

def location_from_json(json_object: dict):
    location = Location(name=json_object['name'], descr=json_object.get('descr', ''))
    location.built = json_object.get('built', True)
    return location

def load_items(json_items: list, locations = {}) -> dict:
    """
        Loads and returns a dict of items from a supplied json dict
        Inserts into locations if supplied and has location
    """
    items = {}
    for item in json_items:
        new_item = load_item(item)
        items[item['name']] = new_item
        if locations and item['location']: 
            _insert(new_item, locations, item['location'])
    return items

def load_item(item: dict):
    item_type = item.get('type', 'Item')
        
    if item_type == 'Money':
        new_item = _init_money(item)
    elif item_type == 'Health':
        new_item = _init_health(item)
        new_item.healing_effect=item.get('effect', 10)
    elif item_type == 'Food':
        new_item = _init_food(item)
        new_item.affect_fullness=item.get('effect', 10)
        new_item.poisoned=item.get('poisoned', False)
    elif item_type == 'Weapon':
        new_item = _init_weapon(item)
    elif item_type == 'Drink':
        new_item = _init_drink(item)
        new_item.affect_thirst=item.get('effect', 10)
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
    return new_item

def load_npcs(json_npcs: list, locations = {}) -> dict:
    """
        Loads npcs and returns a dict from a supplied json dict
        May be custom classes, but be sure the class is available
        Inserts into locations if supplied and has location
    """
    npcs = {}
    for npc in json_npcs: # type dict
        npc_type = npc.get('type', 'Mob')
        if npc_type == 'ignore':
            continue
        if npc['name'].startswith('the') or npc['name'].startswith('The'):
                name = npc['name'].replace('the','').replace('The','').strip()
        else:
            name = npc['name']
        new_npc = load_npc(npc, name, npc_type)

        if locations and npc['location']:
            _insert(new_npc, locations, npc['location'])

        npcs[name] = new_npc
    return npcs

def load_npc(npc: dict, name: str = None, npc_type: str = 'Mob'):
    race = None
    if npc.get('stats', None):
        race = npc['stats'].get('race', None)
    if 'npc' in npc_type.lower():
        new_npc = StationaryNpc(name=name, 
                            gender=lang.validate_gender(npc.get('gender', 'm')), 
                            race=race, 
                            title=npc.get('title', name), 
                            descr=npc.get('descr', ''), 
                            short_descr=npc.get('short_descr', npc.get('description', '')), 
                            age=npc.get('age', 0), 
                            personality=npc.get('personality', ''), 
                            occupation=npc.get('occupation', ''))
        new_npc.aliases.add(name.split(' ')[0].lower())
        new_npc.stats.set_weapon_skill(WeaponType.UNARMED, random.randint(10, 30))
        new_npc.stats.level = npc.get('level', 1)


    else:

        new_npc = StationaryMob(name=npc['name'], 
                            gender=lang.validate_gender(npc.get('gender', 'm')), 
                            race=race, 
                            title=npc.get('title', npc['name']), 
                            descr=npc.get('descr', ''), 
                            short_descr=npc.get('short_descr', npc.get('description', '')))
        new_npc.aliases.add(name.split(' ')[0].lower())
        new_npc.stats.set_weapon_skill(WeaponType.UNARMED, random.randint(10, 30))
        new_npc.stats.level = npc.get('level', 1)

    if npc.get('stats', None):
        new_npc.stats = load_stats(npc['stats'])

    if npc.get('memory', None):
        new_npc.load_memory(npc['memory'])

    new_npc.autonomous = npc.get('autonomous', False)
    new_npc.aggressive = npc.get('aggressive', False)
    return new_npc

def load_story_config(json_file: dict):
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
    config.context = json_file.get('context', '')
    config.type = json_file.get('type', '')
    config.world_info = json_file.get('world_info', '')
    config.world_mood = json_file.get('world_mood', config.world_mood)
    config.custom_resources = json_file.get('custom_resources', config.custom_resources)
    config.image_gen = json_file.get('image_gen', config.image_gen)
    return config

def save_story_config(config: StoryConfig) -> dict:
    json_file = {}
    json_file['name'] = config.name
    json_file['author'] = config.author
    json_file['author_address'] = config.author_address
    json_file['version'] = config.version
    json_file['supported_modes'] = []
    for mode in config.supported_modes:
        json_file['supported_modes'].append(mode.name)
    json_file['player_name'] = config.player_name
    json_file['player_gender'] = config.player_gender
    json_file['player_race'] = config.player_race
    json_file['player_money'] = config.player_money
    json_file['money_type'] = config.money_type.name
    json_file['server_tick_method'] = config.server_tick_method.name
    json_file['server_tick_time'] = config.server_tick_time
    json_file['gametime_to_realtime'] = config.gametime_to_realtime
    json_file['display_gametime'] = config.display_gametime
    json_file['startlocation_player'] = config.startlocation_player
    json_file['startlocation_wizard'] = config.startlocation_wizard
    json_file['zones'] = config.zones
    json_file['server_mode'] = config.server_mode.name
    json_file['npcs'] = config.npcs
    json_file['items'] = config.items
    json_file['context'] = config.context
    json_file['type'] = config.type
    json_file['world_info'] = config.world_info
    json_file['world_mood'] = config.world_mood
    json_file['context'] = config.context
    return json_file


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
    return Money(item['name'], 
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
    note.text = item.get('text', '')

def remove_special_chars(message: str):
    re.sub('[^A-Za-z0-9 .,_\-\'\"]+', '', message)
    return message
        
def trim_response(message: str):
    """ Removes special chars from response"""
    if not message:
        return ''
    enders = [' ', '!', '?', '`', '*', '"', ')', '}', '`', ']', '\n']
    starters = [' ', '`', '*', '"', '(', '{', '`', '[', '\n']

    while message and message[0] in starters:
        message = message[1:]

    while message and message[-1] in enders:
        message = message[:-1]
    
    return message

def sanitize_json(result: str) -> str:
    """ Removes special chars from json string. Some common, and some 'creative' ones. """
    if result is None:
        return ''
    result = result.strip()
    result = result.replace('```json', '') #.replace('\\"', '"').replace('"\\n"', '","').replace('\\n', '').replace('}\n{', '},{').replace('}{', '},{').replace('\\r', '').replace('\\t', '').replace('"{', '{').replace('}"', '}').replace('"\\', '"').replace('\\”', '"').replace('" "', '","').replace(':,',':').replace('},]', '}]').replace('},}', '}}')
    result = result.split('```')[0]
    result = result.replace('False', 'false').replace('True', 'true').replace('None', 'null')
    if not result.endswith('}') and not result.endswith(']'):
        result = result + '}'
    #print('sanitized json: ' + result)
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

def parse_generated_exits(exits: list, exit_location_name: str, location: Location, neighbor_locations: dict = {}):
    """
        Parses a json dict for new locations and exits
        Returns list of new locations and exits
    """
    new_locations = []
    new_exits = []
    occupied_directions = []
    for exit in location.exits.values():
        for dir in exit.names:
            occupied_directions.append(dir)
    for exit in exits:
        dir = exit.get('direction', '')
        if not dir:
            continue
        if dir not in occupied_directions:
            occupied_directions.append(dir)
        else:
            dir = _select_non_occupied_direction(occupied_directions)
            occupied_directions.append(dir)
            exit['direction'] = dir
            
    for exit in exits:
        if exit.get('name', None) is None:
            # With JSON grammar, exits are sometimes generated without name. So until that is fixed,
            # we'll do a work-around
            description = exit.get('description', 'short_descr')
            if description.startswith('A '):
                description.replace('A ', '')
            exit.name = description.split(' ')[:2]
        if exit.get('direction', '') in neighbor_locations.keys():
            # connect to existing location. No new location needed
            direction = exit['direction']
            neighbor = neighbor_locations[direction] # type: Location
            new_exit = Exit(directions=[neighbor.name, direction], target_location=neighbor, short_descr= f'To the {direction} you see {neighbor.name}.')
            connect_location_to_exit(neighbor, location, new_exit)
            new_exits.append(new_exit)
        elif exit['name'] != exit_location_name:
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
            exit_description = exit.get('short_descr', new_location.name).lower()
            to_description = 'To the {direction} you see {exit_description}'.format(direction=directions_to[1], exit_description=exit_description)  if len(directions_to) > 1 else f'You see {exit_description}.'
            exit_to = Exit(directions=directions_to, 
                            target_location=new_location, 
                            short_descr=to_description, 
                            enter_msg=exit.get('enter_msg', ''))
            new_exits.append(exit_to)
            new_locations.append(new_location)
                
    return new_locations, new_exits

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
    return Coord(x, y, z)

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

    if mood == 0:
        return ' neutral'
    
    base_mood = 'friendly' if mood > 0 else 'hostile'
    
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
    
def replace_items_with_world_items(items: list, world_items: list) -> list:
    """ Replaces items in a list with world items"""
    new_items = []
    for item in items:
        if isinstance(item, str):
            for world_item in world_items:
                if item.lower() == world_item['name'].lower():
                    new_items.append(world_item)
        elif isinstance(item, dict):
            new_items.append(item)
    return new_items

def replace_creature_with_world_creature(creatures: list, world_creatures: list) -> list:
    """ Replaces creature with world creature"""
    new_creatures = []
    for creature in creatures:
        if isinstance(creature, str):
            for world_creature in world_creatures:
                if creature.lower() == world_creature['name'].lower():
                    new_creatures.append(world_creature)
        else:
            new_creatures.append(creature)
    return new_creatures

def save_npcs(creatures: []) -> dict:
    npcs = {}
    for npc in creatures: # type: Living
        stored_npc = {}
        stored_npc['location'] = npc.location.name
        stored_npc['name'] = npc.name.capitalize()
        stored_npc['title'] = npc.title
        stored_npc['aliases'] = list(npc.aliases)
        stored_npc['short_descr'] = npc.short_description
        stored_npc['descr'] = npc.description
        stored_npc['personality'] = npc.personality
        stored_npc['occupation'] = npc.occupation
        stored_npc['age'] = npc.age

        if isinstance(npc, StationaryMob):
            stored_npc['type'] = 'Npc'
            
        elif isinstance(npc, StationaryNpc):
            stored_npc['type'] = 'Mob'
        if npc.stats:
            stored_npc['race'] = npc.stats.race
            stored_npc['gender'] = lang.gender_string(npc.gender)
            stored_npc['title'] = npc.title
            stored_npc['descr'] = npc.description
            stored_npc['short_descr'] = npc.short_description
            stored_npc['level'] = npc.stats.level
            stored_npc['stats'] = save_stats(npc.stats)

        if isinstance(npc, LivingNpc):
            stored_npc['memory'] = npc.dump_memory()
        
        npcs[npc.name] = stored_npc
    return npcs

def save_stats(stats: Stats) -> dict:
    json_stats = {}
    json_stats['ac'] = stats.ac
    json_stats['hp'] = stats.hp
    json_stats['max_hp'] = stats.max_hp
    json_stats['level'] = stats.level
    json_stats['weapon_skills'] = save_weaponskills(stats.weapon_skills)
    json_stats['gender'] = stats.gender = 'n'
    json_stats['alignment'] = stats.alignment
    json_stats['weight'] = stats.weight
    json_stats['level'] = stats.level
    json_stats['xp'] = stats.xp
    json_stats['strength'] = stats.strength
    json_stats['dexterity'] = stats.dexterity
    json_stats['unarmed_attack'] = stats.unarmed_attack.name.upper()
    json_stats['race'] = stats.race
    json_stats['bodytype'] = stats.bodytype.name.upper()
    return json_stats


def load_stats(json_stats: dict) -> Stats:
    stats = Stats()
    stats.ac = json_stats.get('ac')
    stats.hp = json_stats.get('hp')
    stats.max_hp = json_stats.get('max_hp')
    stats.level = json_stats.get('level')
    stats.gender = json_stats.get('gender')
    stats.alignment = json_stats.get('alignment')
    stats.weight = json_stats.get('weight')
    stats.level = json_stats.get('level')
    stats.xp = json_stats.get('xp')
    stats.strength = json_stats.get('strength')
    stats.dexterity = json_stats.get('dexterity')
    stats.race = json_stats.get('race', 'human')
    if json_stats.get('bodytype'):
        stats.bodytype = BodyType[json_stats['bodytype'].upper()]
    if json_stats.get('unarmed_attack'):
        stats.unarmed_attack = Weapon(UnarmedAttack[json_stats['unarmed_attack'].upper()], WeaponType.UNARMED)
    if json_stats.get('weapon_skills'):
        json_skills = json_stats['weapon_skills']
        stats.weapon_skills = {}
        for skill in json_skills.keys():
            int_skill = int(skill)
            stats.weapon_skills[WeaponType(int_skill)] = json_skills[skill]
    return stats
    
def save_items(items: [Item]) -> dict:
    json_items = {}
    for item in items: 
        json_item = item.to_dict()
        item_type = item.__class__.__name__
        json_item['type'] = item_type
        
        if item_type == 'Food' or item_type == 'Drink':
            json_item['poisoned'] = item.poisoned
        json_items[item.name] = json_item
    return json_items

def save_locations(locations: [Location]) -> dict:
    json_locations = []
    for location in locations: # type: Location
        json_location = {}
        json_location['name'] = location.name.capitalize()
        json_location['descr'] = location.description
        json_location['short_descr'] = location.short_description
        json_location['exits'] = []
        json_location['world_location'] = location.world_location.as_tuple()
        json_location['built'] = location.built
        exits = []
        for exit in location.exits.values(): # type: Exit
            json_exit = {}
            json_exit['name'] = exit.name.capitalize()
            json_exit['short_descr'] = exit.short_description
            json_exit['long_descr'] = exit.description
            json_exit['direction'] = next(iter(exit.aliases)) if exit.aliases else '' # not pretty, but works
            exits.append(json_exit)
        json_location['exits'] = exits
        json_locations.append(json_location)
    return json_locations

def save_weaponskills(weaponskills: dict) -> dict:
    json_skills = {}
    for skill in weaponskills.keys():
        json_skills[skill.value] = weaponskills[skill]
    return json_skills

def load_mob_spawners(json_spawners: list, locations: dict, creatures: list, world_items: list) -> list:
    spawners = []
    for spawner in json_spawners:
        location = locations[spawner['location']]
        if not location:
            print(f"Location {spawner['location']} not found")
            continue
        mob_type = spawner['mob_type']
        mob = None
        for creature in creatures:
            if creature['name'] == mob_type:
                mob = creature
                break
        if not mob:
            print(f"Mob {mob_type} not in catalogue")
            continue
        drop_items = spawner.get('drop_items', [])
        loaded_drop_items = []
        item_probabilities = []
        if drop_items:
            loaded_drop_items = []
            for item in drop_items:
                for world_item in world_items:
                    if item.lower() == world_item['name'].lower():
                        loaded_drop_items.append(load_item(world_item))
            item_probabilities = spawner.get('drop_item_probabilities', [])
                
        mob_spawner = MobSpawner(mob, location, spawner['spawn_rate'], spawner['spawn_limit'], drop_items=loaded_drop_items, drop_item_probabilities=item_probabilities)
        spawners.append(mob_spawner)
    return spawners

def load_item_spawners(json_spawners: list, zones: dict, world_items: list) -> list:
    spawners = []
    for spawner in json_spawners:
        zone = zones[spawner['zone']]
        if not zone:
            print(f"Zone {spawner['zone']} not found")
            continue
        items = spawner['items']
        
        loaded_items = []
        
        for item in items:
            world_item = None
            for world_item in world_items:
                if item.lower() == world_item['name'].lower():
                    loaded_items.append(world_item)
                    break
            if not world_item:
                print(f"Item {item} not in catalogue")
            continue
        container = None
        if spawner.get('container', None):
            container = world_items[spawner['container']]
        item_spawner = ItemSpawner(zone=zone, spawn_rate=spawner['spawn_rate'], container=container, max_items=spawner['max_items'], items=loaded_items, item_probabilities=spawner['item_probabilities'])
        spawners.append(item_spawner)
    return spawners