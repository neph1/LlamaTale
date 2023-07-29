"""
Mudlib base objects.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)

object hierarchy::

    MudObject (abstract base class, don't use directly)
      |
      +-- Location
      |
      +-- Item
      |     |
      |     +-- Weapon
      |     +-- Armour
      |     +-- Container
      |     +-- Key
      |
      +-- Living (abstract base class, don't use directly)
      |     |
      |     +-- Player
      |     +-- NPC
      |          |
      |          +-- Shopkeeper
      |
      +-- Exit
            |
            +-- Door


Every object that can hold other objects does so in its "inventory" (a set).
You can't access it directly, object.inventory returns a frozenset copy of it.
Except Location: it separates the items and livings it contains internally.
Use its enter/leave methods instead.
"""

import builtins
import copy
import random
import re
from weakref import WeakValueDictionary
from collections import OrderedDict
from textwrap import dedent
from types import ModuleType
from typing import Iterable, Any, Sequence, Optional, Set, Dict, Union, FrozenSet, Tuple, List, Type, no_type_check

from . import lang
from . import mud_context
from . import pubsub
from . import races
from . import util
from . import story
from . import verbdefs
from .errors import ActionRefused, ParseError, LocationIntegrityError, TaleError, UnknownVerbException, NonSoulVerb

__all__ = ["MudObject", "Armour", 'Container', "Door", "Exit", "Item", "Living", "Stats", "Location", "Weapon", "Key", "Soul"]

pending_actions = pubsub.topic("driver-pending-actions")
pending_tells = pubsub.topic("driver-pending-tells")
async_dialogs = pubsub.topic("driver-async-dialogs")


ParsedWhoType = Union['Living', 'Item', 'Exit']
ContainingType = Union['Location', 'Container', 'Living']


class ParseResult:
    """Captures the result of a parsed input line."""
    class WhoInfo:
        """parse details of this Who in the line"""
        def __init__(self, seqnr: int = 0) -> None:
            self.sequence = seqnr  # at what position does this Who occur
            self.previous_word = ""  # what is the word preceding it

        def __str__(self) -> str:
            return "[seq=%d, prev_word=%s]" % (self.sequence, self.previous_word)

    class WhoInfoOrderedDict(OrderedDict):
        def __missing__(self, key):
            self[key] = value = ParseResult.WhoInfo()
            return value

    def __init__(self, verb: str, *, adverb: str = "", message: str = "", bodypart: str = "", qualifier: str = "",
                 args: List[str] = None, who_info: WhoInfoOrderedDict = None,
                 unrecognized: List[str] = None, unparsed: str = "", who_list: List = None) -> None:
        self.verb = verb
        self.adverb = adverb
        self.message = message
        self.bodypart = bodypart
        self.qualifier = qualifier
        self.args = args or []
        self.unrecognized = unrecognized or []
        self.unparsed = unparsed
        assert who_info is None or isinstance(who_info, OrderedDict)  # otherwise parser order gets messed up
        self.who_info = who_info or ParseResult.WhoInfoOrderedDict()
        if who_list and not self.who_info:
            # initialize the who_info dictionary from the given list and check for duplicates
            # if who_info is ALSO provided, we ignore who_list.
            duplicates = set()
            for sequence, who in enumerate(who_list):
                if who in self.who_info:
                    duplicates.add(who)
                self.who_info[who] = ParseResult.WhoInfo(sequence)
            if duplicates:
                raise ParseError("You can do only one thing at the same time with {}. Try to use multiple separate commands instead."
                                 .format(lang.join(s.name for s in duplicates)))
        self.who_count = len(self.who_info)

    @property
    def who_1(self) -> ParsedWhoType:
        """Gets the first occurring ParsedWhoType from the parsed line (or None if it doesn't exist)"""
        return next(iter(self.who_info)) if self.who_info else None     # type: ignore

    @property
    def who_12(self) -> Tuple[ParsedWhoType, ParsedWhoType]:
        """
        Returns a tuple (ParsedWhoType, ParsedWhoType) representing the first two occurring Whos in the parsed line.
        If no such subject exists, None is returned in its place.
        """
        whos = list(self.who_info)    # this is in order because who_info is OrderedDict
        return tuple((whos + [None, None])[:2])  # type: ignore

    @property
    def who_123(self) -> Tuple[ParsedWhoType, ParsedWhoType, ParsedWhoType]:
        """
        Returns a tuple (ParsedWhoType, ParsedWhoType, ParsedWhoType) representing the first three occurring Whos in the parsed line.
        If no such subject exists, None is returned in its place.
        """
        whos = list(self.who_info)    # this is in order because who_info is OrderedDict
        return tuple((whos + [None, None, None])[:3])  # type: ignore

    @property
    def who_last(self) -> Optional[ParsedWhoType]:
        """Gets the last occurring ParsedWhoType on the line (or None if there wasn't any)"""
        if self.who_info:
            return list(self.who_info)[-1]
        return None

    def __str__(self) -> str:
        who_info_str = [" %s->%s" % (living.name, info) for living, info in self.who_info.items()]
        s = [
            "ParseResult:",
            " verb=%s" % self.verb,
            " qualifier=%s" % self.qualifier,
            " adverb=%s" % self.adverb,
            " bodypart=%s" % self.bodypart,
            " message=%s" % self.message,
            " args=%s" % self.args,
            " unrecognized=%s" % self.unrecognized,
            " who_count=%d" % self.who_count,
            " who_info=%s" % "\n   ".join(who_info_str),
            " who_123=%s" % str(self.who_123),
            " who_last=%s" % str(self.who_last),
            " unparsed=%s" % self.unparsed
        ]
        return "\n".join(s)


class MudObjRegistry:
    # the vnum machinery for all created MudObjects:
    seq_nr = 1
    all_items = WeakValueDictionary()       # type: WeakValueDictionary[int, Item]
    all_livings = WeakValueDictionary()     # type: WeakValueDictionary[int, Living]
    all_locations = WeakValueDictionary()   # type: WeakValueDictionary[int, Location]
    all_exits = WeakValueDictionary()       # type: WeakValueDictionary[int, Exit]

    @staticmethod
    def track_vnum(instance: Any, fix_clones: bool=False):
        # create and store a new unique vnum for this mudobject
        instance.vnum = MudObjRegistry.seq_nr
        MudObjRegistry.seq_nr += 1
        if isinstance(instance, Item):
            MudObjRegistry.all_items[instance.vnum] = instance        # type: ignore
        elif isinstance(instance, Living):
            MudObjRegistry.all_livings[instance.vnum] = instance      # type: ignore
        elif isinstance(instance, Exit):
            MudObjRegistry.all_exits[instance.vnum] = instance        # type: ignore
        elif isinstance(instance, Location):
            MudObjRegistry.all_locations[instance.vnum] = instance    # type: ignore
        else:
            raise TypeError("weird MudObj subtype: " + str(type(instance)))
        if fix_clones:
            # the 'clone' command consumes too many vnums because of the way deepcopy works.
            # try to find the double registration and remove it.
            pid = instance.vnum - 1
            existing = MudObjRegistry.all_items.get(pid, None)  # type: Optional[MudObject]
            if existing is instance:
                del MudObjRegistry.all_items[pid]
            else:
                existing = MudObjRegistry.all_livings.get(pid, None)
                if existing is instance:
                    del MudObjRegistry.all_livings[pid]
                else:
                    existing = MudObjRegistry.all_exits.get(pid, None)
                    if existing is instance:
                        del MudObjRegistry.all_exits[pid]
                    else:
                        existing = MudObjRegistry.all_locations.get(pid, None)
                        if existing is instance:
                            del MudObjRegistry.all_locations[pid]

    @classmethod
    @no_type_check
    def create_object(cls, objclass: Type, *vargs, **kwargs) -> Any:
        vnum = kwargs.pop("vnum", 0)
        if vnum:
            # create a new item/living with given vnum, check if vnum is still available.
            if issubclass(objclass, Item):
                if vnum in MudObjRegistry.all_items:
                    raise TaleError("item with vnum %d already exists: %r" % (vnum, repr(MudObjRegistry.all_items[vnum])))
                thing = objclass(*vargs, **kwargs)
                del MudObjRegistry.all_items[thing.vnum]
                thing.vnum = vnum
                MudObjRegistry.all_items[vnum] = thing
            elif issubclass(objclass, Living):
                if vnum in MudObjRegistry.all_livings:
                    raise TaleError("living with vnum %d already exists: %r" % (vnum, repr(MudObjRegistry.all_livings[vnum])))
                thing = objclass(*vargs, **kwargs)
                del MudObjRegistry.all_livings[thing.vnum]
                thing.vnum = vnum
                MudObjRegistry.all_livings[vnum] = thing
            elif issubclass(objclass, Exit):
                raise TypeError("creation of Exit for specific vnum is not supported")
            elif issubclass(objclass, Location):
                raise TypeError("creation of Location for specific vnum is not supported")
            else:
                raise TypeError("weird MudObj subtype: " + str(objclass))
            cls.seq_nr = max(cls.seq_nr, thing.vnum + 1)
            return thing
        else:
            # just create a new object with the next available vnum.
            return objclass(*vargs, **kwargs)


