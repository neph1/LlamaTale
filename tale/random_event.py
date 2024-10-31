from tale.player import PlayerConnection
from tale.util import call_periodically


class RandomEvent:

    def __init__(self, llm_util, player: PlayerConnection):
        self.llm_util = llm_util
        self.player = player

    @call_periodically(300, 600)
    def _random_event(self):
        self.narrative_event()

    def narrative_event(self):
        self.llm_util.generate_narrative_event(self.player.player.location)
