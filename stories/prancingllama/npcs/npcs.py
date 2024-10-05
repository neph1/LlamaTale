import random
from tale import mud_context

from tale.base import Item, Living, ParseResult
from tale.errors import ParseError, ActionRefused
from tale.lang import capital
from tale.llm.LivingNpc import LivingNpc
from tale.player import Player
from tale.quest import Quest, QuestType
from tale.resources_utils import pad_text_for_avatar
from tale.util import call_periodically, Context
from tale import lang
from typing import Optional

from tale.skills.weapon_type import WeaponType

class InnKeeper(LivingNpc):
    
    drink_price = 5.0

    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(InnKeeper, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='Inn Keeper')
        
    def init(self) -> None:
        self.aliases = {"innkeeper"}
        self.verbs["buy"] = "Purchase something."

    def handle_verb(self, parsed: ParseResult, actor: Living) -> bool:
        drink = self.search_item("ale", include_location=False)
        if parsed.verb == "buy" and drink is not None:
            if not parsed.args:
                raise ParseError("Buy what?")
            if "ale" in parsed.args or "drink" in parsed.args:
                self.do_buy_drink(actor, drink, self.drink_price)
                return True
        return False

    def do_buy_drink(self, actor: Living, drink: Item, price: float) -> None:
        if actor.money < price:
            raise ActionRefused("You don't have enough money!")
        actor.money -= price
        self.money += price
        drink.move(actor, self)
        price_str = mud_context.driver.moneyfmt.display(price)
        actor.tell("After handing %s the %s, %s gives you the %s." % (self.objective, price_str, self.subjective, drink.title), evoke=True, short_len=True)
        self.tell_others("{Actor} says: \"Here's your drink, enjoy it!\"", evoke=True, short_len=True)

class Maid(LivingNpc):

    @call_periodically(45, 60)
    def do_random_move(self, ctx: Context) -> None:
        direction = self.select_random_move()
        if direction:
            self.move(direction.target, self, direction_names=direction.names)

class Patron(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(Patron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')
        
    def init(self) -> None:
        self.aliases = {"patron"}
        self.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=35)

    @call_periodically(75, 180)
    def do_idle_action(self, ctx: Context) -> None:
        """ Perform an idle action if a player is in the same location."""
        player_names = ctx.driver.all_players.keys()
        player_in_location = any(name == living.name for name in player_names for living in self.location.livings)
        if player_in_location:
            self.idle_action()

class RoamingPatron(Patron):


    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(RoamingPatron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')
        self.sitting = False
        
    @call_periodically(75, 120)
    def do_random_move(self, ctx: Context) -> None:
        if not self.sitting:
            if random.random() < 0.25:
                self.sitting = True
                self.tell_others("{Actor} sits down.", evoke=False, short_len=True)
            else:
                direction = self.select_random_move()
                if direction:
                    self.move(direction.target, self, direction_names=direction.names)
        elif random.random() < 0.5:
            self.sitting = False
            self.tell_others("{Actor} stands up.", evoke=False, short_len=True)
   
class Shanda(Patron):

    def init(self) -> None:
        self.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=65)


class Rat(Living):
    def init(self) -> None:
        super().init()
        self.aggressive = False
        self.stats.strength = 1
        self.stats.agility = 5
        self.title = "giant rat"
        self.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=25)
        self.target = None

    @call_periodically(10, 25)
    def do_idle_action(self, ctx: Context) -> None:
        if self.aggressive and self.target:
            self.start_attack(self.target)
        action = "{Actor} " + random.choice(["sniffs", "scratches", "hisses", "looks menacing"])
        if self.avatar:
           action = pad_text_for_avatar(action, self.name)
        self.tell_others(action, evoke=False, short_len=True)

    def handle_verb(self, parsed: ParseResult, actor: Living) -> bool:
        if parsed.verb == "attack":
            self.aggressive = True
            self.target = actor
            return True
        return False

        


norhardt = Patron("Norhardt", "m", age=56, descr="A grizzled old man, with parchment-like skin and sunken eyes. He\'s wearing ragged clothing and big leather boots. He\'s a formidable presence, commanding yet somber.", personality="An experienced explorer who is obsessed with finding the mythological Yeti which supposedly haunts these mountains. He won\'t stop talking about it.", short_descr="An old grizzled man sitting by the bar.")
norhardt.aliases = {"norhardt", "old man", "grizzled man"}

elid_gald = Patron("Elid Gald", "m", age=51, descr="A gentleman who's aged with grace. He has a slender appearance with regal facial features, and dark hair, but his (one) eye has a dangerous squint. The other is covered by a patch.", personality="Old Gold is a smooth-talking pick-pocket and charlatan. Although claiming to be retired, he never passes on an opportunity to relieve strangers of their valuables.", short_descr="A slender gentleman with a patch over one of his eyes, leaning against the wall.")
elid_gald.aliases = {"elid", "one eyed man", "gentleman"}
elid_gald.quest = Quest(name="The Map", reason="obtain the map Norhardt possesses", giver=elid_gald.name, type=QuestType.GIVE, target="map")

shanda = Shanda("Shanda Heard", "f", age=31, descr="A fierce looking woman, with a face as if chiseled from granite and a red bandana around her wild hair. She keeps an unblinking gaze on her surroundings.", personality="She's a heavy drinker and boaster, and for a drink she will spill tales of her conquests and battles and long lost love. She's feared by many but respected by all for her prowess in battle.", short_descr="A fierce looking woman sitting by a table, whose eyes seem to follow you.")
shanda.aliases = {"shanda", "fierce woman", "woman by table"}
shanda.quest = Quest(name="bring a rat skull", reason="prove your worth to Shanda", giver=shanda.name, type=QuestType.GIVE, target="rat_skull")

count_karta = Patron("Count of Karta", "m", age=43, descr="A hood shadows his facial features, but a prominent jaw juts out from beneath it. His mouth seems to be working constantly, as if muttering about something.", personality="Having fled from an attempt on his life, and being discredited, he has come here to plan his revenge. He seems to have gold and is looking for able bodies to help him.", short_descr="A mysterious man by the fire.")
count_karta.aliases = {"count", "karta", "mysterious man", "hooded man"}

urta = InnKeeper("Urta", "f", age=44, descr="A gruff, curvy woman with a long brown coat and bushy hair that reaches her waist. When not serving, she keeps polishing jugs with a dirty rag.", personality="She's the owner of The Prancing Llama, and of few words. But the words she speak are kind. She knows a little about all the patrons in her establishment.", short_descr="A curvy woman with long brown coat standing behind the bar.")
urta.aliases = {"bartender", "inn keeper", "curvy woman"}

brim = Maid("Brim", "f", age=22, descr="A timid girl with long dark blonde hair in a braid down her back. She carries trays and dishes back and forth.", personality="She's shy and rarely looks anyone in the eye. When she speaks, it is merely a whisper. She traveled up the mountain looking for work, and ended up serving at the Inn. She dreams of big adventures. She's afraid of the giant rats in the basement.", short_descr="A timid maid with a braid wearing a tunic and dirty apron.")
brim.aliases = {"maid", "timid girl", "serving girl"}