class MudObject:
    """
    Root class of all objects in the mud world
    All objects have an identifying short name (will be lowercased),
    an optional short title (shown when listed in a room -- don't use 'a' or 'the' or pronouns),
    and an optional longer description (shown when explicitly 'examined').
    The long description is 'dedented' first, which means you can put it between triple-quoted-strings easily.
    Short_description is also optional, and is used in the text when a player 'looks' around.
    If it's not set, a generic 'look' message will be shown (something like "XYZ is here").

    Extra descriptions (extra_desc) are used to make stuff more interesting and interactive
    Extra descriptions are accessed by players when they type ``look at <thing>``
    where <thing> is any keyword you choose.  For example, you might write a room description which
    includes the tantalizing sentence, ``The wall looks strange here.``
    Using extra descriptions, players could then see additional detail by typing
    ``look at wall.``  There can be an unlimited number of Extra Descriptions.
    """
    subjective = "it"
    possessive = "its"
    objective = "it"
    gender = "n"

    @staticmethod
    def __new__(cls, *args, **kwargs):
        if cls is MudObject:
            raise TypeError("don't create MudObject directly, use one of the subclasses")
        instance = super().__new__(cls)
        MudObjRegistry.track_vnum(instance)
        return instance

    def __init__(self, name: str, title: str = "", *, descr: str = "", short_descr: str = "") -> None:
        self.vnum = self.vnum   # type: int  # set by mudregistry numbering logic
        self._extradesc = {}  # type: Dict[str,str]
        self.name = self._description = self._title = self._short_description = ""
        self.init_names(name, title, descr, short_descr)
        self.aliases = set()  # type: Set[str]
        # any custom verbs that need to be recognised (verb->docstring mapping), verb handling is done via handle_verb() callbacks.
        self.verbs = {}  # type: Dict[str, str]
        # register all periodical tagged methods
        self.story_data = {}  # type: Dict[Any, Any]   # not used by Tale itself, story can put custom data here. Use builtin types only.
        self.init()
        if util.get_periodicals(self):
            if mud_context.driver is None:
                raise TaleError("Attempt to create MudObject while Driver hasn't been properly initialized yet. "
                                "Possible cause is importing zone or npc module files that create these objects "
                                "early before the driver itself loads them.")
            mud_context.driver.register_periodicals(self)

    def init(self) -> None:
        """
        Secondary initialization/customization. Invoked after all required initialization has been done.
        You can easily override this in a subclass. It is not needed to call the MudObject super class init().
        """
        pass

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    @property
    def short_description(self) -> str:
        return self._short_description

    @short_description.setter
    def short_description(self, value: str) -> None:
        self._short_description = value

    @property
    def extra_desc(self) -> Dict[str, str]:
        return self._extradesc

    @extra_desc.setter
    def extra_desc(self, value: Dict[str, str]) -> None:
        assert isinstance(value, dict)
        self._extradesc = value

    def init_names(self, name: str, title: str, descr: str, short_descr: str) -> None:
        """(re)set the name and description attributes"""
        self.name = name.lower()
        if title:
            self._check_title(title)
        self._title = title or name
        self._description = dedent(descr).strip() if descr else ""
        self._short_description = short_descr.strip() if short_descr else ""
        self._extradesc = {}   # maps keyword to description

    def _check_title(self, title: str) -> None:
        w = title.partition(" ")[0].lower()
        if w in {"a", "an", "the"}:
            raise TaleError("title cannot start with an article: '%s' (these are added automatically)" % title)

    def add_extradesc(self, keywords: Set[str], description: str) -> None:
        """For the set of keywords, add the extra description text"""
        for keyword in keywords:
            self._extradesc[keyword] = description

    def __repr__(self):
        return "<%s '%s' #%d @ 0x%x>" % (self.__class__.__name__, self.name, self.vnum, id(self))

    def destroy(self, ctx: Optional[util.Context]) -> None:
        """Common cleanup code that needs to be called when the object is destroyed"""
        mud_context.driver.remove_deferreds(self)

    def wiz_clone(self, actor: 'Living') -> 'MudObject':
        """clone the thing (performed by a wizard)"""
        raise ActionRefused("Can't clone " + lang.a(self.__class__.__name__))

    def wiz_destroy(self, actor: 'Living', ctx: util.Context) -> None:
        """destroy the thing (performed by a wizard)"""
        raise ActionRefused("Can't destroy " + lang.a(self.__class__.__name__))

    def show_inventory(self, actor: 'Living', ctx: util.Context) -> None:
        """show the object's inventory to the actor"""
        raise ActionRefused("You can't look inside of that.")

    def activate(self, actor: 'Living') -> None:
        # called from the activate command, override if your object needs to act on this.
        raise ActionRefused("You can't activate that.")

    def deactivate(self, actor: 'Living') -> None:
        # called from the deactivate command, override if your object needs to act on this.
        raise ActionRefused("You can't deactivate that.")

    def manipulate(self, verb: str, actor: 'Living') -> None:
        # called from the various manipulate commands, override if your object needs to act on this.
        # verb: move, shove, swivel, shift, manipulate, rotate, press, poke, push, turn
        raise ActionRefused("You can't %s that." % verb)

    def move(self, target: ContainingType, actor: 'Living'=None,
             *, silent: bool=False, is_player: bool=False, verb: str="move", direction_names: Sequence[str]=None) -> None:
        # move the MudObject to a different place (location, container, living).
        raise ActionRefused("You can't %s that." % verb)

    def read(self, actor: 'Living') -> None:
        # called from the read command, override if your object needs to act on this.
        raise ActionRefused("There's nothing to read.")

    def insert(self, obj: Union['Living', 'Item'], actor: Optional['Living']) -> None:
        raise ActionRefused("You can't put things in there.")

    def remove(self, obj: Union['Living', 'Item'], actor: Optional['Living']) -> None:
        raise ActionRefused("You can't take things from there.")

    def handle_verb(self, parsed: ParseResult, actor: 'Living') -> bool:
        """Handle a custom verb (specified in the verbs dict). Return True if handled, False if not handled."""
        return False

    def notify_action(self, parsed: ParseResult, actor: 'Living') -> None:
        """
        Notify the object of an action performed by someone.
        This can be any verb, command, soul emote, custom verb.
        Uncompleted actions (error, or ActionRefused) are ignored.
        Custom verbs are notified however, even if they were already handled by handle_verb!
        It's good practice to first do a check like this::

            if actor is self or parsed.verb in self.verbs:
                return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        """
        pass


class Item(MudObject):
    """
    Root class of all Items in the mud world. Items are physical objects.
    Items can usually be moved, carried, or put inside other items.
    They have a name and optional short and longer descriptions.
    Regular items cannot contain other things, so it makes to sense
    to check containment.
    """

    def __init__(self, name: str, title: str = "", *, descr: str = "", short_descr: str = "") -> None:
        self.contained_in = None   # type: Optional[ContainingType]
        self.default_verb = "examine"
        self.value = 0.0   # what the item is worth
        self.rent = 0.0    # price to keep in store / day
        self.weight = 0.0  # some abstract unit
        self.takeable = True    # can this item be taken/picked up?
        super().__init__(name, title=title, descr=descr, short_descr=short_descr)

    def init(self) -> None:
        """
        Secondary initialization/customization. Invoked after all required initialization has been done.
        You can easily override this in a subclass. It is not needed to call the Item super class init().
        """
        pass

    def __contains__(self, item: 'Item') -> bool:
        raise ActionRefused("You can't look inside of that.")

    @property
    def location(self) -> Optional['Location']:
        if not self.contained_in:
            return None
        if isinstance(self.contained_in, Location):
            return self.contained_in
        elif isinstance(self.contained_in, (Living, Container)):
            return self.contained_in.location
        else:
            raise TaleError("inconsistent contained_in type")

    @location.setter
    def location(self, value: 'Location') -> None:
        if value is None or isinstance(value, Location):
            self.contained_in = value
        else:
            raise TypeError("can only set item's location to a Location, for other container types use item.contained_in")

    @property
    def inventory(self) -> FrozenSet['Item']:
        raise ActionRefused("You can't look inside of that.")

    @property
    def inventory_size(self) -> int:
        raise ActionRefused("You can't look inside of that.")

    def move(self, target: ContainingType, actor: 'Living'=None,
             *, silent: bool=False, is_player: bool=False, verb: str="move", direction_names: Sequence[str]=None) -> None:
        """
        Leave the container the item is currently in, enter the target container (transactional).
        Because items can move on various occasions, there's no message being printed.
        The silent and is_player arguments are not used when moving items -- they're used
        for the movement of livings.
        """
        self.allow_item_move(actor, verb)
        source_container = self.contained_in
        if source_container:
            source_container.remove(self, actor)
        try:
            target.insert(self, actor)
            if source_container:
                self.notify_moved(source_container, target, actor)
        except:
            # insert in target failed, put back in original location
            if source_container:
                source_container.insert(self, actor)
            raise

    def notify_moved(self, source_container: ContainingType, target_container: ContainingType, actor: Optional['Living']) -> None:
        """Called when the item has been moved from one place to another"""
        pass

    def allow_item_move(self, actor: Optional['Living'], verb: str="move") -> None:
        """Does the item allow to be moved (picked up, given away) by someone? (yes; no ActionRefused is raised)"""
        if not self.takeable:
            raise ActionRefused("You can't %s %s." % (verb, self.title))

    def open(self, actor: 'Living', item: 'Item'=None) -> None:
        raise ActionRefused("You can't open that.")

    def close(self, actor: 'Living', item: 'Item'=None) -> None:
        raise ActionRefused("You can't close that.")

    def lock(self, actor: 'Living', item: 'Item'=None) -> None:
        raise ActionRefused("You can't lock that.")

    def unlock(self, actor: 'Living', item: 'Item'=None) -> None:
        raise ActionRefused("You can't unlock that.")

    def combine(self, other: List['Item'], actor: 'Living') -> Optional['Item']:
        """Combine the other thing(s) with us.
        If successful, return the new Item to replace us + all other items with.
        (so 'other' must NOT contain any item not used in combining the things, or it will be silently lost!)
        If stuff cannot be combined, return None (or raise an ActionRefused with a particular message).
        """
        if other:
            raise ActionRefused("You can't combine those.")
        raise ActionRefused("That makes no sense.")

    @util.authorized("wizard")
    def wiz_clone(self, actor: 'Living', make_clone: bool=True) -> 'Item':
        item = self.clone() if make_clone else self
        actor.insert(item, actor)
        actor.tell("Cloned into: " + repr(item) + " (spawned in your inventory)")
        actor.tell_others("{Actor} conjures up %s, and quickly pockets it." % lang.a(item.title))
        return item

    @util.authorized("wizard")
    def wiz_destroy(self, actor: 'Living', ctx: util.Context) -> None:
        if self in actor:
            actor.remove(self, actor)
        else:
            actor.location.remove(self, actor)
        self.destroy(ctx)

    def show_inventory(self, actor: 'Living', ctx: util.Context) -> None:
        """show the object's contents to the actor"""
        if self.inventory:
            actor.tell("It contains:", end=True)
            for item in self.inventory:
                actor.tell("  " + item.title, format=False)
        else:
            actor.tell("It's empty.")

    @staticmethod
    def search_item(name: str, collection: Iterable['Item']) -> Optional['Item']:
        """
        Searches an item (by name) in a collection of Items.
        Returns the first match (or None if nothing found). Also considers aliases and titles.
        """
        name = name.lower()
        items = [i for i in collection if i.name == name]
        if not items:
            # try the aliases or titles
            items = [i for i in collection if name in i.aliases or i.title.lower() == name]
        return items[0] if items else None

    def clone(self) -> 'Item':
        """
        Create a copy of an existing Item.
        Only allowed when it has an empty inventory (to avoid problems).
        Caller has to make sure the resulting copy is moved to its proper destination location.
        """
        try:
            if self.inventory_size > 0:
                raise ValueError("can't clone something that has other stuff in it")
        except ActionRefused:
            pass
        # avoid deepcopying the location
        location, self.location = self.location, None
        duplicate = copy.deepcopy(self)
        self.location = duplicate.location = location
        MudObjRegistry.track_vnum(duplicate, fix_clones=True)   # deepcopy resets initially given vnum so hand out a new one
        mud_context.driver.register_periodicals(duplicate)
        return duplicate


class Weapon(Item):
    """
    An item that can be wielded by a Living (i.e. present in a weapon itemslot),
    and that can be used to attack another Living.
    """
    pass


class Armour(Item):
    """
    An item that can be worn by a Living (i.e. present in an armour itemslot)
    """
    pass


