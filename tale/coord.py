

class Coord():
    """ Represents a coordinate in 3D space.
    x is west and east, 
    y is north and south,
    z is up and down.
    """

    def __init__(self, x:int = 0, y:int = 0, z:int = 0):
        self.x = x
        self.y = y
        self.z = z

    #def __dict__(self):
    #    return {'x': self.x, 'y': self.y, 'z': self.z}

    def as_tuple(self) -> tuple:
        return (self.x, self.y, self.z)
    
    @classmethod
    def from_coord(self, coord: 'Coord'):
        return Coord(coord.x, coord.y, coord.z)

    @classmethod
    def from_input(cls, value) -> 'Coord':
        """Build a Coord from whatever a config or agent might send.

        Accepts an existing Coord, a {"x", "y", "z"} dict (each key optional,
        defaulting to 0), or a [x, y, z] list/tuple. Anything else raises
        ValueError. Centralising this lets code that expects a plain
        coordinate also accept the dict form agents sometimes send.
        """
        if isinstance(value, Coord):
            return Coord(value.x, value.y, value.z)
        if isinstance(value, dict):
            return cls(value.get("x", 0), value.get("y", 0), value.get("z", 0))
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return cls(value[0], value[1], value[2])
        raise ValueError(
            "invalid coordinate %r: expected a Coord, a {'x', 'y', 'z'} dict "
            "or a [x, y, z] list/tuple" % (value,)
        )

    def distance(self, other) -> float:
        """ Returns the manhattan distance between this and another coordinate."""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)
    
    def xyz_distance(self, other) -> 'Coord':
        return Coord(abs(self.x - other.x), abs(self.y - other.y), abs(self.z - other.z))
    
    def subtract(self, other) -> 'Coord':
        """ Returns the coordinate resulting from subtracting other from this coordinate."""
        return Coord(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def add(self, other: 'Coord') -> 'Coord':
        """ Returns the coordinate resulting from adding other to this coordinate."""
        return Coord(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def multiply(self, value: int) -> 'Coord':
        """ Returns the coordinate resulting from multiplying this coordinate by value."""
        return Coord(self.x * value, self.y * value, self.z * value) 

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
    
    def valid(self) -> bool:
        return self.z != 255
    
