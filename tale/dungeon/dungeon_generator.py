

import random
from tale.coord import Coord
from tale.item_spawner import ItemSpawner
from tale.llm.llm_ext import DynamicStory
from tale.mob_spawner import MobSpawner
from tale.zone import Zone


class LayoutGenerator():

    def __init__(self, start_coord: Coord = Coord(0,0,0), seed: int = None):
        self.max_size = 10
        self.min_rooms = 10
        self.max_locked_doors = 1
        self.start_coord = start_coord
        self.layout = Layout(self.start_coord)
        self.unvisited = [] # type: list[Coord]
        if seed:
            random.seed(seed)

    def generate(self) -> 'Layout':

        
        start_location = Cell()
        start_location.is_room = True
        start_location.visited = False
        self.layout.cells[self.start_coord.as_tuple()] = start_location
        self.unvisited.append(self.start_coord)
        start_cell = self.generate_cell(coord=self.start_coord)
        start_cell.is_entrance = True
        while len(self.unvisited) > 0:
            coord = self.unvisited.pop()
            self.generate_room(coord)

        self.set_exit()
        return self.layout
        

    def generate_room(self, coord: Coord):
        cell = self.get_cell(coord) # type: Cell
        parent = cell.parent
        cell.visited = True

        # add neighbors
        openings = self.num_neighbors_to_add(coord)

        if openings == 0:
            cell.leaf = True
            return

        if coord.x % 2 == 1 or coord.y % 2 == 1:
            direction = coord.subtract(parent)
            new_cell = self.get_cell(coord.add(direction))
            if new_cell is None:
                self.generate_cell(coord=coord.add(direction), parent=coord)
            return
        directions = [Coord(1,0,0), Coord(-1,0,0), Coord(0,1,0), Coord(0,-1,0)]
        while openings > 0:
            if len(directions) == 0:
                print('openings left but no directions', coord, openings)
                return
            direction = random.choice(directions)
            new_coord = coord.add(direction)
            if self.get_cell(new_coord) is None:
                self.generate_cell(coord=coord.add(direction), parent=coord)
                openings -= 1
            directions.remove(direction)

    def generate_cell(self, coord: Coord, parent: Coord = None) -> 'Cell':
        new_cell = Cell(coord=coord, parent=parent)
        new_cell.visited = False
        new_cell.is_room = random.random() < 0.33
        self.layout.cells[coord.as_tuple()] = new_cell
        self.unvisited.append(coord)
        if random.random() < 0.25:
            door = Door(coord, parent)
            self.layout.doors.append(door)
            if self.max_locked_doors > 0 and random.random() < 0.15:
                door.locked = True
                self.place_key(door)
                self.max_locked_doors -= 1
        return new_cell

    def place_key(self, door: 'Door') -> 'Key':
        possible_cells = []
        leaves = self.layout.get_leaves()
        for leaf in leaves:
            coord = leaf.coord
            visited_cells = []
            while coord is not self.start_coord:
                visited_cells.append(coord)
                coord = self.get_cell(coord).parent
                if coord is None:
                    break
                if coord == door.coord:
                    visited_cells.clear()
            possible_cells.extend(visited_cells)
        if len(possible_cells) == 0:
            door.locked = False
        key_coord = random.choice(possible_cells)
        key = Key(key_coord, door)
        self.layout.keys.append(key)
        return key

    def num_neighbors_to_add(self, coord: Coord) -> int:
        min_neighbors = 0 if len(self.layout.cells) > self.min_rooms else 1
        if coord.x % 2 == 1 or coord.y % 2 == 1:
            return random.randint(min_neighbors, 1)
        cell_factor = len(self.layout.cells) / self.min_rooms
        if cell_factor < 1:
            max_neighbors = 3 
        elif cell_factor < 1.5:
            max_neighbors = 2
        elif cell_factor < 2:
            max_neighbors = 1
        else:
            return 0
        return random.randint(min_neighbors, max_neighbors)

    def get_cell(self, coord: Coord):
        return self.layout.cells.get(coord.as_tuple(), None)
    
    def set_exit(self):
        candidate_cells = [cell for cell in self.layout.cells.values() if cell.leaf and cell.coord.distance(self.start_coord) > 5]
        if self.get_cell(self.start_coord) in candidate_cells:
            candidate_cells.remove(self.get_cell(self.start_coord))
        if len(candidate_cells) == 0:
            candidate_cells = [cell for cell in self.layout.cells.values() if cell.leaf and cell.coord.__eq__(self.start_coord) == False]
        if len(candidate_cells) == 0:
            candidate_cells = [cell for cell in self.layout.cells.values() if cell.coord.__eq__(self.start_coord) == False]
        exit_cell = random.choice(candidate_cells)
        exit_cell.is_exit = True
        self.exit_coord = exit_cell.coord

    def print(self):
        for coord, cell in self.layout.cells.items():
            print(f'{coord}: {cell.is_room}')
        for door in self.layout.doors:
            print(f'{door}')
        for key in self.layout.keys:
            print(f'{key}')
        
        for y in range(-self.max_size+1, self.max_size-1):
            line = ''
            for x in range(-self.max_size+1, self.max_size-1):
                cell = self.get_cell(Coord(x, y, 0))
                if cell:
                    if cell.coord == self.start_coord:
                        line += 'S'
                    elif cell.coord == self.exit_coord:
                        line += 'E'
                    else:
                        line += 'o'
                else:
                    line += '.'
            print(line)