class Location(MudObject):
    """
    A location in the mud world. Livings and Items are in it.
    Has connections ('exits') to other Locations.
    You can test for containment with 'in': item in loc, npc in loc
    """
    def __init__(self, name: str, descr: str="") -> None:
        self.name = name
        self.livings = set()  # type: Set[Living] # set of livings in this location
        self.items = set()    # type: Set[Item] # set of all items in the room
        self.exits = {}       # type: Dict[str, Exit] # dictionary of all exits: exit_direction -> Exit object with target & descr
        super().__init__(name, descr=descr)
        self.name = name      # make sure we preserve the case; base object overwrites it in lowercase

    def __contains__(self, obj: Union['Living', Item]) -> bool:
        return obj in self.livings or obj in self.items

    def init_inventory(self, objects: Iterable[Union[Item, 'Living']]) -> None:
        """Set the location's initial item and livings 'inventory'"""
        if len(self.items) > 0 or len(self.livings) > 0:
            raise LocationIntegrityError("clobbering existing inventory", "", None, self)
        for obj in objects:
            self.insert(obj, None)

    def destroy(self, ctx: Optional[util.Context]) -> None:
        super().destroy(ctx)
        for living in self.livings:
            if living.location is self:
                living.location = _limbo
        self.livings.clear()
        self.items.clear()
        self.exits.clear()

    def add_exits(self, exits: Iterable['Exit']) -> None:
        """Adds every exit from the sequence as an exit to this room."""
        for exit in exits:
            exit.bind(self)
            # note: we're not simply adding it to the .exits dict here, because
            # the exit may have aliases defined that it wants to be known as also.

    def get_wiretap(self) -> pubsub.Topic:
        """get a wiretap for this location"""
        return pubsub.topic(("wiretap-location", "%s#%d" % (self.name, self.vnum)))

    def tell(self, room_msg: str, exclude_living: 'Living'=None, specific_targets: Set[Union[ParsedWhoType]]=None,
             specific_target_msg: str="", evoke=True, max_length=True) -> None:
        """
        Tells something to the livings in the room (excluding the living from exclude_living).
        This is just the message string! If you want to react on events, consider not doing
        that based on this message string. That will make it quite hard because you need to
        parse the string again to figure out what happened... Use handle_verb / notify_action instead.
        """
        targets = specific_targets or set()
        assert isinstance(targets, (frozenset, set, list, tuple))
        assert exclude_living is None or isinstance(exclude_living, Living)
        for living in self.livings:
            if living == exclude_living:
                continue
            if living in targets:
                living.tell(specific_target_msg, evoke=evoke, max_length=max_length)
            else:
                living.tell(room_msg, evoke=evoke, max_length=max_length)
        if room_msg:
            tap = self.get_wiretap()
            tap.send((self.name, room_msg))

    def message_nearby_locations(self, message: str) -> None:
        """
        Tells a message to adjacent locations, where adjacent is defined by being connected via an exit.
        If the adjacent location has an obvious returning exit to the source location (via one of the
        most obvious routes n/e/s/w/up/down/etc.), it hen also get information on what direction
        the sound originated from.  This is used for loud noises such as yells!
        """
        if self.exits:
            yelled_locations = set()  # type: Set[Location]
            for exit in self.exits.values():
                if exit.target in yelled_locations:
                    continue   # skip double locations (possible because there can be multiple exits to the same location)
                if exit.target is not self:
                    exit.target.tell(message, evoke=True, max_length=True)
                    yelled_locations.add(exit.target)
                    for direction, return_exit in exit.target.exits.items():
                        if return_exit.target is self:
                            if direction in {"north", "east", "south", "west",
                                             "northeast", "northwest", "southeast", "southwest",
                                             "north east", "north west", "south east", "south west",
                                             "left", "right", "front", "back"}:
                                direction = "the " + direction
                            elif direction in {"up", "above", "upstairs"}:
                                direction = "above"
                            elif direction in {"down", "below", "downstairs"}:
                                direction = "below"
                            else:
                                continue  # no direction description possible for this exit
                            exit.target.tell("The sound is coming from %s." % direction, evoke=True, max_length=True)
                            break

    def nearby(self, no_traps: bool=True) -> Iterable['Location']:
        """
        Returns a sequence of all adjacent locations, normally avoiding 'traps' (locations without a way back).
        (this may be expanded in the future with a way to search further than just 1 step away)
        """
        if no_traps:
            return (e.target for e in self.exits.values() if e.target.exits)
        return (e.target for e in self.exits.values())

    def look(self, exclude_living: 'Living'=None, short: bool=False) -> Sequence[str]:
        """returns a list of paragraph strings describing the surroundings, possibly excluding one living from the description list"""
        paragraphs = ["<location>[" + self.name + "]</>"]
        if short:
            if self.exits and mud_context.config.show_exits_in_look:
                paragraphs.append("Exits: " + ", ".join(sorted(set(self.exits.keys()))))
            if self.items:
                item_names = sorted(item.name for item in self.items)
                paragraphs.append("You see: " + lang.join(item_names))
            if self.livings:
                living_names = sorted(living.name for living in self.livings if living != exclude_living)
                if living_names:
                    paragraphs.append("Present here: " + lang.join(living_names))
            return paragraphs
        # normal (long) output
        if self.description:
            paragraphs.append(self.description)
        if self.exits and mud_context.config.show_exits_in_look:
            exits_seen = set()  # type: Set[Exit]
            exit_paragraph = []  # type: List[str]
            for exit_name in sorted(self.exits):
                exit = self.exits[exit_name]
                if exit not in exits_seen:
                    exits_seen.add(exit)
                    exit_paragraph.append(exit.short_description)
            paragraphs.append(" ".join(exit_paragraph))
        items_and_livings = []  # type: List[str]
        items_with_short_descr = [item for item in self.items if item.short_description]
        items_without_short_descr = [item for item in self.items if not item.short_description]
        uniq_descriptions = set()
        if items_with_short_descr:
            for item in items_with_short_descr:
                uniq_descriptions.add(item.short_description)
        items_and_livings.extend(uniq_descriptions)
        if items_without_short_descr:
            titles = sorted([lang.a(item.title) for item in items_without_short_descr])
            items_and_livings.append("You see " + lang.join(titles) + ".")
        livings_with_short_descr = [living for living in self.livings if living != exclude_living and living.short_description]
        livings_without_short_descr = [living for living in self.livings if living != exclude_living and not living.short_description]
        if livings_without_short_descr:
            titles = sorted(living.title for living in livings_without_short_descr)
            if titles:
                titles_str = lang.join(titles)
                if len(titles) > 1:
                    titles_str += " are here."
                else:
                    titles_str += " is here."
                items_and_livings.append(lang.capital(titles_str))
        uniq_descriptions = set()
        if livings_with_short_descr:
            for living in livings_with_short_descr:
                uniq_descriptions.add(living.short_description)
        items_and_livings.extend(uniq_descriptions)
        if items_and_livings:
            paragraphs.append(" ".join(items_and_livings))
        return paragraphs

    def search_living(self, name: str) -> Optional['Living']:
        """
        Search for a living in this location by its name (and title, if no names match).
        Is alias-aware. If there's more than one match, returns the first. None if nothing found.
        """
        name = name.lower()
        result = [living for living in self.livings if living.name == name]
        if not result:
            # try titles and aliases
            result = [living for living in self.livings if name in living.aliases or living.title.lower() == name]
        return result[0] if result else None

    def insert(self, obj: Union['Living', Item], actor: Optional['Living']) -> None:
        """Add item to the contents of the location (either a Living or an Item)"""
        assert obj is not None
        if isinstance(obj, Living):
            self.livings.add(obj)
        elif isinstance(obj, Item):
            self.items.add(obj)
        else:
            raise TypeError("can only add Living or Item")
        obj.location = self

    def remove(self, obj: Union['Living', Item], actor: Optional['Living']) -> None:
        """Remove obj from this location (either a Living or an Item)"""
        assert obj is not None
        if obj in self.livings:
            self.livings.remove(obj)    # type: ignore
        elif obj in self.items:
            self.items.remove(obj)      # type: ignore
        else:
            return   # just ignore an object that wasn't present in the first place
        obj.location = None

    def handle_verb(self, parsed: ParseResult, actor: 'Living') -> bool:
        """
        Handle a custom verb (specified in the verbs dict of a living/item/exit in this location).
        Return True if handled, False if not handled.
        """
        # @todo this code cannot deal with yields directly but you can raise AsyncDialog exception,
        # that indicates to the driver that it should initiate the given async dialog when continuing.
        handled = any(living._handle_verb_base(parsed, actor) for living in self.livings)
        if not handled:
            handled = any(item.handle_verb(parsed, actor) for item in self.items)
            if not handled:
                handled = any(exit.handle_verb(parsed, actor) for exit in set(self.exits.values()))
        return handled

    def _notify_action_all(self, parsed: ParseResult, actor: 'Living') -> None:
        """
        Notify the location, the items in it, and the livings in it, of an action performed by someone.
        Don't override this one in a subclass, override notify_action instead.
        Uncompleted actions (error, or ActionRefused) are ignored.
        Custom verbs are notified however, even if they were already handled by handle_verb!
        """
        # Notice that this notification event is invoked by the driver after all
        # actions concerning player input have been handled, so we don't have to
        # queue the delegated calls.
        self.notify_action(parsed, actor)
        for living in self.livings:
            living._notify_action_all(parsed, actor)
        for item in self.items:
            item.notify_action(parsed, actor)
        for exit in set(self.exits.values()):
            exit.notify_action(parsed, actor)

    def notify_action(self, parsed: ParseResult, actor: 'Living') -> None:
        """
        Notify the location, the items in it, and the livings in it, of an action performed by someone.
        This can be any verb, command, soul emote, custom verb.
        Uncompleted actions (error, or ActionRefused) are ignored.
        Custom verbs are notified however, even if they were already handled by handle_verb!
        It's good practice to first do a check like this::

            if actor is self or parsed.verb in self.verbs:
                return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        """
        pass

    def notify_npc_arrived(self, npc: 'Living', previous_location: 'Location') -> None:
        """
        A NPC has arrived in this location.
        When you override this be sure to call base method.
        This event is not delegated to all items or creatures in the location!
        If you need that, you should create a pubsub topic event, where the correct
        objects are listening on.
        """
        pass

    def notify_npc_left(self, npc: 'Living', target_location: 'Location') -> None:
        """
        A NPC has left the location.
        When you override this be sure to call base method.
        This event is not delegated to all items or creatures in the location!
        If you need that, you should create a pubsub topic event, where the correct
        objects are listening on.
        """
        # creatures that follow the npc should move after it.
        for living in self.livings:
            if living.following is npc:
                if mud_context.config.server_tick_method == story.TickMethod.COMMAND:
                    living.move(target_location)    # move immediately
                else:
                    mud_context.driver.defer(2, living.move, target_location)   # move after a short delay

    def notify_player_arrived(self, player, previous_location: 'Location') -> None:
        """
        A player has arrived in this location.
        When you override this be sure to call base method.
        This event is not delegated to all items or creatures in the location!
        If you need that, you should create a pubsub topic event, where the correct
        objects are listening on.
        """
        pass

    def notify_player_left(self, player, target_location: 'Location') -> None:
        """
        A player has left this location.
        When you override this be sure to call base method.
        This event is not delegated to all items or creatures in the location!
        If you need that, you should create a pubsub topic event, where the correct
        objects are listening on.
        """
        # creatures that follow the player should move after them.
        for living in self.livings:
            if living.following is player:
                if mud_context.config.server_tick_method == story.TickMethod.COMMAND:
                    living._move_follow(target_location, util.Context.from_global())    # move immediately
                else:
                    mud_context.driver.defer(1.5, living._move_follow, target_location)   # move after a short delay


class Stats:
    def __init__(self) -> None:
        self.gender = 'n'
        self.level = 1
        self.xp = 0
        self.hp = 0
        self.maxhp_dice = ""
        self.ac = 0
        self.wc = 0
        self.attack_dice = ""  # damage roll when attacking without a weapon
        self.alignment = 0   # -1000 (evil) to +1000 (good), neutral=[-349..349]
        self.bodytype = races.BodyType.HUMANOID
        self.language = ""
        self.weight = 0.0
        self.size = races.BodySize.HUMAN_SIZED
        self.race = ""      # the name of the race of this creature
        self.strength = 3
        self.agility = 3

    def __repr__(self):
        return "<Stats: %s>" % vars(self)

    @classmethod
    def from_race(cls: type, race: builtins.str, gender: builtins.str='n') -> 'Stats':
        r = races.races[race]
        s = cls()
        s.gender = gender
        s.race = race
        s.set_stats_from_race()
        # @todo initialize xp, hp, maxhp, ac, attack, alignment, level. Current race defs don't include this data
        return s

    def set_stats_from_race(self) -> None:
        # the stats that are static are always initialized from the races table
        # we look it up via the name, not needed to store the actual Race object here
        r = races.races[self.race]
        self.bodytype = r.body
        self.language = r.language
        self.weight = r.mass
        self.size = r.size


