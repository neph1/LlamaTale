

class Coord():
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def distance(self, other) -> float:
        """ Returns the manhattan distance between this and another coordinate."""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)
    
    def xyz_distance(self, other) -> 'Coord':
        return Coord(abs(self.x - other.x), abs(self.y - other.y), abs(self.z - other.z))
    
    def subtract(self, other) -> 'Coord':
        """ Returns the coordinate resulting from subtracting other from this coordinate."""
        return Coord(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def add(self, other) -> 'Coord':
        """ Returns the coordinate resulting from adding other to this coordinate."""
        return Coord(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def multiply(self, value: int) -> 'Coord':
        """ Returns the coordinate resulting from multiplying this coordinate by value."""
        return Coord(self.x * value, self.y * value, self.z * value)
        

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
