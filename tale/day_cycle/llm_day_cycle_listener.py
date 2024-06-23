


from tale.day_cycle.day_cycle import DayCycleEventObserver
from tale.driver import Driver


class LlmDayCycleListener(DayCycleEventObserver):

    def __init__(self, driver):
        self.driver = driver # type: Driver

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
        self.driver.llm_util.describe_day_cycle_transition(list(self.driver.all_players.values())[0], from_time, to_time)