class Living(MudObject):
    """
    A living entity in the mud world (also known as an NPC).
    Livings sometimes have a heart beat 'tick' that makes them interact with the world.
    They are always inside a Location (Limbo when not specified yet).
    They also have an inventory object, and you can test for containment with item in living.
    """
    def __init__(self, name: str, gender: str, *, race: str="human",
                 title: str="", descr: str="", short_descr: str="") -> None:
        if race:
            self.stats = Stats.from_race(race, gender=gender)
        else:
            self.stats = Stats()
        self.init_gender(gender)
        self.soul = Soul()
        self.location = _limbo  # type: Location  # set transitional location
        self.privileges = set()  # type: Set[str] # probably only used for Players though
        self.aggressive = False
        self.money = 0.0  # the currency is determined by util.MoneyFormatter set in the driver
        self.default_verb = "examine"
        self.__inventory = set()   # type: Set[Item]
        self.previous_commandline = ""
        self._previous_parse = ParseResult("")
        self.teleported_from = None   # type: Optional[Location]   # used by teleport/return commands
        self.following = None   # type: Optional[Living]
        self.is_pet = False   # set this to True if creature is/becomes someone's pet
        super().__init__(name, title=title, descr=descr, short_descr=short_descr)

    def init_gender(self, gender: str) -> None:
        """(re)set gender attributes"""
        self.gender = gender
        self.stats.gender = gender  # notice that for completeness, gender is also present on the stats object
        self.subjective = lang.SUBJECTIVE[self.gender]
        self.possessive = lang.POSSESSIVE[self.gender]
        self.objective = lang.OBJECTIVE[self.gender]

    def init_inventory(self, items: Iterable[Item]) -> None:
        """Set the living's initial inventory"""
        assert len(self.__inventory) == 0
        for item in items:
            self.insert(item, self)

    def __contains__(self, item: Union['Living', Item, Location]) -> bool:
        return item in self.__inventory

    @property
    def inventory_size(self) -> int:
        return len(self.__inventory)

    @property
    def inventory(self) -> FrozenSet[Item]:
        return frozenset(self.__inventory)

    def insert(self, item: Union['Living', Item], actor: Optional['Living']) -> None:
        """Add an item to the inventory."""
        assert item is not None
        if not isinstance(item, Item):
            raise ActionRefused("You can't do that.")
        try:
            self.allow_give_item(item, actor)  # if this passes we are good to go
            if self.aggressive and actor is not self:
                raise ActionRefused()
        except ActionRefused:
            if actor is None or ("wizard" not in actor.privileges and "shopkeeper" not in actor.privileges):
                if self.aggressive:
                    raise ActionRefused("It's probably not a good idea to give things to %s." % self.title)
                raise
        self.__inventory.add(item)
        item.contained_in = self

    def remove(self, item: Union['Living', Item], actor: Optional['Living']) -> None:
        """remove an item from the inventory"""
        assert item is not None
        if not isinstance(item, Item):
            raise ActionRefused("You can't do that.")
        if actor is self or actor is not None and "wizard" in actor.privileges:
            self.__inventory.remove(item)
            item.contained_in = None
        else:
            raise ActionRefused("You can't take %s from %s." % (item.title, self.title))

    def destroy(self, ctx: Optional[util.Context]) -> None:
        super().destroy(ctx)
        if self.location and self in self.location.livings:
            self.location.livings.remove(self)
        self.location = _limbo
        for item in self.__inventory:
            item.destroy(ctx)
        self.__inventory.clear()
        # @todo: remove attack status, etc.
        self.soul = None   # type: ignore  # truly die ;-)

    @util.authorized("wizard")
    def wiz_clone(self, actor: 'Living', make_clone: bool=True) -> 'Living':
        if make_clone:
            # avoid deepcopying the location
            location, self.location = self.location, _limbo
            duplicate = copy.deepcopy(self)
            self.location = location
            MudObjRegistry.track_vnum(duplicate, fix_clones=True)   # deepcopy overwrites initially given vnum so make a new one
            mud_context.driver.register_periodicals(duplicate)
        else:
            duplicate = self
        actor.tell("Cloned into: " + repr(duplicate) + " (spawned in current location)")
        actor.tell_others("{Actor} summons %s..." % lang.a(duplicate.title))
        actor.location.insert(duplicate, actor)
        actor.location.tell("%s appears." % lang.capital(duplicate.title), evoke=True, max_length=True)
        return duplicate

    @util.authorized("wizard")
    def wiz_destroy(self, actor: 'Living', ctx: util.Context) -> None:
        if self is actor:
            raise ActionRefused("You can't destroy yourself, are you insane?!")
        self.tell("%s creates a black hole that sucks you up. You're utterly destroyed." % lang.capital(actor.title))
        self.destroy(ctx)

    def show_inventory(self, actor: 'Living', ctx: util.Context) -> None:
        """show the living's inventory to the actor"""
        name = lang.capital(self.title)
        if self.inventory:
            actor.tell(name + " is carrying:", end=True)
            for item in self.inventory:
                actor.tell("  " + item.title, format=False)
        else:
            actor.tell(name + " is carrying nothing.")
        if ctx.config.money_type:
            actor.tell("Money in possession: %s." % ctx.driver.moneyfmt.display(self.money))

    def get_wiretap(self) -> pubsub.Topic:
        """get a wiretap for this living"""
        return pubsub.topic(("wiretap-living", "%s#%d" % (self.name, self.vnum)))

    def tell(self, message: str, *, end: bool=False, format: bool=True, evoke: bool=False, max_length : bool=False) -> 'Living':
        """
        Every living thing in the mud can receive an action message.
        Message will be converted to str if required.
        For players this is usually printed to their screen, but for all other
        livings the default is to do nothing -- except for making sure
        that the message is sent to any wiretaps that may be present.
        The Living could react on the message, but this is not advisable because
        you'll have to parse the string again to figure out what happened...
        (there are better ways to react on stuff that happened).
        The Living itself is returned so you can easily chain calls.
        Note: end and format parameters are ignored for Livings but may be
        useful when this function is called on a subclass such as Player.
        """
        tap = self.get_wiretap()
        tap.send((self.name, str(message)))
        return self

    def tell_later(self, message: str) -> None:
        """Tell something to this creature, but do it after all other messages."""
        pending_tells.send(lambda: self.tell(message, evoke=True, max_length=True))

    def tell_others(self, message: str, target: Optional['Living']=None, evoke: bool=False, max_length: bool=True) -> None:
        """
        Send a message to the other livings in the location, but not to self.
        There are a few formatting strings for easy shorthands:
        {actor}/{Actor} = the acting living's title / acting living's title capitalized (subject in the sentence)
        {target}/{Target} = the target's title / target's title capitalized (object in the sentence)
        If you need even more tweaks with telling stuff, use living.location.tell directly.
        """
        if target is None:
            room_msg = message.format(actor=self.title, Actor=lang.capital(self.title))
            self.location.tell(room_msg, exclude_living=self, evoke=evoke, max_length=True)
        else:
            room_msg = message.format(actor=self.title, Actor=lang.capital(self.title),
                                      target=target.title, Target=lang.capital(target.title))
            spec_msg = message.format(actor=self.title, Actor=lang.capital(self.title), target="you", Target="You")
            self.location.tell(room_msg, exclude_living=self, specific_targets={target}, specific_target_msg=spec_msg, evoke=evoke, max_length=True)

    def parse(self, commandline: str, external_verbs: Set[str]=set()) -> ParseResult:
        """Parse the commandline into something that can be processed by the soul (ParseResult)"""
        if commandline == "again":
            # special case, repeat previous command
            if self.previous_commandline:
                commandline = self.previous_commandline
                self.tell("<dim>(repeat: %s)</>" % commandline, end=True)
            else:
                raise ActionRefused("Can't repeat your previous action.")
        self.previous_commandline = commandline
        parsed = self.soul.parse(self, commandline, external_verbs)
        self._previous_parse = parsed
        if external_verbs and parsed.verb in external_verbs:
            raise NonSoulVerb(parsed)
        if parsed.verb not in verbdefs.NONLIVING_OK_VERBS:
            # check if any of the targeted objects is a non-living
            if any(not isinstance(who, Living) for who in parsed.who_info):
                raise NonSoulVerb(parsed)
        self.validate_socialize_targets(parsed)
        return parsed

    def validate_socialize_targets(self, parsed: ParseResult) -> None:
        """check if any of the targeted objects is an exit"""
        if any(isinstance(w, Exit) for w in parsed.who_info):
            raise ParseError("That doesn't make much sense.")

    def remember_previous_parse(self) -> None:
        """remember the previously parsed data, soul uses this to reference back to earlier items/livings"""
        self.soul.remember_previous_parse(self._previous_parse)

    def do_socialize(self, cmdline: str, external_verbs: Set[str]=set()) -> None:
        """
        Perform a command line with a socialize/soul verb on the living's behalf.
        It only performs soul emotes, no custom command functions!
        """
        try:
            parsed = self.parse(cmdline, external_verbs=external_verbs)
            self.do_socialize_cmd(parsed)
        except UnknownVerbException as ex:
            if ex.verb == "say":
                # emulate the say command (which is not an emote, but it's convenient to be able to use it as such)
                verb, _, rest = cmdline.partition(" ")
                rest = rest.strip()
                self.tell_others("{Actor} says: " + rest)
            else:
                raise

    def do_command_verb(self, cmdline: str, ctx: util.Context) -> None:
        """
        Perform a verb, parsed from a command line. This is an easy way to make a Npc do something,
        but it has a pretty large performance overhead. If you can, you should use low level methods
        instead (such as ``tell_others`` or ``do_socialize`` etc)
        The verb can be a soul verb (such as 'ponder') but also a command verb.
        Custom dynamic verbs added by the environment are not supported (yet), and neither are commands
        that initiate a dialog (generators)
        This function is not used in the processing of player commands!
        """
        command_verbs = ctx.driver.current_verbs(self)
        try:
            self.do_socialize(cmdline, command_verbs)
        except NonSoulVerb as nx:
            parsed = nx.parsed
            if parsed.verb in command_verbs:
                func = ctx.driver.commands.get(self.privileges)[parsed.verb]
                if getattr(func, "is_generator", False):
                    raise TaleError("can't let a npc perform a dialog command")
                func(self, parsed, ctx)
                if func.enable_notify_action:
                    pending_actions.send(lambda actor=self: actor.location._notify_action_all(parsed, actor))

    def do_socialize_cmd(self, parsed: ParseResult) -> None:
        """
        A soul verb such as 'ponder' was entered. Socialize with the environment to handle this.
        Some verbs may trigger a response or action from something or someone else.
        """
        who, actor_message, room_message, target_message = self.soul.process_verb_parsed(self, parsed)
        self.tell(actor_message, evoke=True, max_length=False)
        self.location.tell(room_message, self, who, target_message, evoke=True, max_length=False)
        pending_actions.send(lambda actor=self: actor.location._notify_action_all(parsed, actor))
        if parsed.verb == 'attack' :
            for thing in who:
                if isinstance(thing, Living):
                    pending_actions.send(lambda victim=thing: self.start_attack(victim))
        elif parsed.verb in verbdefs.AGGRESSIVE_VERBS:
            # usually monsters immediately attack,
            # other npcs may choose to attack or to ignore it
            # We need to check the verb qualifier, it might void the actual action :)
            if parsed.qualifier not in verbdefs.NEGATING_QUALIFIERS:
                for thing in who:
                    if isinstance(thing, Living) and thing.aggressive:
                        pending_actions.send(lambda victim=self: thing.start_attack(victim))

    @util.authorized("wizard")
    def do_forced_cmd(self, actor: 'Living', parsed: ParseResult, ctx: util.Context) -> None:
        """
        Perform a (pre-parsed) command because the actor forced us to do it.

        This code is fairly similar to the __process_player_command from the driver
        but it doesn't deal with as many error situations, and just bails out if it gets confused.
        It does try its best to support the following:
        - custom location verbs (such as 'sell' in a shop)
        - exit handling
        - built-in cmds (such as 'drop'/'take')
        Note that soul emotes are handled by do_socialize_cmd instead.
        """
        try:
            if parsed.qualifier:
                raise ParseError("That action doesn't support qualifiers.")  # for now, quals are only supported on soul-verbs (emotes).
            custom_verbs = set(ctx.driver.current_custom_verbs(self))
            if parsed.verb in custom_verbs:
                if self.location.handle_verb(parsed, self):       # note: can't deal with async dialogs
                    pending_actions.send(lambda actor=self: actor.location._notify_action_all(parsed, actor))
                    return
                else:
                    raise ParseError("That custom verb is not understood by the environment.")
            if parsed.verb in self.location.exits:
                ctx.driver.go_through_exit(self, parsed.verb)
                return
            command_verbs = set(ctx.driver.current_verbs(self))
            if parsed.verb in command_verbs:
                func = ctx.driver.commands.get(self.privileges)[parsed.verb]
                if getattr(func, "is_generator", False):
                    dialog = func(self, parsed, ctx)
                    async_dialogs.send((ctx.conn, dialog))    # enqueue as async, and continue
                    return
                func(self, parsed, ctx)
                if func.enable_notify_action:
                    pending_actions.send(lambda actor=self: actor.location._notify_action_all(parsed, actor))
                return
            raise ParseError("Command not understood.")
        except Exception as x:
            actor.tell("The forced command failed due to something technical.")
            actor.tell("The reason was: {0!r} {0!s}".format(x))

    def move(self, target: Union[Location, 'Container', 'Living'], actor: 'Living'=None,
             *, silent: bool=False, is_player: bool=False, verb: str="move", direction_names: Sequence[str]=None) -> None:
        """
        Leave the current location, enter the new location (transactional).
        Moving a living is only supported to a Location target.
        Messages are being printed to the locations if the move was successful.
        """
        assert isinstance(target, Location), "can only move to a Location"

        def display_direction(directions: Sequence[str]) -> str:
            for direction in directions:
                if direction in {"north", "east", "south", "west", "out", "outside",
                                 "northeast", "northwest", "southeast", "southwest",
                                 "north east", "north west", "south east", "south west"}:
                    return direction
                if direction in {"up", "above", "upstairs"}:
                    return "up"
                if direction in {"down", "below", "downstairs"}:
                    return "down"
                if direction in {"left", "right"}:
                    return "to the " + direction
            return ""

        actor = actor or self
        original_location = None
        if self.location:
            original_location = self.location
            self.location.remove(self, actor)
            try:
                target.insert(self, actor)
            except:
                # insert in target failed, put back in original location
                original_location.insert(self, actor)
                raise
            if not silent:
                direction_txt = display_direction(direction_names or [])
                if direction_txt:
                    message = "%s leaves %s." % (lang.capital(self.title), direction_txt)
                else:
                    message = "%s leaves." % lang.capital(self.title)
                original_location.tell(message, exclude_living=self, evoke=True, max_length=True)
            # queue event
            if is_player:
                pending_actions.send(lambda who=self, where=target: original_location.notify_player_left(who, where))
            else:
                pending_actions.send(lambda who=self, where=target: original_location.notify_npc_left(who, where))
        else:
            target.insert(self, actor)
        if not silent:
            target.tell(f"{lang.capital(self.title)} arrives from {original_location}." , exclude_living=self, evoke=True, max_length=True)
        # queue event
        if is_player:
            pending_actions.send(lambda who=self, where=original_location: target.notify_player_arrived(who, where))
        else:
            pending_actions.send(lambda who=self, where=original_location: target.notify_npc_arrived(who, where))

    def search_item(self, name: str, include_inventory: bool=True,
                    include_location: bool=True, include_containers_in_inventory: bool=True) -> Optional[Item]:
        """The same as locate_item except it only returns the item, or None."""
        item, container = self.locate_item(name, include_inventory, include_location, include_containers_in_inventory)
        return item  # skip the container

    def locate_item(self, name: str, include_inventory: bool=True, include_location: bool=True,
                    include_containers_in_inventory: bool=True) -> Tuple[Optional[Item], Optional[ContainingType]]:
        """
        Searches an item within the 'visible' world around the living including his inventory.
        If there's more than one hit, just return the first.
        Returns (None,None) or (item, containing_object)
        """
        if not name:
            raise ValueError("name must be given")
        found = None
        containing_object = None   # type: Optional[ContainingType]
        if include_inventory:
            containing_object = self
            found = Item.search_item(name, self.__inventory)
        if not found and include_location:
            containing_object = self.location
            found = Item.search_item(name, self.location.items)
        if not found and include_containers_in_inventory:
            # check if an item in the inventory might contain it
            for container in self.__inventory:
                containing_object = container   # type: ignore
                try:
                    inventory = container.inventory
                except ActionRefused:
                    continue    # no access to inventory, just skip this item silently
                else:
                    found = Item.search_item(name, inventory)
                    if found:
                        break
        return (found, containing_object) if found else (None, None)

    def start_attack(self, victim: 'Living') -> None:
        """Starts attacking the given living until death ensues on either side."""
        # @todo I'm not yet sure if the combat/attack logic should go here (just on Living), or that it should be split with Player...
        # @todo actual fight.   Also implement 'assist' command to help someone that is already fighting.
        # NOTE: combat commands should have a check so that you cannot spam them!
        name = lang.capital(self.title)
        
        result = self.combat(victim)
        
        if result < 0.5:
            text = "After a fierce battle, %s dies." % (name)
        elif result > 0.5:
            text = "After a fierce battle, %s dies." % (victim.title)
        else:
            text = "After a fierce battle, both retreat."
        
        room_msg = "%s attacks %s! %s" % (name, victim.title, text)
        victim_msg = "%s attacks you. %s!" % (name, result)
        attacker_msg = "You attack %s. %s!" % (victim.title, text)
        victim.tell(victim_msg, evoke=True, max_length=False)
        victim.location.tell(room_msg, exclude_living=victim, specific_targets={self}, specific_target_msg=attacker_msg, evoke=True, max_length=False)
        
        if result < 0.5:
            self.destroy()
        elif result > 0.5:
            victim.destroy()
    
    def combat(self, actor2: 'Living'):
        actor1 = self
        """ Simple combat. Credit to ChatGPT.
            < 0.5 actor2 'victim' dies
            > 0.5 actor1 'attacker' dies"""
        
        def calculate_attack(actor: 'Living'):
            # The attack strength depends on the level and strength of the actor
            return actor.stats.level
    
        def calculate_defense(actor: 'Living'):
            # The defense strength depends on the level and agility of the actor
            return actor.stats.level * actor.stats.agility
    
        def calculate_weapon_bonus(actor: 'Living'):
            # The weapon bonus is a random factor between 0 and 1. If the actor has no weapon, bonus is 1.
            return actor.stats.wc + 1
    
        def calculate_armor_bonus(actor: 'Living'):
            # The armor bonus is a random factor between 0 and 1. If the actor has no armor, bonus is 1.
            return actor.stats.ac + 1
    
        def calculate_damage(attacker: 'Living', defender: 'Living'):
            # Calculate the damage done by the attacker to the defender
            attack_strength = calculate_attack(attacker) * calculate_weapon_bonus(attacker) * attacker.stats.strength * attacker.stats.size.order
            defense_strength = calculate_defense(defender) * calculate_armor_bonus(defender) * defender.stats.strength * defender.stats.size.order
            damage = max(0, attack_strength - defense_strength)
            return damage
    
        # Calculate the chances of actor1 and actor2 winning
        damage_to_actor1 = calculate_damage(actor2, actor1)
        damage_to_actor2 = calculate_damage(actor1, actor2)
    
        # Use some randomness to introduce unpredictability
        damage_to_actor1 *= random.uniform(0.9, 1.1)
        damage_to_actor2 *= random.uniform(0.9, 1.1)
    
        # Calculate the normalized factor
        total_damage = damage_to_actor1 + damage_to_actor2
        if total_damage == 0:
            return 0.5
        return damage_to_actor1 / total_damage
        

    def allow_give_money(self, amount: float, actor: Optional['Living']) -> None:
        """Do we accept money? Raise ActionRefused if not."""
        if self.stats.race not in (None, "human"):
            raise ActionRefused("You can't do that.")

    def allow_give_item(self, item: Item, actor: Optional['Living']) -> None:
        """Do we accept given items? Raise ActionRefused if not."""
        if actor is None or actor is not self and "wizard" not in actor.privileges:
            raise ActionRefused("%s doesn't want %s." % (lang.capital(self.title), item.title))

    def _handle_verb_base(self, parsed: ParseResult, actor: 'Living') -> bool:
        """
        Handle a custom verb. Return True if handled, False if not handled.
        Also checks inventory items. (Don't override this in a subclass,
        override handle_verb instead)
        """
        if self.handle_verb(parsed, actor):
            return True
        return any(item.handle_verb(parsed, actor) for item in self.__inventory)

    def handle_verb(self, parsed: ParseResult, actor: 'Living') -> bool:
        """Handle a custom verb (specified in the verbs dict). Return True if handled, False if not handled."""
        return False

    def _notify_action_all(self, parsed: ParseResult, actor: 'Living') -> None:
        """
        Notify the living of an action performed by someone.
        Also calls inventory items. Don't override this one in a subclass, override notify_action instead.
        """
        self.notify_action(parsed, actor)
        for item in self.__inventory:
            item.notify_action(parsed, actor)

    def notify_action(self, parsed: ParseResult, actor: 'Living') -> None:
        """
        Notify the living of an action performed by someone.
        This can be any verb, command, soul emote, custom verb.
        Uncompleted actions (error, or ActionRefused) are ignored.
        Custom verbs are notified however, even if they were already handled by handle_verb!
        It's good practice to first do a check like this::

            if actor is self or parsed.verb in self.verbs:
                return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        """
        pass

    def look(self, short: Optional[bool]=None) -> None:
        """look around in your surroundings. Dummy for base livings (they don't perform 'look' nor react to it)."""
        pass

    def select_random_move(self) -> Optional['Exit']:
        """
        Select a random accessible exit to move to.
        Avoids exits to a room that have no exits (traps).
        If no suitable exit is found in a few random attempts, return None.
        """
        directions_with_exits = [d for d, e in self.location.exits.items() if e.target.exits]
        if directions_with_exits:
            for tries in range(4):
                direction = random.choice(directions_with_exits)
                xt = self.location.exits[direction]
                try:
                    xt.allow_passage(self)
                except ActionRefused:
                    continue
                else:
                    return xt
        return None

    def _move_follow(self, target_location: Location, ctx: util.Context) -> None:
        # follow someone that recently moved.
        if self.is_pet:
            # pets always keep up with their owner, regardless of the given target_location
            if self.following:
                self.move(self.following.location)
        else:
            # non-pets just move to the target location and don't try to keep up.
            self.move(target_location)
            
    def check_stat(self, stat : str):
        if stat == 'hp':
            return self.stat.hp
        
        


