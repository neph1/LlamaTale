"""
Demo story: a single vault room with a trapped chest.

The chest in the vault carries an OPEN trap (see world.json): opening it
springs a poison needle. Use 'search' to reveal the trap and 'disarm' to
make the chest safe to open.
"""

import pathlib
import sys

from tale import parse_utils
from tale.driver import Driver
from tale.json_story import JsonStory
from tale.main import run_from_cmdline


class Story(JsonStory):
    """Single-room story demonstrating a trap attached to a container."""

    driver = None

    def __init__(self, path: str = '') -> None:
        if not path:
            # If no path provided, use the directory containing this file
            import os
            path = os.path.dirname(os.path.abspath(__file__)) + '/'
        config = parse_utils.load_story_config(parse_utils.load_json(path + 'story_config.json'))
        super(Story, self).__init__(path, config)

    def init(self, driver: Driver) -> None:
        super(Story, self).init(driver)


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