class MobPopulator():

    def __init__(self):
        self.max_spawns = 3

    def populate(self, layout: 'Layout', story: DynamicStory, zone: Zone):
        mob_spawners = list()
        leaves = layout.get_leaves()
        for i in range(self.max_spawns):
            cell = random.choice(leaves)
            location = story.grid[cell.coord.as_tuple()]
            mob_type = story.get_catalogue.get_creature(random.choice(zone.races))
            mob_type['level'] = zone.level
            item_probabilities = [random.random() * 0.15 + 0.5 for i in range(len(zone.items))]
            mob_spawner = MobSpawner(location=location, mob_type=mob_type, spawn_rate=30, spawn_limit=2, drop_items=zone.items, drop_item_probabilities=item_probabilities)
            mob_spawners.append(mob_spawner)
        return mob_spawners
    
    
class ItemPopulator():

    def __init__(self):
        self.max_items = 2

    def populate(self, zone: Zone, story: DynamicStory):
        item_spawners = list()
        for i in range(self.max_items):
            item_type = story.get_catalogue.get_item(random.choice(zone.items))
            item_type['level'] = zone.level
            item_types = [item_type]
            item_probabilities = [random.random() * 0.15 + 0.5 for i in range(len(zone.items))]
            item_spawners.append(ItemSpawner(zone=zone, items=item_types, item_probabilities=item_probabilities, spawn_rate=30))
        return item_spawners



class Layout():

    def __init__(self, start_coord: Coord):
        self.start_coord = start_coord
        self.cells = dict()
        self.doors = list()
        self.keys = list()
        self.exit_coord = None


    def get_leaves(self):
        return [cell for cell in self.cells.values() if cell.leaf]

class Cell():

    def __init__(self, coord = Coord(0,0,0), parent: Coord = None):

        self.coord = coord
        self.parent = parent
        self.room = None
        self.visited = False
        self.is_room = False
        self.is_corridor = False
        self.is_entrance = False
        self.is_exit = False
        self.leaf = False

class Door():

    def __init__(self, coord: Coord, other: Coord):
        self.coord = coord
        self.other = other
        self.locked = False

    def __str__(self) -> str:
        return f'Door: {self.coord.as_tuple()} <-> {self.other.as_tuple()}'

class Key():

    def __init__(self, coord: Coord, door: Door):
        self.coord = coord
        self.door = door

    def __str__(self) -> str:
        return f'Key: {self.coord.as_tuple()} -> {self.door.coord.as_tuple()}'