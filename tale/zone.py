import random
from tale.base import Location
from tale.coord import Coord


class Zone():

    def __init__(self, name: str, description: str = '') -> None:
        self.description = description
        self.locations = dict()  # type: dict[str, Location]
        self.level = 1 # average level of the zone
        self.races = [] # type list[str] # common races to be encountered in the zone
        self.items = [] # type list[str] # common items to find in the zone
        self.mood = 0 # defines friendliness or hostility of the zone. > 0 is friendly
        self.size = 5 # roughly the 'radius' of the zone.
        self.size_z = 3 # height of the zone
        self.neighbors = dict() # type: dict[str, Zone] # north, east, south or west
        self.center = Coord(0,0,0) 
        self.name = name

    def add_location(self, location: Location) -> bool:
        """ Add a location to the zone. Skip if location already exists."""
        if location.name in self.locations:
            return False
        self.locations[location.name] = location
        return True
    
    def remove_location(self, name: str) -> bool:
        """ Remove a location from the zone. Skip if location does not exist."""
        if name not in self.locations:
            return False
        self.locations[name] = None
        return True

    def get_location(self, name: str) -> Location:
        return self.locations.get(name, None)
    
    def get_info(self) -> dict:
        return {"description":self.description,
                "level":self.level,
                "mood":self.mood,
                "races":self.races,
                "items":self.items,
                "size":self.size,
                "center":self.center.as_tuple()
                }

    def get_neighbor(self, direction: str) -> 'Zone':
        return self.neighbors[direction]
    
    def get_neighbor(self, direction: Coord) -> 'Zone':
        if direction.x == 1:
            return self.neighbors.get('east', None)
        if direction.x == -1:
            return self.neighbors.get('west', None)
        if direction.y == -1:
            return self.neighbors.get('north', None)
        if direction.y == 1:
            return self.neighbors.get('south', None)
        if direction.z == 1:
            return self.neighbors.get('up', None)
        if direction.z == -1:
            return self.neighbors.get('down', None)
        return None
    
    def on_edge(self, coord: Coord, direction: Coord) -> bool:
        """ Returns true if the coordinate is on the edge of the zone in the given direction. 
        Higher likelihood the further away from the center of the zone.
        """
        zone_distance = self.center.xyz_distance(coord)
        if (direction.x != 0 and zone_distance.x > self.size - 1):
            return True
        if (direction.y != 0 and zone_distance.y > self.size - 1):
            return True
        if (direction.z != 0 and zone_distance.z > self.size_z - 1):
            return True
        return False
    
def from_json(data: dict) -> 'Zone':
    zone = Zone(data.get("name", "unknown"), data.get("description", "unknown"))
    zone.level = data.get("level", 1)
    zone.mood = data.get("mood", 0)
    zone.items = data.get("items", [])
    zone.races = data.get("races", [])
    zone.size = data.get("size", 5)
    if data.get("center", None) is not None:
        center = data.get("center")
        zone.center = Coord(center[0], center[1], center[2])
    return zone
