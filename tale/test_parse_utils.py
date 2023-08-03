import parse_utils


class TestParseUtils():

    def test_load_json(self):
        assert(parse_utils.load_json("tests/data/test.json"))
        
    def test_load_locations(self):
        room_json = parse_utils.load_json("tests/data/test_roms.json")
        locations, exits = parse_utils.load_locations(room_json)
        print(locations)
        print(exits)


if __name__ == "__main__":
    test_parse_utils = TestParseUtils()
    
    test_parse_utils.test_load_locations()