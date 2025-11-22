import pathlib
import random
import sys
from typing import Generator

from tale import parse_utils
from tale import lang
from tale.base import Door, Exit, Location
from tale.charbuilder import PlayerNaming
from tale.coord import Coord
from tale.driver import Driver
from tale.dungeon.dungeon import Dungeon
from tale.dungeon.dungeon_generator import ItemPopulator, Layout, LayoutGenerator, MobPopulator
from tale.items.basic import Money
from tale.json_story import JsonStory
from tale.skills.magic import MagicType
from tale.main import run_from_cmdline
from tale.npc_defs import RoamingMob
from tale.player import Player, PlayerConnection
from tale.skills.skills import SkillType
from tale.story import *
from tale.skills.weapon_type import WeaponType
from tale.zone import Zone

class Story(JsonStory):

    driver = None  # type: Driver

    def __init__(self, path = '', layout_generator = LayoutGenerator(), mob_populator = MobPopulator(), item_populator = ItemPopulator(), config: StoryConfig = None) -> None:
        super(Story, self).__init__(path, config or parse_utils.load_story_config(parse_utils.load_json('story_config.json')))
        self.layout_generator = layout_generator
        self.mob_populator = mob_populator
        self.item_populator = item_populator
        self.max_depth = 5
        self.depth = 0
        self.dungeon = None  # Will be created after init
        

    def init(self, driver: Driver) -> None:
        self.llm_util = driver.llm_util
        # Create the dungeon instance BEFORE calling super().init()
        self.dungeon = Dungeon(
            name="The Depths",
            story=self,
            llm_util=self.llm_util,
            layout_generator=self.layout_generator,
            mob_populator=self.mob_populator,
            item_populator=self.item_populator,
            max_depth=self.max_depth
        )
        super(Story, self).init(driver)

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED, value=random.randint(10, 30))
        player.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=random.randint(20, 30))
        player.stats.magic_skills.set(MagicType.HEAL, 30)
        player.stats.magic_skills.set(MagicType.BOLT, 30)
        player.stats.magic_skills.set(MagicType.DRAIN, 30)
        player.stats.magic_skills.set(MagicType.REJUVENATE, 30)
        pass

    def create_account_dialog(self, playerconnection: PlayerConnection, playernaming: PlayerNaming) -> Generator:
        """
        Override to add extra dialog options to the character creation process.
        Because there's no actual player yet, you receive PlayerConnection and PlayerNaming arguments.
        Write stuff to the user via playerconnection.output(...)
        Ask questions using the yield "input", "question?"  mechanism.
        Return True to declare all is well, and False to abort the player creation process.
        """
        ranged = yield "input", ("Do you prefer ranged over close combat? (yes/no)", lang.yesno)
        if ranged:
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(20, 40))
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(20, 40))
        else:
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED, value=random.randint(20, 40))
            playerconnection.player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED, value=random.randint(20, 40))
        stealth = yield "input", ("Are you sneaky? (yes/no)", lang.yesno)
        if stealth:
            if stealth:
                playerconnection.player.stats.set(SkillType.HIDE, random.randint(30, 50))
                playerconnection.player.stats.set(SkillType.PICK_LOCK, random.randint(30, 50))
            else:
                playerconnection.player.stats.set(SkillType.HIDE, random.randint(10, 30))
                playerconnection.player.stats.set(SkillType.PICK_LOCK, random.randint(10, 30))
            playerconnection.player.stats.set(SkillType.SEARCH, random.randint(20, 40))
        
        return True

    def welcome(self, player: Player) -> str:
        """welcome text when player enters a new game"""
        player.tell("<bright>Hello, %s! Welcome to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        player.tell(self.config.context)
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        """welcome text when player enters the game after loading a saved game"""
        player.tell("<bright>Hello %s, welcome back to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        return ""

    def goodbye(self, player: Player) -> None:
        """goodbye text when player quits the game"""
        player.tell("Goodbye, %s. Please come back again soon." % player.title)
        player.tell("\n")

    def add_zone(self, zone: Zone) -> bool:
        if not super(Story, self).add_zone(zone):
            return False
        if zone.locations != {}:
            return True
        
        # Use the dungeon to generate the level
        if self.dungeon:
            depth = len(self.dungeon.zones)
            self.depth = depth
            self.dungeon.generate_level(zone, depth=depth)
        
        return True


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)