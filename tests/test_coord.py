

from tale.coord import Coord


class TestCoord():

    def test_init(self):
        coord = Coord(1,2,3)
        assert(coord.x == 1)
        assert(coord.y == 2)
        assert(coord.z == 3)

    def test_eq(self):
        coord1 = Coord(1,2,3)
        coord2 = Coord(1,2,3)
        assert(coord1 == coord2)

    def test_multiply(self):
        coord = Coord(1,2,3)
        assert(coord.multiply(2) == Coord(2,4,6))
        assert(coord.multiply(0) == Coord(0,0,0))

    def test_subtract(self):
        coord1 = Coord(1,2,3)
        coord2 = Coord(1,2,3)
        assert(coord1.subtract(coord2) == Coord(0,0,0))
        coord2 = Coord(1,2,4)
        assert(coord1.subtract(coord2) == Coord(0,0,-1))

    def test_xyz_distance(self):
        coord1 = Coord(1,2,3)
        coord2 = Coord(1,2,3)
        assert(coord1.xyz_distance(coord2) == Coord(0,0,0))
        coord2 = Coord(-3,2,4)
        assert(coord1.xyz_distance(coord2) == Coord(4,0,1))

    def test_distance(self):
        coord1 = Coord(1,2,3)
        coord2 = Coord(3,2,1)
        assert(coord1.distance(coord2) == 4)