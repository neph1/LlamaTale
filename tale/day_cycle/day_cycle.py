

from typing import List, Protocol
from tale import mud_context
from tale.util import GameDateTime, call_periodically

class DayCycleEventObserver(Protocol):
    def on_dawn(self): pass
    def on_dusk(self): pass
    def on_day(self): pass
    def on_night(self): pass
    def on_midnight(self): pass

class DayCycle:
    
    def __init__(self, game_date_time: GameDateTime):
        self.game_date_time = game_date_time
        self.current_hour = game_date_time.clock.hour
        self.observers: List[DayCycleEventObserver] = []
        mud_context.driver.register_periodicals(self)
        
    def register_observer(self, observer: DayCycleEventObserver):
        self.observers.append(observer)

    def unregister_observer(self, observer: DayCycleEventObserver):
        self.observers.remove(observer)

    def notify_observers(self, event: str):
        for observer in self.observers:
            notify_method = getattr(observer, event, None)
            if callable(notify_method):
                notify_method()

    @call_periodically(30)
    def hour(self):
        if(self.current_hour == self.game_date_time.clock.hour):
            return
        self.current_hour = self.game_date_time.clock.hour
        if self.current_hour == 6:
            self.dawn()
        elif self.current_hour == 18:
            self.dusk()
        elif self.current_hour == 0:
            self.midnight()
        elif self.current_hour == 8:
            self.day()
        elif self.current_hour == 20:
            self.night()
        

    def dawn(self):
        self.notify_observers('on_dawn')

    def dusk(self):
        self.notify_observers('on_dusk')

    def day(self):
        self.notify_observers('on_day')

    def night(self):
        self.notify_observers('on_night')

    def midnight(self):
        self.current_hour = 0
        self.notify_observers('on_midnight')
