"""
A couple of basic items that go beyond the few base types.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import random
import textwrap
from typing import NamedTuple, FrozenSet, Optional, Union, List

from .. import lang, mud_context, util
from ..base import Item, Container, Weapon, Living, ParseResult, Location, ContainingType
from ..errors import ActionRefused, TaleError


__all__ = ["Boxlike", "Drink", "Food", "GameClock", "Light", "MagicItem", "Money",
           "Note", "Potion", "Scroll", "Trash", "Boat", "Fountain", "Health"]


class Boxlike(Container):
    """
    Container base class/prototype. The container can be opened/closed.
    Only if it is open you can put stuff in it or take stuff out of it.
    You can set a couple of txt attributes that change the visual aspect of this object.
    """
    def init(self) -> None:
        super().init()
        self.opened = False
        self.txt_title_closed = self._title
        self.txt_title_open_filled = "filled " + self._title
        self.txt_title_open_empty = "empty " + self._title
        self.txt_descr_closed = "The lid is closed."
        self.txt_descr_open_filled = "It is a %s, with an open lid, and there's something in it." % self.name
        self.txt_descr_open_empty = "It is a %s, with an open lid." % self.name

    @property
    def title(self) -> str:
        if self.opened:
            return self.txt_title_open_filled if self.inventory_size else self.txt_title_open_empty
        else:
            return self.txt_title_closed

    @title.setter
    def title(self, value: str) -> None:
        raise TaleError("you cannot set the title of a Boxlike because it is dynamic")

    @property
    def description(self) -> str:
        if self.opened:
            if self.inventory_size:
                return self.txt_descr_open_filled
            else:
                return self.txt_descr_open_empty
        else:
            return self.txt_descr_closed

    @description.setter
    def description(self, value: str) -> None:
        raise TaleError("you cannot set the description of a Boxlike because it is dynamic")

    def open(self, actor: Living, item: Item=None) -> None:
        if self.opened:
            raise ActionRefused("It's already open.")
        self.opened = True
        actor.tell("You opened the %s." % self.name)
        actor.tell_others("{Actor} opened the %s." % self.name)

    def close(self, actor: Living, item: Item=None) -> None:
        if not self.opened:
            raise ActionRefused("It's already closed.")
        self.opened = False
        actor.tell("You closed the %s." % self.name)
        actor.tell_others("{Actor} closed the %s." % self.name)

    @property
    def inventory(self) -> FrozenSet[Item]:
        if self.opened:
            return super().inventory
        else:
            raise ActionRefused("You can't peek inside, maybe you should open it first?")

    @property
    def inventory_size(self) -> int:
        if self.opened:
            return super().inventory_size
        else:
            raise ActionRefused("You can't peek inside, maybe you should open it first?")

    def insert(self, item: Union[Living, Item], actor: Optional[Living]) -> None:
        if self.opened:
            super().insert(item, actor)
        else:
            raise ActionRefused("You can't put things in the %s: you should open it first." % self.title)

    def remove(self, item: Union[Living, Item], actor: Optional[Living]) -> None:
        if self.opened:
            super().remove(item, actor)
        else:
            raise ActionRefused("You can't take things from the %s: you should open it first." % self.title)


class GameClock(Item):
    """
    A clock that is able to tell you the in-game time.
    """
    def init(self) -> None:
        super().init()
        self.use_locale = True

    @property
    def description(self) -> str:
        if not mud_context.config or not mud_context.config.display_gametime:
            return "It looks broken."
        if self.use_locale:
            display = mud_context.driver.game_clock.clock.strftime("%c")
        else:
            display = mud_context.driver.game_clock.clock.strftime("%Y-%m-%d %H:%M:%S")
        return "It reads: " + display

    @description.setter
    def description(self, value: str) -> None:
        raise TaleError("you cannot set the description of a GameClock because it is dynamic")

    def activate(self, actor: Living) -> None:
        raise ActionRefused("It's already running.")

    def deactivate(self, actor: Living) -> None:
        raise ActionRefused("Better to keep it running as it is.")

    def manipulate(self, verb: str, actor: Living) -> None:
        actor.tell("%s the %s won't have much effect." % (lang.capital(lang.fullverb(verb)), self.title))

    def read(self, actor: Living) -> None:
        actor.tell(self.description)


class Note(Item):
    """
    A (paper) note with or without something written on it. You can read it.
    """
    def init(self) -> None:
        super().init()
        self._text = "There is nothing written on it."

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, text: str) -> None:
        self._text = textwrap.dedent(text)

    def read(self, actor: Living) -> None:
        actor.tell("The %s reads:" % self.title, end=True)
        actor.tell(self.text)


class Light(Item):
    def init(self) -> None:
        super().init()
        self.capacity = 0   # hours (-1=eternal, 0=burned out)


class Scroll(Item):
    def init(self) -> None:
        super().init()
        self.spell_level = 0   # level of spells
        self.spells = frozenset()   # type: FrozenSet[str]

    def read(self, actor: Living) -> None:
        actor.tell("The %s reads:" % self.title, end=True)
        actor.tell("It contains the following spells: " + str(self.spells))   # @todo spell descriptions


class MagicItem(Weapon):
    def init(self) -> None:
        super().init()
        self.spell_level = 0
        self.capacity = 0
        self.remaining = 0
        self.spell = None


class Trash(Item):
    """Trash -- junked by cleaners, not bought by any shopkeeper."""
    pass


class Drink(Item):
    drinkeffects = NamedTuple("drinkeffects", [("drunkness", int), ("fullness", int), ("thirst", int)])
    drinktypes = {'water':        drinkeffects(0, 1, 10),
                  'beer':         drinkeffects(3, 2, 5),
                  'wine':         drinkeffects(5, 2, 5),
                  'ale':          drinkeffects(2, 2, 5),
                  'darkale':      drinkeffects(1, 2, 5),
                  'whisky':       drinkeffects(6, 1, 4),
                  'lemonade':     drinkeffects(0, 1, 8),
                  'firebreath':   drinkeffects(10, 0, 0),
                  'localspecial': drinkeffects(3, 3, 3),
                  'slime':        drinkeffects(0, 4, -8),
                  'milk':         drinkeffects(0, 3, 6),
                  'tea':          drinkeffects(0, 1, 6),
                  'coffee':       drinkeffects(0, 1, 6),
                  'blood':        drinkeffects(0, 2, -1),
                  'saltwater':    drinkeffects(0, 1, -2),
                  'clearwater':   drinkeffects(0, 0, 13),
                  }

    def init(self) -> None:
        super().init()
        self.contents = "water"
        self.capacity = 1
        self.quantity = 0
        self.affect_drunkness = 0
        self.affect_fullness = 0
        self.affect_thirst = 0
        self.poisoned = False

    def consume(self, actor: 'Living'):
        if self not in actor.inventory:
            raise ActionRefused("You don't have that.")
        actor.stats.hp += self.affect_thirst
        actor.tell("You drink the %s." % (self.title), evoke=True, short_len=True)
        actor.tell_others("{Actor} drinks the %s." % (self.title))
        self.destroy(util.Context.from_global())
        return True


class Potion(Item):
    def init(self) -> None:
        super().init()
        self.spell_level = 0
        self.spells = frozenset()   # type: FrozenSet[str]


class Food(Item):
    def init(self) -> None:
        super().init()
        self.affect_fullness = 1
        self.poisoned = False

    def consume(self, actor: 'Living'):
        if self not in actor.inventory:
            raise ActionRefused("You don't have that.")
        actor.stats.hp += self.affect_fullness
        actor.tell("You eat the %s." % (self.title), evoke=True, short_len=True)
        actor.tell_others("{Actor} eats the %s." % (self.title))
        self.destroy(util.Context.from_global())
        return True


class Money(Item):
    """Some money that is lying around. When picked up, it's added to the money the creature is carrying."""
    def __init__(self, name: str, value: float, *, title: str="", short_descr: str="") -> None:
        mft = mud_context.driver.moneyfmt
        if value <= 0.0:
            raise ValueError("attempt to create money with value <= 0")
        if not title:
            if value <= 1.0:
                title = "tiny amount of "
            elif value <= 10:
                title = "tiny pile of "
            elif value <= 20:
                title = "handful of "
            elif value <= 75:
                title = "little pile of "
            elif value <= 200:
                title = "small pile of "
            elif value <= 1000:
                title = "pile of "
            elif value <= 5000:
                title = "big pile of "
            elif value <= 10000:
                title = "large heap of "
            elif value <= 20000:
                title = "huge mound of "
            elif value <= 75000:
                title = "enormous mound of "
            elif value <= 150000:
                title = "small mountain of "
            elif value <= 250000:
                title = "mountain of "
            elif value <= 500000:
                title = "huge mountain of "
            elif value <= 1000000:
                title = "enormous mountain of "
            else:
                title = "absolutely colossal mountain of "
            title += mft.money_name
        if value < 10:
            descr = "There is " + mft.display(value) + "."
        elif value < 100:
            descr = "There is about " + mft.display(10 * (value // 10)) + "."
        elif value < 1000:
            descr = "It looks to be about " + mft.display(100 * (value // 100)) + "."
        elif value < 100000:
            v = value // 1000
            guess = 1000 * (v + random.randint(int(-v / 3), int(v / 3)))
            descr = "You guess it is, maybe, " + mft.display(guess) + "."
        else:
            descr = "It is A LOT of " + mft.money_name + "."
        if short_descr:
            short_descr = lang.capital(short_descr)
        else:
            short_descr = lang.A(title) + " is lying here."
        super().__init__(name, title, descr=descr, short_descr=short_descr)
        self.value = value

    def __repr__(self):
        return "<%s '%s' value=%f #%d @ 0x%x>" % (self.__class__.__name__, self.name, self.value, self.vnum, id(self))

    def __float__(self):
        return self.value

    def add_to_location(self, location: Location, actor: Living) -> None:
        # if there's already some money in the location, add it to the pile. If not, just drop this money object.
        assert self.value > 0.0
        if self in location.items:
            raise TaleError("money is already in the location")
        for m in location.items:
            if isinstance(m, Money):
                m.value += self.value
                break
        else:
            location.insert(self, actor)

    def notify_moved(self, source_container: ContainingType, target_container: ContainingType, actor: Optional[Living]) -> None:
        # make sure that when the money is moved into a living, it is discarded and its value is added to the living's money.
        if isinstance(target_container, Living):
            target_container.remove(self, actor)
            target_container.money += self.value
            self.destroy(util.Context.from_global())


class Boat(Item):
    def init(self) -> None:
        super().init()


# class Wearable(Item):
#     def init(self) -> None:
#         super().init()


class Fountain(Item):
    def init(self) -> None:
        super().init()
        self.contents = "water"
        self.capacity = 1
        self.quantity = 0
        self.poisoned = False


newspaper = Note("newspaper", descr="""
    Looking at the date on the front page, you see that it is last week's newspaper.
    Perhaps by reading the paper you can see if it still has something interesting to say.
    The paper faintly smells of fish though.""")
newspaper.text = """
        "Last year's Less Popular Sports."
        "Any fan will tell you the big-name leagues aren't the whole sporting world.
         As time expired on last year, we take a look at major accomplishments, happenings,
         and developments in the less popular sports."
        It looks like a boring article, and you have better things to do."""
newspaper.aliases.add("paper")

rock = Item("rock", "large rock", descr="A pretty large rock. It looks extremely heavy.")
gem = Item("gem", "sparkling gem", descr="Light sparkles from this beautiful gem.")
diamond = Item("diamond", "large blinking diamond", descr="This is the biggest diamond you have ever seen.")
pouch = Container("pouch", "small leather pouch", descr="It is opened and closed with a thin leather strap.")
trashcan = Boxlike("trashcan", "dented steel trashcan")
gameclock = GameClock("clock", "ticking clock", short_descr="The clock makes ticking noises.")


class WoodenYstick(Item):
    # this Y-stick is part of a catapult .
    def combine(self, other: List[Item], actor: Living) -> Optional[Item]:
        if len(other) == 1:
            thing = other[0]
            if isinstance(thing, ElasticBand):
                # combine elastic band and Y-stick into .... the catapult
                catapult = Catapult("catapult", "flimsy catapult",
                                    descr="A flimsy looking catapult. It looks like it might just work though!")
                catapult.aliases.add("flimsy catapult")
                return catapult
        return None


class ElasticBand(Item):
    # the band is part of a catapult.
    # This is a class to be able to identify items of this type easily when combining stuff.
    pass


class Catapult(Weapon):
    # you can create this directly but it is more fun if it is created by combining a Y-stick and an elastic band.
    def init(self):
        super().init()
        self.value = 15.0
        self.verbs = {"shoot": "Fire the weapon!"}

    def handle_verb(self, parsed: ParseResult, actor: Living) -> bool:
        if parsed.verb == "shoot":
            if self in actor:
                actor.tell("While the weapon is fine, you don't have munition. Shooting is not happening.")
                actor.tell_others("{Actor} fiddles a bit with %s %s." % (actor.possessive, self.title))
            else:
                actor.tell("You see the weapon lying there. To use it, you'll have to pick it up first though.")
            return True
        return False


woodenYstick = WoodenYstick("stick", "wooden y-shaped stick",
                            descr="A firm, Y-shaped wooden stick. You can hold it pretty comfortably.")
woodenYstick.value = 4
elastic_band = ElasticBand("band", "large elastic band",
                           descr="It is a pretty strong and large elastic band. "
                                 "It's not the type used to hold small packages but rather looks "
                                 "like it came off a catapult of some sort.")
elastic_band.value = 2.2
elastic_band.aliases.add("elastic")
elastic_band.aliases.add("elastic band")

class Health(Item):
    """ A health item that can be eaten or drank."""

    def init(self, healing_effect = 0) -> None:
        super().init()
        self.healing_effect = healing_effect

    def consume(self, actor: 'Living'):
        if self not in actor.inventory:
            raise ActionRefused("You don't have that.")
        actor.stats.hp += self.healing_effect
        actor.tell("You take the %s and feel better." % (self.title), evoke=True, short_len=True)
        actor.tell_others("{Actor} takes the %s." % (self.title))
        self.destroy(util.Context.from_global())
        return True
        