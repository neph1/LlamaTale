

import random
from tale.base import Container
from tale.coord import Coord
from tale.item_spawner import ItemSpawner
from tale.items.basic import Money
from tale.llm.dynamic_story import DynamicStory
from tale.mob_spawner import MobSpawner
from tale.zone import Zone


class LayoutGenerator():

    def __init__(self, seed: int = None, start_coord: Coord = None):
        """ Allow init for tests """
        self.max_size = 10
        self.min_rooms = 10
        self.max_locked_doors = 1
        self.unvisited = []
        self.layout = Layout()
        self.start_coord = start_coord
        if seed:
            random.seed(seed)

    def generate(self, start_coord: Coord = Coord(0,0,0)) -> 'Layout':
        self.start_coord = start_coord
        self.layout = Layout(self.start_coord)
        start_location = Cell()
        start_location.is_room = True
        start_location.visited = False
        start_location.parent = None # block pathfinding across levels
        self.layout.cells[self.start_coord.as_tuple()] = start_location
        self.unvisited = [self.start_coord] # type: list[Coord]
        start_cell = self._generate_cell(coord=self.start_coord)
        if start_coord.z == 0:
            start_cell.is_dungeon_entrance = True
        else:
            start_cell.is_entrance = True
        while len(self.unvisited) > 0:
            coord = self.unvisited.pop()
            self._generate_room(coord)

        exit_coord = self.set_exit()
        self._place_door(exit_coord, self.layout.cells[exit_coord.as_tuple()].parent, locked=True)

        self.add_connector_cell(exit_coord)

        for door in self.layout.connections:
            if door.locked:
                self._place_key(door)

        return self.layout
        
    def add_connector_cell(self, exit_coord: Coord) -> 'Cell':
        connector_cell = self._generate_cell(exit_coord.add(Coord(0,0,-1)), exit_coord)
        connector_cell.is_entrance = True
        connector_cell.leaf = True
        return connector_cell

    def _generate_room(self, coord: Coord):
        cell = self._get_cell(coord) # type: Cell
        cell.visited = True

        # add neighbors
        openings = self._num_neighbors_to_add(coord)

        if openings == 0:
            cell.leaf = True
            return

        if coord.x % 2 == 1 or coord.y % 2 == 1:
            direction = coord.subtract(cell.parent)
            new_cell = self._get_cell(coord.add(direction))
            if new_cell is None:
                self._generate_cell(coord=coord.add(direction), parent=coord)
            return
        directions = [Coord(1,0,0), Coord(-1,0,0), Coord(0,1,0), Coord(0,-1,0)]
        if cell.parent:
            directions.remove(cell.parent.subtract(coord))
        while openings > 0:
            direction = random.choice(directions)
            new_coord = coord.add(direction)
            if self._get_cell(new_coord) is None:
                self._generate_cell(coord=coord.add(direction), parent=coord)
            else:
                self.layout.connections.add(Connection(coord, new_coord))
            openings -= 1
            
            directions.remove(direction)

    def _generate_cell(self, coord: Coord, parent: Coord = None) -> 'Cell':
        new_cell = Cell(coord=coord, parent=parent)
        new_cell.visited = False
        new_cell.is_room = random.random() < 0.33
        self.layout.cells[coord.as_tuple()] = new_cell
        self.unvisited.append(coord)
        door = None
        if parent and random.random() < 0.25:
            door = self._place_door(coord, parent)
            if self.max_locked_doors > 0 and random.random() < 0.2:
                door.locked = True
        return new_cell
    
    def _place_door(self, coord: Coord, other: Coord, locked: bool = False) -> 'Connection':
        door = Connection(coord, other, door=True)
        door.locked = locked
        self.layout.connections.add(door)
        return door

    def _place_key(self, door: 'Connection') -> 'Key':
        possible_cells = []
        leaves = self.layout.get_leaves()
        for leaf in leaves:
            coord = leaf.coord
            visited_cells = []
            previous_coord = None
            while coord is not self.start_coord:
                visited_cells.append(coord)
                previous_coord = coord
                coord = self._get_cell(coord).parent
                if coord is None:
                    break
                if coord == door.coord and previous_coord == door.other:
                    visited_cells.clear()
                
            possible_cells.extend(visited_cells)
        if len(possible_cells) == 0:
            door.locked = False
            print('no possible cells for key ', door)
            return None
        key_coord = random.choice(possible_cells)
        key = Key(key_coord, door)
        key.key_code = door.key_code = f'{random.randint(1000,99999)}'
        self.layout.keys.add(key)
        return key

    def _num_neighbors_to_add(self, coord: Coord) -> int:
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

    def _get_cell(self, coord: Coord):
        return self.layout.cells.get(coord.as_tuple(), None)
    
    def set_exit(self) -> Coord:
        candidate_cells = [cell for cell in self.layout.cells.values() if cell.leaf and cell.coord.distance(self.start_coord) > 5]
        if self._get_cell(self.start_coord) in candidate_cells:
            candidate_cells.remove(self._get_cell(self.start_coord))
        if len(candidate_cells) == 0:
            candidate_cells = [cell for cell in self.layout.cells.values() if cell.leaf and cell.coord.__eq__(self.start_coord) == False]
        if len(candidate_cells) == 0:
            candidate_cells = [cell for cell in self.layout.cells.values() if cell.coord.__eq__(self.start_coord) == False]
        exit_cell = random.choice(candidate_cells)
        exit_cell.is_exit = True
        exit_cell.leaf = False
        self.exit_coord = exit_cell.coord
        return exit_cell.coord
    

    def spawn_gold(self, zone: Zone):

        container_names = ["Box", "Pouch", "Chest", "Bag"]
        for i in range(self.max_gold):
            money = Money(name="money", value=random.randrange(5, 25) * zone.level)
            container = Container(random.choice(container_names))
            container.init_inventory([money])
            location = random.choice(list(zone.locations.values())) # Location
            location.insert(container, None)
            self.depth += 1

    def print(self):
        for coord, cell in self.layout.cells.items():
            print(f'{coord}: {cell.is_room}')
        for door in self.layout.connections:
            print(f'{door}')
        for key in self.layout.keys:
            print(f'{key}')
        
        for y in range(-self.max_size+1, self.max_size-1):
            line = ''
            for x in range(-self.max_size+1, self.max_size-1):
                cell = self._get_cell(Coord(x, y, 0))
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

    def populate(self, layout: 'Layout', story: DynamicStory, zone: Zone) -> list:
        if len(zone.races) == 0:
            return []
        mob_spawners = []
        leaves = layout.get_leaves()
        # Filter leaves to only those that have locations in the grid
        valid_leaves = [cell for cell in leaves if cell.coord.as_tuple() in story.grid]
        if not valid_leaves:
            return []
        for i in range(self.max_spawns):
            cell = random.choice(valid_leaves)
            location = story.grid[cell.coord.as_tuple()]
            mob_type = story.get_catalogue.get_creature(random.choice(zone.races))
            if not mob_type:
                continue
            mob_type['level'] = zone.level
            item_types = [zone.items]
            item_probabilities = [(random.random() * 0.15 + 0.5) for i in range(len(item_types))]
            mob_spawner = MobSpawner(location=location, mob_type=mob_type, spawn_rate=30, spawn_limit=2, drop_items=zone.items, drop_item_probabilities=item_probabilities)
            mob_spawners.append(mob_spawner)
        if len(mob_spawners) == 1:
            return [mob_spawners]
        return mob_spawners
    
    
