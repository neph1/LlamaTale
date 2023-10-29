"""
Embedded Demo story, start it with python -m tale.demo.story

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import pathlib
import sys
from typing import Optional

import tale
from tale.driver import Driver
from tale.main import run_from_cmdline
from tale.player import Player
from tale.story import *
from tale.json_story import JsonStory
import tale.parse_utils as parse_utils


class Story(JsonStory):
    # create story configuration and customize:
    config = parse_utils.load_story_config(parse_utils.load_json('tests/files/world_story/Test Story Config 1.json'))
    
    def init_player(self, player: Player) -> None:
        player.money = 12.65

    def welcome(self, player: Player) -> str:
        return ""

    def welcome_savegame(self, player: Player) -> str:
        return ""  # not supported in demo

    def goodbye(self, player: Player) -> None:
        player.tell("Thanks for trying out Tale!")


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
    else:
        print("Cannot load the story files from:", gamedir, file=sys.stderr)
        print("\nIt looks like you tried running the built-in demo story, "
              "but the tale library has been installed as an 'egg' or zip-file "
              "rather than normal files in your packages directory.\n"
              "This is not yet supported, sorry. "
              "Either re-install tale as normal files or just try any of the separate demo stories that come with it!\n",
              file=sys.stderr)
        raise SystemExit
