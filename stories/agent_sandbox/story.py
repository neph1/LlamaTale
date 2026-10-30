import pathlib
import sys

import tale
from tale.driver import Driver
from tale.llm.dynamic_story import DynamicStory
from tale.main import run_from_cmdline
from tale.player import Player
from tale.story import GameMode, MoneyType, StoryConfig, TickMethod
from tale.story_context import StoryContext
from tale.zone import Zone


class Story(DynamicStory):

    config = StoryConfig()
    config.name = "Agent Sandbox"
    config.author = "LlamaTale"
    config.version = tale.__version__
    config.supported_modes = {GameMode.IF}
    config.money_type = MoneyType.NOTHING
    config.server_tick_method = TickMethod.TIMER
    config.server_tick_time = 1.0
    config.gametime_to_realtime = 1
    config.savegames_enabled = False
    config.startlocation_player = "agent_sandbox.garden"
    config.startlocation_wizard = "agent_sandbox.garden"
    config.zones = ["agent_sandbox"]
    config.context = StoryContext(base_story="A quiet village outskirts: a fenced garden next to a cottage, with a locked toolshed. Bram the gardener minds the garden on his own.")
    config.type = "A minimal sandbox for testing autonomous LLM-driven NPC agents."
    config.world_info = "A small rural homestead: vegetable garden, cottage, and a locked shed. Inhabited by a gardener, a villager and the odd giant rat."
    config.world_mood = 2

    def init(self, driver: Driver) -> None:
        """Called by the game driver when it is done with its initial initialization."""
        self.driver = driver
        zone = Zone("agent_sandbox", description="A small test area for autonomous agents.")
        self._zones["agent_sandbox"] = zone
        import zones.agent_sandbox
        for location in zones.agent_sandbox.all_locations:
            zone.add_location(location)

    def welcome(self, player: Player) -> str:
        player.tell("<bright>Welcome to the Agent Sandbox, %s!</>" % player.title, end=True)
        player.tell("Bram the gardener (an autonomous agent) is puttering around the garden.", end=True)
        player.tell("Try talking to him or Mira, or just watch what he does.", end=True)
        return ""


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