class ItemPopulator():

    def __init__(self):
        self.max_items = 2
        self.max_gold = 5

    def populate(self, zone: Zone, story: DynamicStory) -> list:
        if len(zone.items) == 0:
            return []
        item_spawners = []
        if len(zone.items) == 0:
            self.max_items = 0
        for i in range(self.max_items):
            item_type = story.get_catalogue.get_item(random.choice(zone.items))
            if not item_type:
                continue
            item_type['level'] = zone.level
            item_types = [item_type]
            item_probabilities = [(random.random() * 0.15 + 0.5) for i in range(len(item_types))]
            item_spawners.append(ItemSpawner(zone=zone, items=item_types, item_probabilities=item_probabilities, spawn_rate=30))
        if len(item_spawners) == 1:
            return [item_spawners]
        return item_spawners

class Layout():

    def __init__(self, start_coord: Coord = None):
        self.start_coord = start_coord
        self.cells = dict()
        self.doors = set()
        self.keys = set()
        self.connections = set()
        self.exit_coord = None

    def get_leaves(self):
        return [cell for cell in self.cells.values() if cell.leaf]

class Cell():

    def __init__(self, coord = Coord(0,0,0), parent: Coord = None):

        self.coord = coord
        self.parent = parent
        self.room = None
        self.visited = False
        self.is_dungeon_entrance = False
        self.is_room = False
        self.is_corridor = False
        self.is_entrance = False
        self.is_exit = False
        self.leaf = False

class Key():

    def __init__(self, coord: Coord, door: 'Connection'):
        self.coord = coord
        self.door = door
        self.key_code = ""

    def __str__(self) -> str:
        return f'Key: {self.coord.as_tuple()} -> {self.door.coord.as_tuple()}'
    
class Connection():

    def __init__(self, coord: Coord, other: Coord, door: bool = False):
        self.coord = coord
        self.other = other
        self.door = door
        self.locked = False
        self.key_code = ""  

    
    def __str__(self) -> str:
        if self.door:
            return f'Door: {self.coord.as_tuple()} <-> {self.other.as_tuple()}'
        return f'Connection: {self.coord.as_tuple()} <-> {self.other.as_tuple()}'