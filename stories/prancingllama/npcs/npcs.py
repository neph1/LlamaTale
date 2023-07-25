from tale import mud_context
from tale.base import Item, Living, ParseResult
from tale.errors import ParseError, ActionRefused
from tale.llm_ext import LivingNpc

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

class Patron(LivingNpc):
    
    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str):
        super(Patron, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation='')
        
    def init(self) -> None:
        self.aliases = {"patron"}

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



norhardt = Patron("Norhardt", "m", age=56, descr="A grizzled old man, with parchment-like skin and sunken eyes. He\'s wearing ragged clothing and big leather boots. He\'s a formidable presence, commanding yet somber.", personality="An experienced explorer who is obsessed with finding the mythological Yeti which supposedly haunts these mountains. He won\'t stop talking about it.", short_descr="An old grizzled man sitting by the bar.")
norhardt.aliases = {"norhardt", "old man", "grizzled man"}

elid_gald = Patron("Elid Gald", "m", age=51, descr="A gentleman who's aged with grace. He has a slender appearance with regal facial features, and dark hair, but his (one) eye has a dangerous squint. The other is covered by a patch.", personality="Old Gold is a smooth-talking pick-pocket and charlatan. Although claiming to be retired, he never passes on an opportunity to relieve strangers of their valuables. He wishes to obtain the map Norhardt possesses.", short_descr="A slender gentleman with a patch over one of his eyes, leaning against the wall.")
elid_gald.aliases = {"elid", "one eyed man", "gentleman"}

shanda = Patron("Shanda Heard", "f", age=31, descr="A fierce looking woman, with a face like chiseled from granite and a red bandana around her wild hair. She keeps an unblinking gaze on her surroundings.", personality="She's a heavy drinker and boaster, and for a drink she will spill tales of her conquests and battles and long lost love. She's feared by many but respected by all for her prowess in battle.", short_descr="A fierce looking woman sitting by a table, whose eyes seem to follow you.")
shanda.aliases = {"shanda", "fierce woman", "woman by table"}

count_karta = Patron("Count of Karta", "m", age=43, descr="A hood shadows his facial features, but a prominent jaw juts out. His mouth seems to be working constantly, as if muttering about something.", personality="Having fled from an attempt on his life, and being discredited, he has come here to plan his revenge. He seems to have gold and is looking for able bodies to help him.", short_descr="A mysterious man by the fire.")
count_karta.aliases = {"count", "karta", "mysterious man"}

urta = InnKeeper("Urta", "f", age=44, descr="A gruff, curvy woman with a long brown coat and bushy hair that reaches her waist. When not serving, she keeps polishing jugs with a dirty rag.", personality="She's the owner of The Prancing Llama, and of few words. But the words she speak are kind. She knows a little about all the patrons in her establishment.", short_descr="A curvy woman with long brown coat standing behind the bar.")
urta.aliases = {"bartender", "inn keeper", "curvy woman"}