class Container(Item):
    """
    A bag-type container (i.e. an item that acts as a container)
    Allows insert and remove, and examine its contents, as opposed to an Item
    You can test for containment with 'in': item in bag
    """
    def init(self) -> None:
        self.__inventory = set()   # type: Set[Item]

    def init_inventory(self, items: Iterable[Item]) -> None:
        """Set the container's initial inventory"""
        assert len(self.__inventory) == 0
        self.__inventory = set(items)
        for item in items:
            item.contained_in = self

    @property
    def inventory(self) -> FrozenSet[Item]:
        return frozenset(self.__inventory)

    @property
    def inventory_size(self) -> int:
        return len(self.__inventory)

    def __contains__(self, item: Item) -> bool:
        return item in self.__inventory

    def destroy(self, ctx: Optional[util.Context]) -> None:
        for item in self.__inventory:
            item.destroy(ctx)
        self.__inventory.clear()
        super().destroy(ctx)

    def insert(self, item: Union[Living, Item], actor: Optional[Living]) -> None:
        assert item is not None
        if not isinstance(item, Item):
            raise ActionRefused("You can't do that.")
        self.__inventory.add(item)
        item.contained_in = self

    def remove(self, item: Union[Living, Item], actor: Optional[Living]) -> None:
        assert item is not None
        if not isinstance(item, Item):
            raise ActionRefused("You can't do that.")
        self.__inventory.remove(item)
        item.contained_in = None


