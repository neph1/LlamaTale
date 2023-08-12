import random
from tale import mud_context

from tale.base import Item, Living, ParseResult
from tale.errors import ParseError, ActionRefused
from tale.lang import capital
from tale.llm_ext import LivingNpc
from tale.player import Player
from tale.util import call_periodically, Context
from tale import lang
from typing import Optional

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
        actor.tell("After handing %s the %s, %s gives you the %s." % (self.objective, price_str, self.subjective, drink.title), evoke=True, max_length=True)
        self.tell_others("{Actor} says: \"Here's your drink, enjoy it!\"", evoke=True, max_length=True)

class Maid(LivingNpc):

    @call_periodically(10, 20)
    def do_random_move(self, ctx: Context) -> None:
        direction = self.select_random_move()
        if direction:
            self.move(direction.target, self, direction_names=direction.names)

    @call_periodically(30, 60)
    def do_pick_up_dishes(self, ctx: Context) -> None:
        self.location.tell(f"{lang.capital(self.title)} wipes a table and picks up dishes.", evoke=False, max_length=True)


    
class Patron(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(Patron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')
        
    def init(self) -> None:
        self.aliases = {"patron"}

class Shanda(Patron):

    def allow_give_item(self, item: Item, actor: Optional[Living]) -> None:
        if item.name == "rat_skull":
            self.sentiments(actor.title, 'impressed')
            self.do_say(f'{actor.title} gives Shanda a giant rat skull', actor=actor)

class Guard(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(Patron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')
        
    def init(self) -> None:
        self.aliases = {"guard"}

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        if parsed.verb in AGGRESSIVE_VERBS:
            self.tell_others("{Actor} screams at you: 'What are you doing!?'")
            do_attack()
                
        elif parsed.verb in ("hello", "hi", "greet"):
            self.tell_others("{Actor} says 'Hello' to {target}.", target=actor)

    def do_attack(self) -> None:
        if not self.attacking:
            for liv in self.location.livings:
                if isinstance(liv, Player):
                    self.start_attack(self.location)
                    liv.tell("It may be a good idea to run away!")
                    self.attacking = True
                    
                    break

class Rat(Living):
    def init(self) -> None:
        super().init()
        self.aggressive = False
        self.stats.strength = 1
        self.stats.agility = 5

    @call_periodically(10, 25)
    def do_idle_action(self, ctx: Context) -> None:
        if random.random() < 0.5:
            self.tell_others("{Actor} hisses.", evoke=False, max_length=True)
        else:
            self.tell_others("{Actor} sniffs around.", evoke=False, max_length=True)


norhardt = Patron("Norhardt", "m", age=56, descr="A grizzled old man, with parchment-like skin and sunken eyes. He\'s wearing ragged clothing and big leather boots. He\'s a formidable presence, commanding yet somber.", personality="An experienced explorer who is obsessed with finding the mythological Yeti which supposedly haunts these mountains. He won\'t stop talking about it.", short_descr="An old grizzled man sitting by the bar.")
norhardt.aliases = {"norhardt", "old man", "grizzled man"}

elid_gald = Patron("Elid Gald", "m", age=51, descr="A gentleman who's aged with grace. He has a slender appearance with regal facial features, and dark hair, but his (one) eye has a dangerous squint. The other is covered by a patch.", personality="Old Gold is a smooth-talking pick-pocket and charlatan. Although claiming to be retired, he never passes on an opportunity to relieve strangers of their valuables. He wishes to obtain the map Norhardt possesses.", short_descr="A slender gentleman with a patch over one of his eyes, leaning against the wall.")
elid_gald.aliases = {"elid", "one eyed man", "gentleman"}

shanda = Shanda("Shanda Heard", "f", age=31, descr="A fierce looking woman, with a face as if chiseled from granite and a red bandana around her wild hair. She keeps an unblinking gaze on her surroundings.", personality="She's a heavy drinker and boaster, and for a drink she will spill tales of her conquests and battles and long lost love. She's feared by many but respected by all for her prowess in battle.", short_descr="A fierce looking woman sitting by a table, whose eyes seem to follow you.")
shanda.aliases = {"shanda", "fierce woman", "woman by table"}

count_karta = Patron("Count of Karta", "m", age=43, descr="A hood shadows his facial features, but a prominent jaw juts out from beneath it. His mouth seems to be working constantly, as if muttering about something.", personality="Having fled from an attempt on his life, and being discredited, he has come here to plan his revenge. He seems to have gold and is looking for able bodies to help him.", short_descr="A mysterious man by the fire.")
count_karta.aliases = {"count", "karta", "mysterious man", "hooded man"}

urta = InnKeeper("Urta", "f", age=44, descr="A gruff, curvy woman with a long brown coat and bushy hair that reaches her waist. When not serving, she keeps polishing jugs with a dirty rag.", personality="She's the owner of The Prancing Llama, and of few words. But the words she speak are kind. She knows a little about all the patrons in her establishment.", short_descr="A curvy woman with long brown coat standing behind the bar.")
urta.aliases = {"bartender", "inn keeper", "curvy woman"}

brim = Maid("Brim", "f", age=22, descr="A timid girl with long dark blonde hair in a braid down her back. She carries trays and dishes back and forth.", personality="She's shy and rarely looks anyone in the eye. When she speaks, it is merely a whisper. She traveled up the mountain looking for work, and ended up serving at the Inn. She dreams of big adventures.", short_descr="A timid maid with a braid wearing a tunic and dirty apron.")
brim.aliases = {"maid", "timid girl", "serving girl"}


