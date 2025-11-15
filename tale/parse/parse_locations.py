
from typing import Tuple
from tale import zone
from tale.base import Exit
from tale.coord import Coord
from tale.dungeon.dungeon import DungeonEntrance
from tale.load_items import load_item
from tale.parse_utils import location_from_json, opposite_direction


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
        
        if loc.get('items', None):
            for item in loc['items']:
                loaded_item = load_item(item)
                location.insert(loaded_item, None)

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

            if exit_to.get('type', '') == 'DungeonEntrance':
                exit1 = DungeonEntrance(directions=directions,
                                        target_location=to_loc,
                                        short_descr=exit_to['short_descr'], 
                                        long_descr=exit_to['long_descr'],
                                        enter_msg=exit_to.get('enter_msg', 'You enter a dungeon.'))
                exits.append(exit1)
                exit1.bind(from_loc)
                exit2 = Exit(directions=return_directions,
                             target_location=from_loc,
                             short_descr=exit_from['short_descr'], 
                             long_descr=exit_from['long_descr'])
                exits.append(exit2)
                exit2.bind(to_loc)

            else:
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