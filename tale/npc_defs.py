

import random
from tale.base import Living
from tale.llm.llm_ext import LivingNpc
from tale.player import Player
from tale.util import Context, call_periodically

class StationaryNpc(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str, occupation: str="", race: str=""):
        super(StationaryNpc, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation=occupation, race=race)
        

    @call_periodically(20, 45)
    def do_idle_action(self, ctx: Context) -> None:
        """ Perform an idle action if a player is in the same location."""
        player_names = ctx.driver.all_players.keys()
        player_in_location = any(name == living.name for name in player_names for living in self.location.livings)
        if player_in_location:
            self.idle_action()

class StationaryMob(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", race: str=""):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, race=race, age=0, personality='', occupation='')

    @call_periodically(15, 60)
    def do_idle_action(self, ctx: Context) -> None:
        player_in_location = any(isinstance(living, Player) for living in self.location.livings)
        if player_in_location and self.aggressive and not self.attacking:
            for liv in self.location.livings:
                if isinstance(liv, Player):
                    self.do_attack(liv)
        elif player_in_location:
            self.idle_action()

    def do_attack(self, target: Living) -> None:
        self.start_attack(victim=target)
        
class RoamingMob(StationaryMob):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", race: str=""):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr,race=race)

    @call_periodically(40, 180)
    def do_random_move(self, ctx: Context) -> None:
        direction = self.select_random_move()
        if direction:
            self.move(direction.target, self, direction_names=direction.names)
