
import random
from tale.base import Item
from tale.llm.LivingNpc import LivingNpc
from tale.player import Player
from tale.shop import ShopBehavior, Shopkeeper
from tale.skills.magic import MagicType
from tale.skills.skills import SkillType
from tale.skills.weapon_type import WeaponType
from tale.util import Context, call_periodically

class StationaryNpc(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str, occupation: str="", race: str="human", parse_occupation: bool = False):
        super(StationaryNpc, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation=occupation, race=race, parse_occupation=parse_occupation)

    @call_periodically(30, 60)
    def do_idle_action(self, ctx: Context) -> None:
        """ Perform an idle action if a player is in the same location."""
        if not self.location or self.location.name == 'Limbo':
            return
        player_names = ctx.driver.all_players.keys()
        player_in_location = any(name == living.name for name in player_names for living in self.location.livings)
        
        if player_in_location or self.location.get_wiretap() or self.get_wiretap():
            self.idle_action()

class StationaryMob(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", race: str="human", occupation: str="", parse_occupation: bool = False):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, race=race, age=0, personality='', occupation=occupation, parse_occupation=parse_occupation)

    @call_periodically(30, 60)
    def do_idle_action(self, ctx: Context) -> None:
        if not self.location or self.location.name == 'Limbo':
            return
        player_in_location = any(isinstance(living, Player) for living in self.location.livings)
        if player_in_location and self.aggressive and not self.attacking:
            for liv in self.location.livings:
                if isinstance(liv, Player):
                    self.start_attack(defender=liv)
        elif player_in_location or self.location.get_wiretap() or self.get_wiretap():
            self.idle_action()
        
class RoamingMob(StationaryMob):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", race: str="human", parse_occupation: bool = False):
        super(StationaryMob, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr,race=race, parse_occupation=parse_occupation)

    @call_periodically(40, 180)
    def do_random_move(self, ctx: Context) -> None:
        if not self.location or self.location.name == 'Limbo':
            return
        direction = self.select_random_move()
        if direction:
            self.move(direction.target, self, direction_names=direction.names)

class Trader(Shopkeeper):
    
    def __init__(self, name: str, gender: str, *, title: str = "", descr: str = "", short_descr: str = "", age: int, personality: str, occupation: str = "", race: str = "", parse_occupation: bool = False):
        super(Trader, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation=occupation, race=race, parse_occupation=parse_occupation)

    def setup_shop_items(self, items: list = [], always_for_sale: list = [], will_buy: list = []):
        """ Supply a list of items for sale and a list of items that never run out (subset of items)"""
        shopinfo = ShopBehavior()
        for item in always_for_sale:
            shopinfo.forsale.add(item)
        shopinfo.banks_money = True
        self.init_inventory([item for item in items])
        self.set_shop(shopinfo)
