
import pathlib
import sys
from tale import parse_utils
from tale.driver import Driver
from tale.json_story import JsonStory
from tale.main import run_from_cmdline
from tale.player import Player
from tale.quest import Quest, QuestType
from tale.skills.weapon_type import WeaponType


class Story(JsonStory):

    driver = None

    def __init__(self) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))

    def init(self, driver: Driver) -> None:
        super(Story, self).init(driver)
        # TALK quest on the landlady: completes on the second dialogue exchange
        # with her (the first one starts it), publishing a QuestCompleted event
        # that completes the "suspicion" beat
        corbin = self._world.npcs.get("corbin")
        if corbin is not None:
            corbin.quest = Quest(name="the cellar secret", type=QuestType.TALK,
                                 target=corbin.title, reason="find out what is in the cellar",
                                 giver=corbin.title)

    def init_player(self, player: Player) -> None:
        # test story: the (single) player may use wizard commands such as !set_beat
        player.privileges.add("wizard")
        # unarmed skill 100: every attack hits, so the kill-goal smoke test is deterministic
        player.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=100)


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
