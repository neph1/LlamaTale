"""
Tests for the reset_story wizard command.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import unittest
from unittest.mock import MagicMock, patch
import tale
from tale.base import Location, ParseResult
from tale.cmds import wizard
from tale.player import Player
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver


class TestResetStory(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.context = tale._MudContext()
        self.context.config = StoryConfig()
        self.context.driver = FakeDriver()
        
        self.player = Player('test_wizard', 'f')
        self.player.privileges.add('wizard')
        
        self.location = Location('test_location')
        self.location.init_inventory([self.player])
    
    def test_reset_story_command_exists(self):
        """Test that the reset_story command is registered."""
        # The command should be available
        self.assertTrue(hasattr(wizard, 'do_reset_story'))
    
    def test_reset_story_is_generator(self):
        """Test that reset_story is a generator (for the confirmation dialog)."""
        # The @wizcmd decorator wraps the function, so we check the 'is_generator' attribute
        # that was set by the decorator
        self.assertTrue(hasattr(wizard.do_reset_story, 'is_generator'))
        self.assertTrue(wizard.do_reset_story.is_generator)
    
    def test_reset_story_requires_confirmation(self):
        """Test that reset_story requires confirmation before executing."""
        parse_result = ParseResult(verb='!reset_story')
        
        # Create a generator from the command
        gen = wizard.do_reset_story(self.player, parse_result, self.context)
        
        # The first yield should be for input confirmation
        try:
            why, what = next(gen)
            self.assertEqual(why, 'input')
            # The confirmation message should mention affecting all players
            self.assertIn('all players', what[0].lower())
        except StopIteration:
            self.fail("Generator should yield for confirmation")
    
    def test_reset_story_driver_method_exists(self):
        """Test that the Driver.reset_story method exists."""
        from tale.driver import Driver
        self.assertTrue(hasattr(Driver, 'reset_story'))
        self.assertTrue(callable(getattr(Driver, 'reset_story')))
    
    @patch('tale.driver.Driver.reset_story')
    def test_reset_story_calls_driver_reset(self, mock_reset):
        """Test that the command calls the driver's reset_story method."""
        parse_result = ParseResult(verb='!reset_story')
        
        # Mock the driver's reset_story method
        self.context.driver.reset_story = mock_reset
        
        # Create and run the generator
        gen = wizard.do_reset_story(self.player, parse_result, self.context)
        
        # Send confirmation "yes"
        try:
            next(gen)  # First yield for input
            gen.send("yes")  # Confirm the reset
        except StopIteration:
            pass
        
        # The driver's reset_story should have been called
        mock_reset.assert_called_once()


if __name__ == '__main__':
    unittest.main()
