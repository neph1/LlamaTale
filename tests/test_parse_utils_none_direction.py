"""
Test for the fix of None direction issue during start location generation.
This test validates that parse_generated_exits handles edge cases properly.
"""
import json
from tale.base import Location
import tale.parse_utils as parse_utils


class TestParseUtilsNoneDirection:
    """Tests for handling None/missing directions in exit parsing"""

    def test_parse_generated_exits_missing_direction(self):
        """Test that exits without direction field don't cause None values"""
        exits = json.loads('{"exits": [{"name": "The Cave", "short_descr": "A dark opening."}]}')
        exit_location_name = 'Entrance'
        location = Location(name='Outside')
        
        new_locations, parsed_exits = parse_utils.parse_generated_exits(
            exits=exits.get('exits'), 
            exit_location_name=exit_location_name, 
            location=location
        )
        
        # Should create one exit with only location name as direction
        assert len(parsed_exits) == 1
        assert parsed_exits[0].name == 'cave'
        # Description should not contain 'None'
        assert 'None' not in parsed_exits[0].short_description
        assert parsed_exits[0].short_description == 'You see a dark opening.'

    def test_parse_generated_exits_null_direction(self):
        """Test that exits with null direction don't cause crashes"""
        exits = [{"name": "Willowdale", "direction": None, "short_descr": "A path."}]
        exit_location_name = 'Start'
        location = Location(name='Beginning')
        
        new_locations, parsed_exits = parse_utils.parse_generated_exits(
            exits=exits, 
            exit_location_name=exit_location_name, 
            location=location
        )
        
        # Should create one exit
        assert len(parsed_exits) == 1
        # Description should not contain 'None'
        assert 'None' not in parsed_exits[0].short_description

    def test_parse_generated_exits_all_directions_occupied(self):
        """Test that when all cardinal directions are occupied, function still works"""
        # Create a location with all four cardinal directions already occupied
        location = Location(name='Center')
        
        # First, add exits in all four cardinal directions
        exits_round1 = [
            {"name": "North Room", "direction": "north", "short_descr": "Northern exit."},
            {"name": "South Room", "direction": "south", "short_descr": "Southern exit."},
            {"name": "East Room", "direction": "east", "short_descr": "Eastern exit."},
            {"name": "West Room", "direction": "west", "short_descr": "Western exit."}
        ]
        
        new_locations, parsed_exits = parse_utils.parse_generated_exits(
            exits=exits_round1, 
            exit_location_name='', 
            location=location
        )
        
        location.add_exits(parsed_exits)
        assert len(location.exits) == 8  # 4 exits × 2 directions each (name + cardinal)
        
        # Now try to add more exits when all cardinals are taken
        exits_round2 = [
            {"name": "Fifth Room", "direction": "north", "short_descr": "Another room."}
        ]
        
        new_locations2, parsed_exits2 = parse_utils.parse_generated_exits(
            exits=exits_round2, 
            exit_location_name='', 
            location=location
        )
        
        # Should still create an exit with a valid direction (not None)
        assert len(parsed_exits2) == 1
        assert parsed_exits2[0].name is not None
        assert 'None' not in parsed_exits2[0].short_description

    def test_select_non_occupied_direction_all_occupied(self):
        """Test that _select_non_occupied_direction returns a valid direction even when all are occupied"""
        occupied = ['north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest', 'up', 'down']
        direction = parse_utils._select_non_occupied_direction(occupied)
        
        # Should return a valid direction (fallback), not None
        assert direction is not None
        assert isinstance(direction, str)
        assert len(direction) > 0

    def test_opposite_direction_diagonals(self):
        """Test that opposite_direction handles diagonal directions"""
        assert parse_utils.opposite_direction('northeast') == 'southwest'
        assert parse_utils.opposite_direction('southwest') == 'northeast'
        assert parse_utils.opposite_direction('northwest') == 'southeast'
        assert parse_utils.opposite_direction('southeast') == 'northwest'

    def test_location_look_with_exits(self):
        """Test that Location.look() can handle exits properly without crashing on None"""
        from tale import mud_context
        from tale.driver_if import IFDriver
        from tale.story import StoryConfig, GameMode
        from tale.base import Exit
        
        # Set up minimal driver context
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        mud_context.driver = driver
        
        config = StoryConfig()
        config.name = "Test"
        config.supported_modes = [GameMode.IF]
        config.show_exits_in_look = True
        mud_context.config = config
        
        # Create location with exits
        location = Location(name='Test Room', descr='A test room')
        north_room = Location(name='North Room', descr='Northern room')
        
        # Create an exit with a valid direction
        exit_north = Exit(directions=['north', 'north room'], 
                         target_location=north_room, 
                         short_descr='To the north you see North Room.')
        location.add_exits([exit_north])
        
        # This should not crash
        paragraphs = location.look()
        assert len(paragraphs) > 0
        # Join all paragraphs and check that 'None' doesn't appear
        full_text = ' '.join(paragraphs)
        assert 'None' not in full_text