

import random
from tale import _MudContext
from tale.driver import Driver
from tale.llm.llm_ext import DynamicStory
from tale.player import PlayerConnection
from tale.util import call_periodically


class RandomEvent:

    def __init__(self, driver: Driver):
        self.driver = driver
        self.driver.register_periodicals(self)

    @call_periodically(300, 600)
    def _random_event(self):
        self.narrative_event()

    def narrative_event(self):
        self.player = list(self.driver.all_players.values())[0] # type: PlayerConnection
        self.driver.llm_util.generate_narrative_event(self.player.player.location)
