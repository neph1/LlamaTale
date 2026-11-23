import pathlib
import sys

from tale import parse_utils
from tale.driver import Driver
from tale.json_story import JsonStory
from tale.main import run_from_cmdline
from tale.player import Player
from tale.skills.weapon_type import WeaponType


class Story(JsonStory):
    """Smoke test story for non-lethal combat (PR #153).

    story_config.json sets "combat_type": "non-lethal" and deliberately omits the
    "lethal" key, so lethal=False is derived from the combat tone by
    load_story_config(). Attacking the training dummy must floor its hp at 1
    ("knocked out and yields"), never kill it.
    """

    driver = None

    def __init__(self) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))

    def init(self, driver: Driver) -> None:
        super(Story, self).init(driver)

    def init_player(self, player: Player) -> None:
        # strong enough to floor the dummy's 5 hp at 1 in a single hit
        player.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=90)
        player.stats.wc = 25
        player.stats.hp = 50
        player.stats.max_hp = 50


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