class Exit(MudObject):
    """
    An 'exit' that connects one location to another. It is strictly one-way!
    Directions can be a single string or a sequence of directions (all meaning the same exit).
    You can use a Location object as target, or a string designating the location
    (for instance "town.square" means the square location object in game.zones.town).
    If using a string, it will be retrieved and bound at runtime.
    Short_description will be shown when the player looks around the room.
    Long_description is optional and will be shown instead if the player examines the exit.
    Enter_msg is the text shown to the player when they succesfully enter/pass through the exit/door.
    The exit's direction is stored as its name attribute (if more than one, the rest are aliases).
    Note that the exit's origin is not stored in the exit object.
    """
    def __init__(self, directions: Union[str, Sequence[str]], target_location: Union[str, Location],
                 short_descr: str, long_descr: str="", *, enter_msg: str="") -> None:
        assert isinstance(target_location, (Location, str)), "target must be a Location or a string"
        self.target = _limbo   # type: Location
        if isinstance(directions, str):
            direction = directions
            aliases = set()  # type: Set[str]
        else:
            direction = directions[0]
            aliases = set(directions[1:])
        self.target = _limbo
        if isinstance(target_location, Location):
            self.target = target_location
            self._target_str = ""
            title = "Exit to " + self.target.title
        else:
            self._target_str = target_location
            title = "Exit to <unbound:%s>" % target_location
        long_descr = long_descr or short_descr
        # the name of the exit/door is the first direction given (any others are aliases)
        super().__init__(direction, title=title, descr=long_descr, short_descr=short_descr)
        self.aliases = aliases
        if self.target in (_limbo, None):
            # The driver needs to know about all unbound exits,
            # it will hook them all up once initialization is complete.
            mud_context.driver.register_exit(self)
        self.enter_msg = enter_msg

    def __repr__(self):
        targetname = self.target.name if self.target not in (_limbo, None) else self._target_str
        return "<base.Exit to '%s' #%d @ 0x%x>" % (targetname, self.vnum, id(self))

    @property
    def names(self):
        """a list of all the names of this direction (name followed by aliases)"""
        return [self.name] + list(self.aliases)

    @classmethod
    def connect(cls, from_loc: Location, directions: Union[str, Sequence[str]], short_descr: str, long_descr: str,
                to_loc: Location, return_directions: Union[str, Sequence[str]],
                return_short_descr: str, return_long_descr: str) -> Tuple['Exit', 'Exit']:
        """
        Create a pair of exits that connect two locations.
        (This requires two exit definitions because the directions and descriptions differ for the to- and return-exists)
        """
        e1 = cls(directions, to_loc, short_descr, long_descr)
        e2 = cls(return_directions, from_loc, return_short_descr, return_long_descr)
        e1.bind(from_loc)
        e2.bind(to_loc)
        return e1, e2

    def bind(self, location: Location) -> None:
        """Binds the exit to a location."""
        assert isinstance(location, Location)
        directions = self.aliases | {self.name}
        for direction in directions:
            if direction in location.exits:
                raise LocationIntegrityError("exit already exists: '%s' in %s" % (direction, location), direction, self, location)
            location.exits[direction] = self

    def _bind_target(self, game_zones_module: ModuleType) -> None:
        """
        Binds the exit to the actual target_location object.
        Usually called by the driver before it starts player interaction.
        The caller needs to pass in the root module of the game zones (to avoid circular import dependencies)
        """
        if self.target in (_limbo, None) and self._target_str:
            target_module, target_object = self._target_str.rsplit(".", 1)
            module = game_zones_module
            try:
                for name in target_module.split("."):
                    module = getattr(module, name)
                target = getattr(module, target_object)
            except AttributeError:
                raise AttributeError("exit target error, cannot find target: '%s.%s' in exit: '%s'" %
                                     (target_module, target_object, self.short_description))
            assert isinstance(target, Location)
            self.target = target
            self.title = "Exit to " + target.title
            del self._target_str

    def allow_passage(self, actor: Living) -> None:
        """Is the actor allowed to move through the exit? Raise ActionRefused if not"""
        if self.target in (None, _limbo):
            raise LocationIntegrityError("exit not bound", "", self, None)

    def open(self, actor: Living, item: Item=None) -> None:
        raise ActionRefused("You can't open that.")

    def close(self, actor: Living, item: Item=None) -> None:
        raise ActionRefused("You can't close that.")

    def lock(self, actor: Living, item: Item=None) -> None:
        raise ActionRefused("You can't lock that.")

    def unlock(self, actor: Living, item: Item=None) -> None:
        raise ActionRefused("You can't unlock that.")

    def manipulate(self, verb: str, actor: Living) -> None:
        # override from base to print a special error message
        raise ActionRefused("It makes no sense to %s in that direction." % verb)


class Door(Exit):
    """
    A special exit that connects one location to another but which can be closed or even locked.
    Because a single door is still only one-way, you have to create a second -linked- door to go back.
    This is easily done by the ``reverse_door`` method.
    """
    def __init__(self, directions: Union[str, Sequence[str]], target_location: Union[str, Location],
                 short_descr: str, long_descr: str="", *, enter_msg: str="",
                 locked: bool=False, opened: bool=False, key_code: str="") -> None:
        self.locked = locked
        self.opened = opened
        self.__description_prefix = long_descr or short_descr
        self.key_code = key_code   # you can optionally set this to any code that a key must match to unlock the door
        super().__init__(directions, target_location, short_descr, long_descr, enter_msg=enter_msg)
        if locked and opened:
            raise ValueError("door cannot be both locked and opened")
        self.linked_door = None  # type: Optional[Door]

    @classmethod
    def connect(cls, from_loc: Location, directions: Union[str, Sequence[str]], short_descr: str, long_descr: str,
                to_loc: Location, return_directions: Union[str, Sequence[str]], return_short_descr: str, return_long_descr: str,
                locked: bool=False, opened: bool=False, key_code: str="") -> Tuple['Door', 'Door']:
        """
        Create a pair of doors that connect two locations.
        (This requires two door definitions because the directions and descriptions differ for the to- and return-exists)
        """
        d1 = cls(directions, to_loc, short_descr, long_descr, locked=locked, opened=opened, key_code=key_code)
        d2 = d1.reverse_door(return_directions, from_loc, return_short_descr, return_long_descr)
        d1.bind(from_loc)
        d2.bind(to_loc)
        return d1, d2

    def reverse_door(self, directions: Union[str, Sequence[str]], returning_location: Location,
                     short_description: str, long_description: str="") -> 'Door':
        """
        Set up a second door in the other location that is paired with this door.
        Opening this door will also open the other door etc.    Returns the new door object.
        (we need 2 doors because the name/exit descriptions are often different from both locations)
        """
        other_door = Door(directions, returning_location, short_description, long_description, locked=self.locked, opened=self.opened)
        self.linked_door = other_door
        other_door.linked_door = self
        other_door.key_code = self.key_code
        return other_door

    @property
    def description(self) -> str:
        if self.opened:
            status = "It is open "
        else:
            status = "It is closed "
        if self.locked:
            status += "and locked."
        else:
            status += "and unlocked."
        return self.__description_prefix + " " + status

    @description.setter
    def description(self, value: str) -> None:
        raise TaleError("you cannot set the description of a Door because it is dynamic")

    def __repr__(self):
        target = self.target.name if self.target else self._target_str
        return "<base.Door '%s'->'%s' #%d @ 0x%x>" % (self.name, target, self.vnum, id(self))

    def allow_passage(self, actor: Living) -> None:
        """Is the actor allowed to move through this door?"""
        if not self.target:
            raise LocationIntegrityError("door not bound", "", self, None)
        if not self.opened:
            raise ActionRefused("You can't go there; it's closed.")

    def open(self, actor: Living, item: Item=None) -> None:
        """Open the door with optional item. Notifies actor and room of this event."""
        if self.opened:
            raise ActionRefused("It's already open.")
        elif self.locked:
            raise ActionRefused("You try to open it, but it's locked.")
        else:
            self.opened = True
            actor.tell("You open it.", evoke=True, max_length=True)
            actor.tell_others("{Actor} opens the %s." % self.name, evoke=True, max_length=True)
            if self.linked_door:
                self.linked_door.opened = True
                self.target.tell("The %s is opened from the other side." % self.linked_door.name, evoke=True, max_length=True)

    def close(self, actor: Living, item: Item=None) -> None:
        """Close the door with optional item. Notifies actor and room of this event."""
        if not self.opened:
            raise ActionRefused("It's already closed.")
        self.opened = False
        actor.tell("You close it.", evoke=True, max_length=True)
        actor.tell_others("{Actor} closes the %s." % self.name, evoke=True, max_length=True)
        if self.linked_door:
            self.linked_door.opened = False
            self.target.tell("The %s is closed from the other side." % self.linked_door.name, evoke=True, max_length=True)

    def lock(self, actor: Living, item: Item=None) -> None:
        """Lock the door with the proper key (optional)."""
        key = None
        if self.locked:
            raise ActionRefused("It's already locked.")
        if self.opened:
            raise ActionRefused("The door is open! It makes no sense trying to lock it like this.")
        if item:
            if self.check_key(item):
                key = item
            else:
                raise ActionRefused("You can't use that to lock it.")
        else:
            if actor:
                key = self.search_key(actor)
            if not key:
                raise ActionRefused("You don't seem to have the means to lock it.")
        self.locked = True
        actor.tell("Your %s fits, the %s is now locked." % (key.title, self.name), evoke=True, max_length=True)
        actor.tell_others("{Actor} locks the %s with %s." % (self.name, lang.a(key.title)), evoke=True, max_length=True)
        if self.linked_door:
            self.linked_door.locked = True
            self.target.tell("The %s is locked from the other side." % self.linked_door.name, evoke=True, max_length=True)

    def unlock(self, actor: Living, item: Item=None) -> None:
        """Unlock the door with the proper key (optional)."""
        key = None
        if self.opened:
            raise ActionRefused("It's already open, so there's not much unlocking to be done.")
        if not self.locked:
            raise ActionRefused("It's not locked.")
        if item:
            if self.check_key(item):
                key = item
            else:
                raise ActionRefused("You can't use that to unlock it.")
        else:
            if actor:
                key = self.search_key(actor)
            if not key:
                raise ActionRefused("You don't seem to have the means to unlock it.")
        self.locked = False
        self.opened = True
        actor.tell("Your %s fits! You unlock the %s and open it." % (key.title, self.name), evoke=True, max_length=True)
        actor.tell_others("{Actor} unlocks the %s with %s %s, and opens it." % (self.name, actor.possessive, key.title), evoke=True, max_length=True)
        if self.linked_door:
            self.linked_door.locked = False
            self.linked_door.opened = True
            self.target.tell("The %s is unlocked and opened from the other side." % self.linked_door.name, evoke=True, max_length=True)

    def check_key(self, item: Item) -> bool:
        """Check if the item is a proper key for this door (based on key_code)"""
        key_code = getattr(item, "key_code", None)
        if self.linked_door:
            # if this door has a linked door, it could be that the key_code was set on the other door.
            # in that case, copy the key code from the other door.
            other_code = self.linked_door.key_code
            if self.key_code and self.key_code != other_code:
                raise TaleError("door key codes must match")
            else:
                self.key_code = other_code
        return key_code and key_code == self.key_code

    def search_key(self, actor: Living) -> Optional[Item]:
        """Does the actor have a proper key? Return the item if so, otherwise return None."""
        for item in actor.inventory:
            if self.check_key(item):
                return item
        return None

    def insert(self, item: Union[Living, Item], actor: Optional[Living]) -> None:
        """used when the player tries to put a key into the door, for instance."""
        assert item is not None
        if not isinstance(item, Item):
            raise ActionRefused("You can't do that.")
        if self.check_key(item):
            if self.locked:
                raise ActionRefused("You could try to unlock the door with it instead.")
            else:
                raise ActionRefused("You could try to lock the door with it instead.")
        raise ActionRefused("The %s doesn't fit." % item.title)


class Key(Item):
    """A key which has a unique code. It can be used to open a matching Door. Set the door or code using the key_for method."""
    def init(self) -> None:
        self.key_code = ""

    def key_for(self, door: Door=None, code: str="") -> None:
        """Makes this key a key for the given door. (basically just copies the door's key_code)"""
        if code:
            assert door is None
            self.key_code = code
        elif door:
            self.key_code = door.key_code
            if not self.key_code:
                raise LocationIntegrityError("door has no key_code set", "", door, door.target)

