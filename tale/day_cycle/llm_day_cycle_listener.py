from typing import List
from tale.day_cycle.day_cycle import DayCycleEventObserver
from tale.player import PlayerConnection


class LlmDayCycleListener(DayCycleEventObserver):

    def __init__(self, llm_util, players):
        self.llm_util = llm_util
        self.players = players # type: List[PlayerConnection]

    def on_dawn(self):
        self._describe_transition("night", "dawn")

    def on_dusk(self):
        self._describe_transition("day", "dusk")

    def on_day(self):
        self._describe_transition("dawn", "day")

    def on_night(self):
        self._describe_transition("dusk", "night")

    def on_midnight(self):
        pass

    def _describe_transition(self, from_time: str, to_time: str):
        self.llm_util.describe_day_cycle_transition(self.players, from_time, to_time)