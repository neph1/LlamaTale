"""
'Zed is me' -  a small survival adventure

Written for Tale IF framework.
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import sys
from typing import Optional

from tale.driver import Driver
from tale.player import Player
from tale.story import *


class Story(StoryBase):
    # create story configuration and customize:
    config = StoryConfig()
    config.name = "Zed is me"
    config.author = "Irmen de Jong"
    config.author_address = "irmen@razorvine.net"
    config.version = "1.11"
    config.requires_tale = "0.51.0"
    config.supported_modes = {GameMode.IF}
    config.money_type = MoneyType.MODERN
    config.player_name = "julie"
    config.player_gender = "f"
    config.player_race = "human"
    config.playable_races = {"human"}
    config.startlocation_player = "houses.livingroom"
    config.startlocation_wizard = "houses.livingroom"
    config.zones = ["houses", "magnolia_st", "rose_st"]
    # story-specific fields follow:
    driver = None     # will be set by init()

    def init(self, driver: Driver) -> None:
        """Called by the game driver when it is done with its initial initialization."""
        self.driver = driver

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        pass

    def welcome(self, player: Player) -> str:
        """
        Welcome text when player enters a new game
        If you return a string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Welcome to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        player.tell_text_file(self.driver.resources["messages/welcome.txt"])
        player.tell("\n")
        return "<bright>Press enter to continue.</>"

    def welcome_savegame(self, player: Player) -> str:
        """
        Welcome text when player enters the game after loading a saved game
        If you return a string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Welcome back to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        player.tell_text_file(self.driver.resources["messages/welcome.txt"])
        player.tell("\n")
        return "<bright>Press enter to continue where you were before.</>"


if __name__ == "__main__":
    # story is invoked as a script, start it.
    from tale.main import run_from_cmdline
    run_from_cmdline(["--game", sys.path[0]])
