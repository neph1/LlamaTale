import pathlib
import sys
from typing import Optional, Generator

import tale
from tale import parse_utils
from tale.base import Exit, Location
from tale.driver import Driver
from tale.dungeon.dungeon_generator import ItemPopulator, Layout, LayoutGenerator, MobPopulator
from tale.json_story import JsonStory
from tale.main import run_from_cmdline
from tale.story import *
from tale.zone import Zone

class Story(JsonStory):

    driver = None  # type: Driver

    def __init__(self, layout_generator = LayoutGenerator(), mob_populator = MobPopulator(), item_populator = ItemPopulator()) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))
        self.layout_generator = layout_generator
        self.mob_populator = mob_populator
        self.item_populator = item_populator
        self.max_depth = 10
        

    def init(self, driver: Driver) -> None:
        super(Story, self).init(driver)

    def add_zone(self, zone: Zone) -> bool:
        first_zone = len(self._zones.values()) == 0
        if super(Story, self).add_zone(zone):
            zone.size_z = 1
            layout = self.layout_generator.generate()

            rooms = self._prepare_locations(layout=layout, first_zone=first_zone)

            self._describe_rooms(zone=zone, layout=layout, rooms=rooms)
            
            self._connect_locations(layout=layout)

            mob_spawners = [self.mob_populator.populate(zone=zone, layout=layout)]
            for mob_spawner in mob_spawners:
                self.world.add_mob_spawner(mob_spawner)

            item_spawners = [self.item_populator.populate(zone=zone, story=self)]
            for item_spawner in item_spawners:
                self.world.add_item_spawner(item_spawner)
                
            return True
        return False
    
    def _describe_rooms(self, zone: Zone, layout: Layout, rooms: list):
        for i in range(3):
            described_rooms = self.driver.llm_util.generate_dungeon_locations(zone_info=zone.get_info(), locations=rooms)
            if described_rooms and len(described_rooms) == len(rooms):
                break
        if isinstance(described_rooms, dict):
            described_rooms = list(described_rooms.values())
        for room in described_rooms:
            i = 1
            if zone.get_location(room['name']):
                # ensure unique names
                room['name'] = f'{room["name"]}({i})'
                i += 1
            location = Location(name=room['name'], descr=room['description'])
            location.world_location = list(layout.cells.values())[room['index']].coord
            zone.add_location(location=location)
            self.add_location(zone=zone.name, location=location)
        return described_rooms

    
    def _prepare_locations(self, layout: Layout, first_zone: bool = False) -> list:
        index = 0
        rooms = []
        for cell in list(layout.cells.values()):
            if cell.is_entrance:
                room_string = f'{{"index": {index}, "name":{"Entrance to dungeon" if first_zone else "Room with staircase leading up"}}}'
            elif cell.is_exit:
                room_string = f'{{"index": {index}, "name": "Room with staircase leading down"}}'
            elif cell.is_room:
                room_string = f'{{"index": {index}, "name": ""}}'
            else:
                room_string = f'{{"index": {index}, "name": "Hallway", "description": "A hallway"}}'
            rooms.append(room_string)
            index += 1
        return rooms
    
    def _connect_locations(self, layout: Layout) -> None:
        leaf_cells = [cell for cell in layout.cells.values() if cell.leaf]
        cells_to_parse = leaf_cells.copy()
        while len(cells_to_parse) > 0:
            cell = cells_to_parse[0]
            parent = cell.parent
            if not parent:
                cells_to_parse.remove(cell)
                continue
            cell_location = self.world._grid.get(cell.coord.as_tuple(), None)
            parent_location = self.world._grid.get(parent.as_tuple(), None)
            if cell_location.exits.get(parent_location.name, None):
                cells_to_parse.remove(cell)
                continue
            Exit.connect(cell_location, parent_location.name, '', None, parent_location, cell_location.name, '', None)
            cells_to_parse.append(layout.cells[parent.as_tuple()])
            cells_to_parse.remove(cell)

if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)