class Corpse(MudObject):
    """ The remains of someone or something that has died """
    

class Soul:
    """
    The 'soul' of a Living (most importantly, a Player).
    Handles the high level verb actions and allows for social player interaction.
    Verbs that actually do something in the environment (not purely social messages) are implemented elsewhere.
    """

    _quoted_message_regex = re.compile(r"('(?P<msg1>.*)')|(\"(?P<msg2>.*)\")")  # greedy single-or-doublequoted string match
    _skip_words = {"and", "&", "at", "to", "before", "in", "into", "on", "off", "onto",
                   "the", "with", "from", "after", "before", "under", "above", "next"}

    def __init__(self) -> None:
        self.__previously_parsed = ParseResult("")

    def is_verb(self, verb: str) -> bool:
        return verb in verbdefs.VERBS

    def process_verb(self, player: Living, commandstring: str, external_verbs: Set[str]=set()) \
            -> Tuple[str, Tuple[Set[ParsedWhoType], str, str, str]]:
        """
        Parse a command string and return a tuple containing the main verb (tickle, ponder, ...)
        and another tuple containing the targets of the action (excluding the player) and the various action messages.
        Any action qualifier is added to the verb string if it is present ("fail kick").
        """
        parsed = self.parse(player, commandstring, external_verbs)
        if parsed.verb in external_verbs:
            raise NonSoulVerb(parsed)
        result = self.process_verb_parsed(player, parsed)
        if parsed.qualifier:
            verb = parsed.qualifier + " " + parsed.verb
        else:
            verb = parsed.verb
        return verb, result

    def process_verb_parsed(self, player: Living, parsed: ParseResult) -> Tuple[Set[ParsedWhoType], str, str, str]:
        """
        This function takes a verb and the arguments given by the user,
        creates various display messages that can be sent to the players and room,
        and returns a tuple: (targets-without-player, playermessage, roommessage, targetmessage)
        Target can be a Living, an Item or an Exit.
        """
        if not player:
            raise TaleError("no player in process_verb_parsed")
        verbdata = verbdefs.VERBS.get(parsed.verb)
        if not verbdata:
            raise UnknownVerbException(parsed.verb, [], parsed.qualifier)

        message = parsed.message
        adverb = parsed.adverb

        vtype = verbdata[0]
        if not message and verbdata[1] and len(verbdata[1]) > 1:
            message = verbdata[1][1]  # get the message from the verbs table
        if message:
            if message.startswith("'"):
                # use the message without single quotes around it
                msg = message = self.spacify(message[1:])
            else:
                msg = " '" + message + "'"
                message = " " + message
        else:
            msg = message = ""
        if not adverb:
            if verbdata[1]:
                adverb = verbdata[1][0]    # normal-adverb
            else:
                adverb = ""
        where = ""
        if parsed.bodypart:
            where = " " + verbdefs.BODY_PARTS[parsed.bodypart]
        elif not parsed.bodypart and verbdata[1] and len(verbdata[1]) > 2 and verbdata[1][2]:
            where = " " + verbdata[1][2]  # replace bodyparts string by specific one from verbs table
        how = self.spacify(adverb)

        def result_messages(action: str, action_room: str) -> Tuple[Set[ParsedWhoType], str, str, str]:
            action = action.strip()
            action_room = action_room.strip()
            if parsed.qualifier:
                qual_action, qual_room, use_room_default = verbdefs.ACTION_QUALIFIERS[parsed.qualifier]
                action_room = qual_room % action_room if use_room_default else qual_room % action
                action = qual_action % action
            # construct message seen by player
            targetnames = [self.who_replacement(player, target, player) for target in parsed.who_info]
            player_msg = action.replace(" \nWHO", " " + lang.join(targetnames))
            player_msg = player_msg.replace(" \nYOUR", " your")
            player_msg = player_msg.replace(" \nMY", " your")
            # construct message seen by room
            targetnames = [self.who_replacement(player, target, None) for target in parsed.who_info]
            room_msg = action_room.replace(" \nWHO", " " + lang.join(targetnames))
            room_msg = room_msg.replace(" \nYOUR", " " + player.possessive)
            room_msg = room_msg.replace(" \nMY", " " + player.objective)
            # construct message seen by targets
            target_msg = action_room.replace(" \nWHO", " you")
            target_msg = target_msg.replace(" \nYOUR", " " + player.possessive)
            target_msg = target_msg.replace(" \nPOSS", " your")
            target_msg = target_msg.replace(" \nIS", " are")
            target_msg = target_msg.replace(" \nSUBJ", " you")
            target_msg = target_msg.replace(" \nMY", " " + player.objective)
            # fix up POSS, IS, SUBJ in the player and room messages
            if parsed.who_count == 1:
                only_living = parsed.who_1
                subjective = getattr(only_living, "subjective", "it")  # if no subjective attr, use "it"
                player_msg = player_msg.replace(" \nIS", " is")
                player_msg = player_msg.replace(" \nSUBJ", " " + subjective)
                player_msg = player_msg.replace(" \nPOSS", " " + Soul.poss_replacement(player, only_living, player))
                room_msg = room_msg.replace(" \nIS", " is")
                room_msg = room_msg.replace(" \nSUBJ", " " + subjective)
                room_msg = room_msg.replace(" \nPOSS", " " + Soul.poss_replacement(player, only_living, None))
            else:
                targetnames_player = lang.join([Soul.poss_replacement(player, living, player) for living in parsed.who_info])
                targetnames_room = lang.join([Soul.poss_replacement(player, living, None) for living in parsed.who_info])
                player_msg = player_msg.replace(" \nIS", " are")
                player_msg = player_msg.replace(" \nSUBJ", " they")
                player_msg = player_msg.replace(" \nPOSS", " " + lang.possessive(targetnames_player))
                room_msg = room_msg.replace(" \nIS", " are")
                room_msg = room_msg.replace(" \nSUBJ", " they")
                room_msg = room_msg.replace(" \nPOSS", " " + lang.possessive(targetnames_room))
            # add fullstops at the end
            player_msg = lang.fullstop("You " + player_msg)
            room_msg = lang.capital(lang.fullstop(player.title + " " + room_msg))
            target_msg = lang.capital(lang.fullstop(player.title + " " + target_msg))
            if player in parsed.who_info:
                who = set(parsed.who_info)
                who.remove(player)  # the player should not be part of the remaining targets.
                whof = set(who)
            else:
                whof = set(parsed.who_info)
            return whof, player_msg, room_msg, target_msg

        # construct the action string
        action = None
        if vtype == verbdefs.DEUX:
            action = verbdata[2]
            action_room = verbdata[3]
            if not self.check_person(action, parsed):
                raise ParseError("The verb %s needs a person." % parsed.verb)
            action = action.replace(" \nWHERE", where)
            action_room = action_room.replace(" \nWHERE", where)
            action = action.replace(" \nWHAT", message)
            action = action.replace(" \nMSG", msg)
            action_room = action_room.replace(" \nWHAT", message)
            action_room = action_room.replace(" \nMSG", msg)
            action = action.replace(" \nHOW", how)
            action_room = action_room.replace(" \nHOW", how)
            return result_messages(action, action_room)
        elif vtype == verbdefs.QUAD:
            if parsed.who_info:
                action = verbdata[4]
                action_room = verbdata[5]
            else:
                action = verbdata[2]
                action_room = verbdata[3]
            action = action.replace(" \nWHERE", where)
            action_room = action_room.replace(" \nWHERE", where)
            action = action.replace(" \nWHAT", message)
            action = action.replace(" \nMSG", msg)
            action_room = action_room.replace(" \nWHAT", message)
            action_room = action_room.replace(" \nMSG", msg)
            action = action.replace(" \nHOW", how)
            action_room = action_room.replace(" \nHOW", how)
            return result_messages(action, action_room)
        elif vtype == verbdefs.FULL:
            raise TaleError("vtype verbdefs.FULL")  # doesn't matter, verbdefs.FULL is not used yet anyway
        elif vtype == verbdefs.DEFA:
            action = parsed.verb + "$ \nHOW \nAT"
        elif vtype == verbdefs.PREV:
            action = parsed.verb + "$" + self.spacify(verbdata[2]) + " \nWHO \nHOW"
        elif vtype == verbdefs.PHYS:
            action = parsed.verb + "$" + self.spacify(verbdata[2]) + " \nWHO \nHOW \nWHERE"
        elif vtype == verbdefs.SHRT:
            action = parsed.verb + "$" + self.spacify(verbdata[2]) + " \nHOW"
        elif vtype == verbdefs.PERS:
            action = verbdata[3] if parsed.who_count else verbdata[2]
        elif vtype == verbdefs.SIMP:
            action = verbdata[2]
        else:
            raise TaleError("invalid vtype " + vtype)

        if parsed.who_info and len(verbdata) > 3:
            action = action.replace(" \nAT", self.spacify(verbdata[3]) + " \nWHO")
        else:
            action = action.replace(" \nAT", "")

        if not self.check_person(action, parsed):
            raise ParseError("The verb %s needs a person." % parsed.verb)

        action = action.replace(" \nHOW", how)
        action = action.replace(" \nWHERE", where)
        action = action.replace(" \nWHAT", message)
        action = action.replace(" \nMSG", msg)
        action_room = action
        action = action.replace("$", "")
        action_room = action_room.replace("$", "s")
        return result_messages(action, action_room)

    def parse(self, player: Living, cmd: str, external_verbs: Set[str]=set()) -> ParseResult:
        """Parse a command string, returns a ParseResult object."""
        qualifier = ""
        message_verb = False  # does the verb expect a message?
        external_verb = False  # is it a non-soul verb?
        adverb = ""
        message = []  # type: List[str]
        bodypart = ""
        arg_words = []  # type: List[str]
        unrecognized_words = []   # type: List[str]
        who_info = ParseResult.WhoInfoOrderedDict()
        who_list = []   # type: List[ParsedWhoType]
        who_sequence = 0
        unparsed = cmd

        # a substring enclosed in quotes will be extracted as the message
        m = self._quoted_message_regex.search(cmd)
        if m:
            message = [(m.group("msg1") or m.group("msg2")).strip()]
            cmd = cmd[:m.start()] + cmd[m.end():]

        if not cmd:
            raise ParseError("What?")
        words = cmd.split()
        if words[0] in verbdefs.ACTION_QUALIFIERS:     # suddenly, fail, ...
            qualifier = words.pop(0)
            unparsed = unparsed[len(qualifier):].lstrip()
            if qualifier == "dont":
                qualifier = "don't"  # little spelling suggestion
            # note: don't add qualifier to arg_words
        if words and words[0] in self._skip_words:
            skipword = words.pop(0)
            unparsed = unparsed[len(skipword):].lstrip()

        if not words:
            raise ParseError("What?")
        verb = None
        if words[0] in external_verbs:    # external verbs have priority above soul verbs
            verb = words.pop(0)
            external_verb = True
            # note: don't add verb to arg_words
        elif words[0] in verbdefs.VERBS:
            verb = words.pop(0)
            verbdata = verbdefs.VERBS[verb][2]
            message_verb = "\nMSG" in verbdata or "\nWHAT" in verbdata
            # note: don't add verb to arg_words
        elif player.location.exits:
            # check if the words are the name of a room exit.
            move_action = None
            if words[0] in verbdefs.MOVEMENT_VERBS:
                move_action = words.pop(0)
                if not words:
                    raise ParseError("%s where?" % lang.capital(move_action))
            exit, exit_name, wordcount = self.check_name_with_spaces(words, 0, {}, {}, player.location.exits)
            if exit:
                if wordcount != len(words):
                    raise ParseError("What do you want to do with that?")
                unparsed = unparsed[len(exit_name or ""):].lstrip()
                who_info = ParseResult.WhoInfoOrderedDict()
                raise NonSoulVerb(ParseResult(verb=exit_name or "", who_list=[exit], qualifier=qualifier, unparsed=unparsed))
            elif move_action:
                raise ParseError("You can't %s there." % move_action)
            else:
                # can't determine verb at this point, just continue with verb=None
                pass
        else:
            # can't determine verb at this point, just continue with verb=None
            pass

        if verb:
            unparsed = unparsed[len(verb):].lstrip()
        include_flag = True
        collect_message = False
        all_livings = {}  # livings in the room (including player) by name + aliases
        all_items = {}  # all items in the room or player's inventory, by name + aliases
        for living in player.location.livings:
            all_livings[living.name] = living
            for alias in living.aliases:
                all_livings[alias] = living
        for item in player.location.items:
            all_items[item.name] = item
            for alias in item.aliases:
                all_items[alias] = item
        for item in player.inventory:
            all_items[item.name] = item
            for alias in item.aliases:
                all_items[alias] = item
        previous_word = None
        words_enumerator = enumerate(words)
        for index, word in words_enumerator:
            if collect_message:
                message.append(word)
                arg_words.append(word)
                previous_word = word
                continue
            if not message_verb and not collect_message:
                word = word.rstrip(",")
            if word in ("them", "him", "her", "it"):
                if self.__previously_parsed:
                    # try to connect the pronoun to a previously parsed item/living
                    prev_who_list = self.match_previously_parsed(player, word)
                    if prev_who_list:
                        for who, name in prev_who_list:
                            if include_flag:
                                who_info[who].sequence = who_sequence
                                who_info[who].previous_word = previous_word
                                who_sequence += 1
                                who_list.append(who)
                            else:
                                del who_info[who]
                                who_list.remove(who)
                            arg_words.append(name)  # put the replacement-name in the args instead of the pronoun
                    previous_word = None
                    continue
                raise ParseError("It is not clear who you mean.")
            if word in ("me", "myself", "self"):
                if include_flag:
                    who_info[player].sequence = who_sequence
                    who_info[player].previous_word = previous_word
                    who_sequence += 1
                    who_list.append(player)
                elif player in who_info:
                    del who_info[player]
                    who_list.remove(player)
                arg_words.append(word)
                previous_word = None
                continue
            if word in verbdefs.BODY_PARTS:
                if bodypart:
                    raise ParseError("You can't do that both %s and %s." % (verbdefs.BODY_PARTS[bodypart], verbdefs.BODY_PARTS[word]))
                if (word not in all_items and word not in all_livings) or previous_word == "my":
                    bodypart = word
                    arg_words.append(word)
                    continue
            if word in ("everyone", "everybody", "all"):
                if include_flag:
                    if not all_livings:
                        raise ParseError("There is nobody here.")
                    # include every *living* thing visible, don't include items, and skip the player itself
                    for living in player.location.livings:
                        if living is not player:
                            who_info[living].sequence = who_sequence
                            who_info[living].previous_word = previous_word
                            who_sequence += 1
                            who_list.append(living)
                else:
                    who_info.clear()
                    who_list.clear()
                    who_sequence = 0
                arg_words.append(word)
                previous_word = None
                continue
            if word == "everything":
                raise ParseError("You can't do something to everything around you, be more specific.")
            if word in ("except", "but"):
                include_flag = not include_flag
                arg_words.append(word)
                continue
            if word in lang.ADVERBS:
                if adverb:
                    raise ParseError("You can't do that both %s and %s." % (adverb, word))
                adverb = word
                arg_words.append(word)
                continue
            if word in all_livings:
                living = all_livings[word]
                if include_flag:
                    who_info[living].sequence = who_sequence
                    who_info[living].previous_word = previous_word
                    who_sequence += 1
                    who_list.append(living)
                elif living in who_info:
                    del who_info[living]
                    who_list.remove(living)
                arg_words.append(word)
                previous_word = None
                continue
            if word in all_items:
                item = all_items[word]
                if include_flag:
                    who_info[item].sequence = who_sequence
                    who_info[item].previous_word = previous_word
                    who_sequence += 1
                    who_list.append(item)
                elif item in who_info:
                    del who_info[item]
                    who_list.remove(item)
                arg_words.append(word)
                previous_word = None
                continue
            if player.location:
                exit, exit_name, wordcount = self.check_name_with_spaces(words, index, {}, {}, player.location.exits)
                if exit:
                    who_info[exit].sequence = who_sequence
                    who_info[exit].previous_word = previous_word
                    previous_word = None
                    who_sequence += 1
                    who_list.append(exit)
                    if exit_name:
                        arg_words.append(exit_name)
                    while wordcount > 1:
                        next(words_enumerator)
                        wordcount -= 1
                    continue
            item_or_living, full_name, wordcount = self.check_name_with_spaces(words, index, all_livings, all_items, {})
            if item_or_living:
                while wordcount > 1:
                    next(words_enumerator)
                    wordcount -= 1
                if include_flag:
                    who_info[item_or_living].sequence = who_sequence
                    who_info[item_or_living].previous_word = previous_word
                    who_sequence += 1
                    who_list.append(item_or_living)
                elif item_or_living in who_info:
                    del who_info[item_or_living]
                    who_list.remove(item_or_living)
                if full_name:
                    arg_words.append(full_name)
                previous_word = None
                continue
            if message_verb and not message:
                collect_message = True
                message.append(word)
                arg_words.append(word)
                continue
            if word not in self._skip_words:
                # unrecognized word, check if it could be a person's name or an item. (prefix)
                if not who_list:
                    for name in all_livings:
                        if name.startswith(word):
                            raise ParseError("Perhaps you meant %s?" % name)
                    for name in all_items:
                        if name.startswith(word):
                            raise ParseError("Perhaps you meant %s?" % name)
                if not external_verb:
                    if not verb:
                        raise UnknownVerbException(word, words, qualifier)
                    # check if it is a prefix of an adverb, if so, suggest a few adverbs
                    adverbs = lang.adverb_by_prefix(word)
                    if len(adverbs) == 1:
                        word = adverbs[0]
                        if adverb:
                            raise ParseError("You can't do that both %s and %s." % (adverb, word))
                        adverb = word
                        arg_words.append(word)
                        previous_word = word
                        continue
                    elif len(adverbs) > 1:
                        raise ParseError("What adverb did you mean: %s?" % lang.join(adverbs, conj="or"))

                if external_verb:
                    arg_words.append(word)
                    unrecognized_words.append(word)
                else:
                    if word in verbdefs.VERBS or word in verbdefs.ACTION_QUALIFIERS or word in verbdefs.BODY_PARTS:
                        # in case of a misplaced verb, qualifier or bodypart give a little more specific error
                        raise ParseError("The word %s makes no sense at that location." % word)
                    else:
                        # no idea what the user typed, generic error
                        errormsg = "It's not clear what you mean by '%s'." % word
                        if word[0].isupper():
                            errormsg += " Just type in lowercase ('%s')." % word.lower()
                        raise ParseError(errormsg)
            previous_word = word

        message_text = " ".join(message)
        if not verb:
            # This is interesting: there's no verb.
            # but maybe the thing the user typed refers to an object or creature.
            # In that case, set the verb to that object's default verb.
            if len(who_list) == 1:
                verb = getattr(who_list[0], "default_verb", "examine")
            else:
                raise UnknownVerbException(words[0], words, qualifier)
        return ParseResult(verb or "", who_info=who_info, who_list=who_list,
                           adverb=adverb, message=message_text, bodypart=bodypart, qualifier=qualifier,
                           args=arg_words, unrecognized=unrecognized_words, unparsed=unparsed)

    def remember_previous_parse(self, parsed: ParseResult) -> None:
        self.__previously_parsed = parsed

    def match_previously_parsed(self, player: Living, pronoun: str) -> List[Tuple[Any, str]]:
        """
        Try to connect the pronoun (it, him, her, them) to a previously parsed item/living.
        Returns a list of (who, replacement-name) tuples.
        The reason we return a replacement-name is that the parser can replace the
        pronoun by the proper name that would otherwise have been used in that place.
        """
        if pronoun == "them":
            # plural (any item/living qualifies)
            matches = list(self.__previously_parsed.who_info)
            for who in matches:
                if not player.search_item(who.name) and who not in player.location.livings:
                    player.tell("<dim>(By '%s', we assume you meant %s.)</>" % (pronoun, who.title))
                    raise ParseError("%s is no longer around." % lang.capital(who.subjective))
            if matches:
                player.tell("<dim>(By '%s', we assume you meant %s.)</>" % (pronoun, lang.join(who.title for who in matches)))
                return [(who, who.name) for who in matches]
            else:
                raise ParseError("It is not clear who or what you're referring to.")
        for who in self.__previously_parsed.who_info:
            # first see if it is an exit
            if pronoun == "it":
                for direction, exit in player.location.exits.items():
                    if exit is who:
                        player.tell("<dim>(By '%s', we assume you meant %s.)</>" % (pronoun, direction))
                        return [(who, direction)]
            # not an exit, try an item or a living
            if pronoun == who.objective:
                if player.search_item(who.name) or who in player.location.livings:
                    player.tell("<dim>(By '%s', we assume you meant %s.)</>" % (pronoun, who.title))
                    return [(who, who.name)]
                player.tell("<dim>(By '%s', we assume you meant %s.)</>" % (pronoun, who.title))
                raise ParseError("%s is no longer around." % lang.capital(who.subjective))
        raise ParseError("It is not clear who or what you're referring to.")

    @staticmethod
    def poss_replacement(actor: Living, target: Union[MudObject, None], observer: Optional[Living]) -> str:
        """determines what word to use for a POSS"""
        if target is actor:
            if actor is observer:
                return "your own"       # your own foot
            else:
                return actor.possessive + " own"   # his own foot
        else:
            if target is observer:
                return "your"           # your foot
            elif target:
                return lang.possessive(target.title)
            else:
                raise TaleError("cannot determine POSS for None target")

    def spacify(self, string: str) -> str:
        """returns string prefixed with a space, if it has contents. If it is empty, prefix nothing"""
        return " " + string.lstrip(" \t") if string else ""

    def who_replacement(self, actor: Living, target: MudObject, observer: Optional[Living]) -> str:
        """determines what word to use for a WHO"""
        if target is actor:
            if actor is observer:
                return "yourself"       # you kick yourself
            else:
                return actor.objective + "self"    # ... kicks himself
        else:
            if target is observer:
                return "you"            # ... kicks you
            else:
                return target.title      # ... kicks ...

    def check_person(self, action: str, parsed: ParseResult) -> bool:
        if not parsed.who_info and ("\nWHO" in action or "\nPOSS" in action):
            return False
        return True

    def check_name_with_spaces(self, words: Sequence[str], startindex: int, all_livings: Dict[str, Living],
                               all_items: Dict[str, Item], all_exits: Dict[str, Exit]) \
            -> Tuple[Optional[ParsedWhoType], str, int]:
        """
        Searches for a name used in sentence where the name consists of multiple words (separated by space).
        You provide the sequence of words that forms the sentence and the startindex of the first word
        to start searching.
        Searching is done in the livings, items, and exits dictionaries, in that order.
        The name being searched for is gradually extended with more words until a match is found.
        The return tuple is (matched_object, matched_name, number of words used in match).
        If nothing is found, a tuple (None, None, 0) is returned.
        """
        wordcount = 1
        name = words[startindex]
        try:
            while wordcount < 6:    # an upper bound for the number of words to concatenate to avoid long runtime
                if name in all_livings:
                    return all_livings[name], name, wordcount
                if name in all_items:
                    return all_items[name], name, wordcount
                if name in all_exits:
                    return all_exits[name], name, wordcount
                name = name + " " + words[startindex + wordcount]
                wordcount += 1
        except IndexError:
            pass
        return None, "", 0


_limbo = Location("Limbo", "The intermediate or transitional place or state. There's only nothingness. "
                           "Living beings end up here if they're not in a proper location yet.")
