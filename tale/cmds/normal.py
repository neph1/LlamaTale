"""
Normal player commands.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import itertools
import random
from typing import Iterable, List, Dict, Generator, Union, Optional

from . import abbreviations, cmd, disabled_in_gamemode, disable_notify_action, overrides_soul, no_soul_parse
from .. import base
from .. import lang
from .. import races
from .. import util
from .. import cmds
from ..accounts import MudAccounts
from ..errors import ParseError, ActionRefused, SessionExit, RetrySoulVerb, RetryParse
from ..items.basic import GameClock, Money
from ..player import Player
from ..story import GameMode
from ..verbdefs import VERBS, ACTION_QUALIFIERS, BODY_PARTS, AGGRESSIVE_VERBS
from tale.wearable import WearLocation


@cmd("inventory")
@disable_notify_action
def do_inventory(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Show the items you are carrying."""
    if parsed.who_info and "wizard" in player.privileges:
        # wizards may look at the inventory of everything else
        other = parsed.who_1
        other.show_inventory(player, ctx)
    else:
        inventory = player.inventory
        if inventory:
            player.tell("You are carrying:", end=True)
            for item in inventory:
                player.tell("  %s" % item.title, format=False)
        else:
            player.tell("You are carrying nothing.")
        if ctx.config.money_type:
            player.tell("Money in possession: %s." % ctx.driver.moneyfmt.display(player.money, zero_msg="you are broke"))


@cmd("locate", "search", "find")
def do_locate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Try to locate a specific item, creature or player."""
    p = player.tell
    if not parsed.args:
        raise ParseError("Locate what/who?")
    if len(parsed.args) > 1 or parsed.who_count > 1:
        raise ParseError("Can only search for one thing at a time.")
    name = parsed.args[0]
    p("You look around to see if you can locate %s." % name)
    player.tell_others("{Actor} looks around.")
    if parsed.who_count:
        thing = parsed.who_1
        if thing is player:
            p("You are here, in <location>%s</>." % player.location.name)
            return
        if thing in player.location:
            if isinstance(thing, base.Living):
                p("%s is here next to you." % lang.capital(thing.title))
            else:
                player.tell_object_location(thing, player.location, False)
        elif thing in player:
            player.tell_object_location(thing, player, False)
        else:
            p("You can't find that.")
    else:
        # The default parser checks inventory and location, but it didn't find anything.
        # Check inside containers in the player's inventory instead.
        item, container = player.locate_item(name, include_inventory=False, include_location=False, include_containers_in_inventory=True)
        if item:
            player.tell_object_location(item, container, False)
        else:
            otherplayer = ctx.driver.search_player(name)  # global player search
            if otherplayer:
                player.tell("%s is playing, %s is currently in '<location>%s</>'." %
                            (lang.capital(otherplayer.title), otherplayer.subjective, otherplayer.location.name))
            else:
                p("You can't find that.")


@cmd("drop")
def do_drop(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Drop an item (or all items) you are carrying."""
    if not parsed.args:
        raise ParseError("Drop what?")

    def drop_stuff(items, container):
        items = list(items)
        refused = []
        for item in items:
            try:
                item.move(player.location, player, verb="drop")
                if container is not player and container in player:
                    print_item_removal(player, item, container)
            except ActionRefused as x:
                refused.append((item, str(x)))
        for item, message in refused:
            items.remove(item)
            player.tell(message)
        if items:
            items_str = lang.join(lang.a(item.title) for item in items)
            player.tell("You drop %s." % items_str)
            player.tell_others("{Actor} drops %s." % items_str)
        else:
            player.tell("You didn't drop anything.")

    arg = parsed.args[0]
    if arg == "all":
        if player.inventory_size == 0:
            raise ActionRefused("You're not carrying anything.")
        else:
            if (yield "input", ("Are you sure you want to drop all you are carrying?", lang.yesno)):
                drop_stuff(player.inventory, player)
            else:
                player.tell("You hold onto your stuff.")
    else:
        # drop a single item from the inventory (or a container in the inventory), or perhaps some coins
        item = None  # type: Optional[base.ParsedWhoType]
        if parsed.who_count:
            item = parsed.who_1
            if item in player:
                drop_stuff([item], player)
            else:
                raise ActionRefused("You can't drop that.")
        else:
            item, container = player.locate_item(arg, include_location=False)
            if item:
                if container is not player:
                    player.tell_object_location(item, container)
                drop_stuff([item], container)
            else:
                # perhaps it's some money then?
                try:
                    amount = ctx.driver.moneyfmt.parse(parsed.args)
                except ParseError:
                    raise ActionRefused("You don't have %s." % lang.a(arg))
                if amount > player.money:
                    raise ActionRefused("You don't have that much money.")
                money = Money(ctx.driver.moneyfmt.money_name, amount)
                money.add_to_location(player.location, player)
                player.money -= amount
                player.tell("You reach into your pockets and put %s on the ground." % ctx.driver.moneyfmt.display(amount, short=True))
                player.tell_others("{Actor} reaches into %s pockets and puts some %s on the ground."
                                   % (player.possessive, ctx.driver.moneyfmt.money_name))


@cmd("empty")
def do_empty(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Remove the contents from an object."""
    if len(parsed.args) != 1 or not parsed.who_info:
        if parsed.args[0] in ("bags", "pockets"):
            raise RetryParse("drop all")
        raise ParseError("Empty what or who?")
    if parsed.who_count > 1:
        raise ParseError("Please be more specific, only empty one thing at a time.")
    container = parsed.who_1
    if not isinstance(container, base.Container):
        raise ActionRefused("You can't take anything from %s." % container.title)
    if container in player.location:
        # move the contents to the room
        target = player.location        # type: base.ContainingType
        action = "dropped"
    elif container in player:
        # move the contents to the player's inventory
        target = player
        action = "took"
    else:
        raise ParseError("You can't seem to empty that.")
    items_moved = []
    for item in container.inventory:
        try:
            item.move(target, player)
            items_moved.append(item.title)
        except ActionRefused as x:
            player.tell(str(x))
    if items_moved:
        itemnames = lang.join(items_moved)
        player.tell("You %s: %s." % (action, itemnames))
        player.tell_others("{Actor} %s: %s." % (action, itemnames))
    else:
        player.tell("You %s nothing." % action)


@cmd("put", "place")
def do_put(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Put an item (or all items) into something else. If you're not carrying the item, you will first pick it up."""
    p = player.tell
    if len(parsed.args) < 2:
        raise ParseError("Put what where?")
    if parsed.args[0] == "all":
        if player.inventory_size == 0:
            raise ActionRefused("You're not carrying anything.")
        if len(parsed.args) != 2:
            raise ParseError("Put what where?")
        what = list(player.inventory)
        where = parsed.who_last   # last object is where to put the stuff
        if what:
            if not (yield "input", ("Are you sure you want to put everything away?", lang.yesno)):
                p("You leave everything where it is.")
                return
    elif parsed.unrecognized:
        raise ActionRefused("You don't see %s." % lang.join(parsed.unrecognized))
    else:
        whos = list(parsed.who_info)
        what = whos[:-1]
        where = whos[-1]
    if isinstance(where, base.Living):
        raise ActionRefused("You can't put stuff in %s, try giving it to %s?" % (where.name, where.objective))
    inventory_items = []
    refused = []
    word_before = parsed.who_info[where].previous_word or "in"
    if word_before != "in" and word_before != "into":
        raise ActionRefused("You can't do that.")  # only supports put X in Y
    for item in what:
        if item is where:
            p("You can't put %s %s itself." % (item.title, word_before))
            continue
        if item is player:
            p("What did you mean to do with yourself?")
            continue
        try:
            if item in player:
                # simply use the item from the player's inventory
                item.move(where, player)
                inventory_items.append(item)
            elif item in player.location.items:
                # first take the item from the room, then move it to the target location
                item.move(player, player)
                p("You take %s." % item.title)
                player.tell_others("{Actor} takes %s." % item.title)
                item.move(where, player)
                p("You put it in the %s." % where.name)
                player.tell_others("{Actor} puts it in the %s." % where.name)
            else:
                p("You can't put %s somewhere else." % item.title)
                continue
        except ActionRefused as x:
            refused.append((item, str(x)))
    for item, message in refused:
        p(message)
    if inventory_items:
        items_msg = lang.join(lang.a(item.title) for item in inventory_items)
        player.tell_others("{Actor} puts %s in the %s." % (items_msg, where.name))
        p("You put {items} in the {where}.".format(items=items_msg, where=where.name))


def replace_items(player: Player, existing: List[base.Item], replacement: base.Item,
                  message: str, others_message: str, ctx: util.Context) -> None:
    # removes all existing items from player's inventory and replaces them with the given replacement item
    if any(item not in player for item in existing):
        raise ParseError("can only replace items that are in player's inventory")
    try:
        for item in existing:
            player.remove(item, player)
    except ActionRefused:
        # restore items
        for item in existing:
            player.insert(item, player)
        raise
    try:
        player.insert(replacement, player)
    except ActionRefused:
        # restore items
        for item in existing:
            player.insert(item, player)
        raise
    else:
        for item in existing:
            item.destroy(ctx)
            del item
        if message:
            player.tell(message)
        if others_message:
            player.tell_others(others_message)


@cmd("attach", "apply", "install")
def do_combine_two(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Combine two items you are carrying by attaching them, applying them or installing them together.
    If successful, this can perhaps result in a new item!"""
    if parsed.who_count != 2:
        if parsed.verb == "attach":
            raise ParseError("Attach what to what?")
        if parsed.verb == "apply":
            raise ParseError("Apply what to what?")
        if parsed.verb == "install":
            raise ParseError("Install what on what?")
        return
    item1, item2 = tuple(parsed.who_info)
    if item1 not in player or item2 not in player:
        raise ActionRefused("You are not carrying both, try to pick them up first.")
    try:
        result = item2.combine([item1], player)
        if result:
            replace_items(player, [item1, item2], result, "You created %s!" % lang.a(result.title),
                          "{Actor} tinkers with some things %s carries." % player.subjective, ctx)
            return
    except ActionRefused:
        pass
    result = item1.combine([item2], player)
    if not result:
        raise ActionRefused("You can't combine those.")
    replace_items(player, [item1, item2], result, "You created %s!" % lang.a(result.title),
                  "{Actor} tinkers with some things %s carries." % player.subjective, ctx)


@cmd("combine")
def do_combine_many(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Combine two or more items you are carrying. If successful, this can perhaps result in a new item!"""
    if parsed.who_count == 1:
        raise ParseError("Combine %s with what?" % parsed.who_1.title)
    if parsed.who_count < 2:
        raise ParseError("Combine which things?")
    if any(item not in player for item in parsed.who_info):
        raise ActionRefused("You should pick all of those up first if you want to combine them.")
    # 'combine W and X and Y and Z' -> first try (w,x,y) on Z, then (x,y,z) on W as second option
    all_who = list(parsed.who_info)
    item, others = all_who[-1], all_who[:-1]
    try:
        result = item.combine(others, player)
        if result is not None:
            replace_items(player, others + [item], result, "You created %s!" % lang.a(result.title),
                          "{Actor} tinkers with some things %s carries." % player.subjective, ctx)
            return
    except ActionRefused:
        pass
    item, others = all_who[0], all_who[1:]
    try:
        result = item.combine(others, player)
        if result is not None:
            replace_items(player, others + [item], result, "You created %s!" % lang.a(result.title),
                          "{Actor} tinkers with some things %s carries." % player.subjective, ctx)
            return
    except ActionRefused:
        pass
    raise ActionRefused("That didn't work. Perhaps if you try it in a different order, or try it with other things?")


@cmd("loot", "pilfer", "sack")
def do_loot(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Take all things from something or someone else. Keep in mind that stealing and robbing is frowned upon, to say the least."""
    if len(parsed.args) != 1 or not parsed.who_info:
        raise ParseError("Loot what or who?")
    if parsed.who_count > 1:
        raise ParseError("Please be more specific, you can only loot from one thing at a time.")
    container = parsed.who_1
    if not isinstance(container, base.Container):
        raise ActionRefused("You can't take anything from %s." % container.title)
    raise RetryParse("take all from " + parsed.who_1.name)


@cmd("take", "get", "steal", "rob")
def do_take(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Take something (or all things) from the room, or something or someone else.
    Keep in mind that stealing and robbing is frowned upon, to say the least."""
    p = player.tell
    if len(parsed.args) == 0:
        raise ParseError("Take what?")
    if len(parsed.args) == 1:  # take thing|all
        what_names = parsed.args
        where = None
    else:
        if parsed.who_info:
            last_obj = parsed.who_last
            if parsed.who_info[last_obj].previous_word == "from":
                # take x[,y and z] from something
                what_names = parsed.args[:-1]
                where = last_obj
            else:
                # take x[,y and z]
                what_names = parsed.args
                where = None
        else:
            # take x[,y and z] - unrecognised names
            what_names = parsed.args
            where = None
    if where is player:
        raise ActionRefused("There's no reason to take things from yourself.")
    if isinstance(where, base.Living):
        player.tell_others("{Actor} tries to steal things from %s." % where.title)
        if where.aggressive:
            where.start_attack(player)  # stealing stuff is a hostile act!
        raise ActionRefused("You can't just steal stuff from %s!" % where.title)
    elif parsed.verb == "steal" or parsed.verb == "rob":
        if where is None:
            raise ActionRefused("Steal what from whom?")
        raise ActionRefused("You can't steal stuff from an object. Try taking it instead.")
    if what_names == ["all"]:   # take ALL the things!
        if where:
            # take all stuff out of some container
            if where in player or where in player.location:
                # take all stuff from a bag that the player is carrying, or from a bag in the room.
                if where.inventory_size > 0:
                    take_stuff(player, where.inventory, where, where.title)
                    return
                else:
                    raise ActionRefused("There's nothing in there.")
            raise ActionRefused("Take what?")
        else:
            # take all stuff out of the room
            if not player.location.items:
                raise ActionRefused("There's nothing here to take.")
            else:
                take_stuff(player, player.location.items, player.location)
                return
    else:   # take one or more specific items
        if where:
            if where in player or where in player.location:
                # take specific items out of some container
                items_by_name = {item.name: item for item in where.inventory}
                items_to_take = []
                for name in what_names:
                    if name in items_by_name:
                        items_to_take.append(items_by_name[name])
                    else:
                        p("There's no %s in there." % name)
                take_stuff(player, items_to_take, where, where.title)
                return
        else:
            # take things from the room
            if parsed.unrecognized:
                p("You don't see %s." % lang.join(parsed.unrecognized))
            livings = [item for item in parsed.who_info if item in player.location.livings]
            for living in livings:
                try_pick_up_living(player, living)
            if not player.location.items:
                raise ActionRefused("There's nothing here to take.")
            else:
                items_to_take = []
                for item in parsed.who_info:
                    if item in player.location.items:
                        items_to_take.append(item)
                    elif isinstance(item, base.Exit):
                        raise ActionRefused("You can't pick that up.")
                    elif item not in player.location.livings:
                        if item in player:
                            other_item = player.search_item(item.name, False, True, False)  # look outside of inventory
                            if other_item:
                                p("There's another one here!")
                                items_to_take.append(other_item)
                            else:
                                p("You've already got it.")
                        else:
                            p("There's no %s here." % item.name)
                take_stuff(player, items_to_take, player.location)
                return
            p("Take things from what?")


def take_stuff(player: Player, items: Iterable[base.Item], container: base.MudObject, where_str: str="") -> int:
    """Takes stuff and returns the number of items taken"""
    if not items:
        return 0
    if where_str:
        player_msg = "You take {items} from the %s." % where_str
        room_msg = "{{Actor}} takes {items} from the %s." % where_str
    else:
        player_msg = "You take {items}."
        room_msg = "{{Actor}} takes {items}."
    items = list(items)
    refused = []
    for item in items:
        try:
            item.move(player, player, verb="take")
        except ActionRefused as x:
            refused.append((item, str(x)))
    for item, message in refused:
        player.tell(message)
        items.remove(item)
    if items:
        items_str = lang.join(lang.a(item.title) for item in items)
        player.tell(player_msg.format(items=items_str))
        player.tell_others(room_msg.format(items=items_str))
        return len(items)
    else:
        return 0


def try_pick_up_living(player: Player, living: base.Living) -> None:
    if player.stats.size - living.stats.size >= 2:
        player.tell("Even though {subj}'s small enough, you can't carry {obj} with you."
                    .format(subj=living.subjective, obj=living.objective))
        if living.aggressive:
            player.tell("Trying to pick {0} up wasn't a very good idea, you've made {0} angry!".format(living.objective))
            living.start_attack(player)
    else:
        player.tell("You can't carry {obj} with you, {subj}'s too large.".format(subj=living.subjective, obj=living.objective))


@cmd("throw")
def do_throw(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Throw something you are carrying at someone or something. If you don't have it yet, you will first pick it up."""
    if parsed.who_count != 2:
        raise ParseError("Throw what where?")
    item, where = parsed.who_12
    if isinstance(item, base.Living):
        raise ActionRefused("You can't throw that.")
    if item in player.location:
        # first take the item from the room
        item.move(player, player, verb="take")
        player.tell("You take %s." % item.title)
        player.tell_others("{Actor} takes %s." % item.title)
    # throw the item back into the room, missing the target by a hair. Possibly start combat.
    item.move(player.location, player, verb="throw")
    player.tell("You throw the %s at %s, missing %s by a hair." % (item.title, where.title, where.objective))
    player.tell_others("{Actor} throws the %s at %s, missing %s by a hair." % (item.title, where.title, where.objective))
    if isinstance(where, base.Living) and where.aggressive:
        where.start_attack(player)


@cmd("give")
def do_give(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Give something (or all things) you are carrying to someone else."""
    if len(parsed.args) < 2:
        raise ParseError("Give what to whom?")
    if parsed.who_count == 1:
        # first try if the first one or two words can be interpreted as an amount of money
        if ctx.config.money_type:
            try:
                amount = ctx.driver.moneyfmt.parse(parsed.unrecognized)
            except (ValueError, ParseError):
                pass   # go on below
            else:
                # we're giving some money away
                recipient = parsed.who_1
                if not recipient:
                    raise ActionRefused("Give it to whom?")
                if not isinstance(recipient, base.Living):
                    raise ActionRefused("You can't do that.")
                if recipient is player:
                    raise ActionRefused("There's no reason to give it to yourself.")
                if amount <= 0:
                    raise ActionRefused("You don't give away anything.")
                elif player.money < amount:
                    raise ActionRefused("You don't have that amount of wealth.")
                else:
                    recipient.allow_give_money(amount, player)
                    if (yield "input", ("Are you sure you want to give %s away?" % ctx.driver.moneyfmt.display(amount), lang.yesno)):
                        player.money -= amount
                        recipient.money += amount
                        amount_formatted = ctx.driver.moneyfmt.display(amount)
                        player_title = lang.capital(player.title)
                        room_msg = "%s gave %s some money." % (player_title, recipient.title)
                        recipient_msg = "%s gave you %s." % (player_title, amount_formatted)
                        player.location.tell(room_msg, player, {recipient}, recipient_msg)
                        player.tell("You gave %s %s." % (recipient.title, amount_formatted))
                        return
                    else:
                        raise ActionRefused("You keep your money.")
    if parsed.unrecognized:
        raise ParseError("You don't have %s." % lang.join(parsed.unrecognized))
    if player.inventory_size == 0:
        raise ActionRefused("You're not carrying anything.")
    # check for "all"
    if "all" in parsed.args:
        if len(parsed.args) != 2:
            raise ParseError("Give all to who?")
        what = player.inventory
        if what:
            if not (yield "input", ("Are you sure you want to give it all away?", lang.yesno)):
                player.tell("You leave everything where it is.")
                return
        if parsed.args[0] == "all":
            # give all [to] living
            give_stuff(player, what, parsed.args[1])
            return
        else:
            # give living all
            give_stuff(player, what, parsed.args[0])
            return

    # give one or more specific items.
    if len([who for who in parsed.who_info if isinstance(who, base.Living)]) > 1:
        # if there's more than one living, it's not clear who to give stuff to
        raise ActionRefused("It's not clear who you want to give things to.")
    if isinstance(parsed.who_1, base.Living):
        # if the first is a living, assume "give living [the] thing(s)"
        things = list(parsed.who_info)[1:]
        give_stuff(player, things, "", target=parsed.who_1)
        return
    elif isinstance(parsed.who_last, base.Living):
        # if the last is a living, assume "give thing(s) [to] living"
        things = list(parsed.who_info)[:-1]
        give_stuff(player, things, "", target=parsed.who_last)
        return
    else:
        raise ActionRefused("It's not clear who you want to give things to.")


def give_stuff(player: Player, items: Iterable[base.Item], target_name: str, target: Union[base.Living, base.Item, base.Exit]=None) -> None:
    p = player.tell
    if not target:
        target = player.location.search_living(target_name)
    if not target:
        raise ActionRefused("%s isn't here." % target_name)
    if target is player:
        raise ActionRefused("There's no reason to give things to yourself.")
    if not isinstance(target, (base.Location, base.Container, base.Living)):
        raise ActionRefused("You cannot do that.")
    items = list(items)
    refused = []
    for item in items:
        try:
            item.move(target, player)
        except ActionRefused as x:
            refused.append((item, str(x)))
    have_refused_message = False
    for item, message in refused:
        if message:
            p(message)
            have_refused_message = True
        items.remove(item)
    if items:
        items_str = lang.join(lang.a(item.title) for item in items)
        player_str = lang.capital(player.title)
        room_msg = "%s gives %s to %s." % (player_str, items_str, target.title)
        target_msg = "%s gives you %s." % (player_str, items_str)
        player.location.tell(room_msg, exclude_living=player, specific_targets={target}, specific_target_msg=target_msg)
        p("You give %s %s." % (target.title, items_str))
    elif not have_refused_message:
        p("You didn't give %s anything." % target.title)


@cmd("help")
@disable_notify_action
def do_help(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Provides some helpful information about different aspects of the game. Also try 'hint' or 'recap'."""
    if parsed.args:
        do_what(player, parsed, ctx)
    else:
        all_verbs = ctx.driver.current_verbs(player)
        verb_help = {}   # type: Dict[str, List[str]]  # verb -> [list of abbrs]
        aliases = frozenset(itertools.chain(*cmds.cmds_aliases.values()))
        for verb in all_verbs:
            if verb not in aliases:
                verb_help[verb] = []
        abbrevs = dict(abbreviations)
        for abbr, verb in abbreviations.items():
            if verb in verb_help:
                verb_help[verb].append(abbr)
                del abbrevs[abbr]
        cmds_help = []
        for verb, abbrs in verb_help.items():
            if abbrs:
                verb += "/" + "/".join(abbrs)
            cmds_help.append(verb)
        player.tell("<bright>Available commands:</>")
        player.tell(", ".join(sorted(cmds_help)), end=True)
        player.tell("\n")
        if aliases:
            player.tell("<bright>Synonyms:</> a different word for one of the commands mentioned above. "
                        "Makes typing a bit more natural sometimes. The synonyms are: ")
            player.tell(", ".join(sorted(aliases)), end=True)
            player.tell("\n")
        player.tell("<bright>Abbreviations:</>")
        player.tell(", ".join(sorted("%s=%s" % (a, v) for a, v in abbrevs.items())), end=True)
        player.tell("\n")
        player.tell("You can get more info about all kinds of stuff by asking 'what is <topic>' (?topic).")
        player.tell("You can get more info about the 'emote' verbs by asking 'what is soul' (?soul).")
        player.tell("To see all possible verbs ask 'what is emotes' (?emotes).", end=True)


@cmd("look")
@disable_notify_action
def do_look(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Look around to see where you are and what's around you."""
    if parsed.args:
        arg = parsed.args[0]
        # look <direction> is the only thing we support, the rest should be done with examine
        if arg in player.location.exits:
            exit = player.location.exits[arg]
            player.tell(exit.short_description)
            if exit.short_description != exit.description:
                # give a little hint that more information can be gained by examining it
                player.tell("Maybe you should examine it?")
                return
        elif arg in abbreviations and abbreviations[arg] in player.location.exits:
            player.tell(player.location.exits[abbreviations[arg]].short_description)
        elif arg == "around":
            player.look(short=False)
        else:
            raise ParseError("Maybe you should examine that instead.")
    else:
        player.look(short=False)


@cmd("examine", "inspect")
@disable_notify_action
def do_examine(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Examine something or someone thoroughly."""
    p = player.tell
    living = None
    if parsed.who_info and isinstance(parsed.who_1, base.Living):
        living = parsed.who_1
        name = living.name
    if not living:
        if not parsed.args:
            raise ParseError("Examine what or who?")
        remove_is_are_args(parsed.args)
        name = parsed.args[0]
        living = player.location.search_living(name)
    if living:
        if living is player:
            # player examines him/herself
            p("You are %s. But you knew that already." % lang.capital(living.title))
            player.tell_others("{Actor} is looking at %sself." % living.objective, evoke=True, max_length=False)
            return
        # if "wizard" in player.privileges:
        #     tell(repr(living), end=True)
        if living.description:
            p(living.description, evoke=True, max_length=False)
        else:
            p("This is %s." % living.title, evoke=True, max_length=False)
        if ctx.config.display_race and living.stats.race != "human":
            # only print this race related info when dealing with creatures other than humans
            if living.stats.bodytype and living.stats.size:
                p("{subj}'s a {size} {btype} {race}.".format(
                    subj=lang.capital(living.subjective),
                    size=living.stats.size.text,
                    btype=living.stats.bodytype.value,
                    race=living.stats.race or "creature"
                ), evoke=True, max_length=False)
        if name in living.extra_desc:
            p(living.extra_desc[name], evoke=True, max_length=False)   # print the extra description, rather than a generic message
        if name in player.location.extra_desc:
            p(player.location.extra_desc[name], evoke=True, max_length=False)   # print the extra description, rather than a generic message
        if living.following:
            if living.is_pet:
                if living.following is player:
                    p("%s's your loyal pet." % lang.capital(living.subjective), evoke=True, max_length=False)
                else:
                    p("%s's a pet of %s." % (lang.capital(living.subjective), living.following.title), evoke=True, max_length=False)
            else:
                if living.following is player:
                    p("%s's following you." % lang.capital(living.subjective))
                else:
                    p("It seems that %s's following %s." % (living.subjective, living.following.title), evoke=True, max_length=False)
        return
    item, container = player.locate_item(name)
    if item:
        if name in item.extra_desc:
            p(item.extra_desc[name])   # print the extra description, rather than a generic message
        else:
            if item in player:
                p("You're carrying %s." % lang.a(item.title))
            elif container and container in player:
                player.tell_object_location(item, container, True)
            else:
                if not item.description:
                    p("You see %s." % lang.a(item.title))
            if item.description:
                p(item.description)
        try:
            inventory = item.inventory
        except ActionRefused:
            pass
        else:
            if inventory:
                p("It contains: %s." % lang.join(subitem.title for subitem in inventory))
            else:
                p("It's empty.")
    elif name in player.location.exits:
        p("It seems you can go there:")
        p(player.location.exits[name].description)
    elif name in abbreviations and abbreviations[name] in player.location.exits:
        p("It seems you can go there:")
        p(player.location.exits[abbreviations[name]].description)
    else:
        # check if name is in location's or an item's extradesc
        text = player.search_extradesc(name)
        if text:
            p(text)
        else:
            raise ActionRefused("%s isn't here." % name)


@cmd("stats")
@disable_notify_action
@disabled_in_gamemode(GameMode.IF)
def do_stats(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Prints the gender, race and stats information of yourself, or another creature or player."""
    if not parsed.args:
        target = player
    elif parsed.who_count == 1:
        target = parsed.who_1
        if not isinstance(target, base.Living):
            raise ActionRefused("That doesn't have stats.")
    else:
        raise ActionRefused("Show stats from who?")
    gender = lang.GENDERS[target.gender]
    race = target.stats.race or "creature"
    player.tell("%s (%s)" % (target.title, target.name), end=True)
    if target is player:
        # if the target inspected is self, show level as well
        player.tell("Level %d " % target.stats.level)
    if target.stats.size:
        player.tell("%s %s %s." % (lang.capital(target.stats.size.text), gender, race))
    else:
        player.tell("%s %s." % (lang.capital(gender), race))
    if target.stats.bodytype:
        player.tell("%s." % lang.capital(target.stats.bodytype.value))
    if target.stats.weight:
        player.tell("Weighs ~%s kg." % target.stats.weight)
    if target.stats.language:
        player.tell("Speaks %s." % target.stats.language)
    if target.aggressive:
        player.tell("%s seems to be aggressive." % lang.capital(target.subjective))


@cmd("tell")
def do_tell(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Pass a message to another player or creature that nobody else can hear.
    The other player doesn't have to be in the same location as you."""
    if len(parsed.args) < 1:
        raise ActionRefused("Tell whom what?")
    # we can't use parsed.who_info directly, because the message could be directed to a player
    # that is not in the same location (and hence will not appear in parsed.who_info)
    name = parsed.args[0]
    living = player.location.search_living(name)
    if not living:
        living = ctx.driver.search_player(name)   # is there a player around with this name?
        if not living:
            if name == "all":
                raise ActionRefused("You can't tell something to everyone, only to individuals.")
            raise ActionRefused("%s isn't here." % name)
    if living is player:
        player.tell("You're talking to yourself...")
    else:
        unparsed = parsed.unparsed[len(name):].lstrip()
        if unparsed:
            living.tell("%s tells you: %s" % (player.name, unparsed), evoke=True, max_length=False)
            player.tell("You told %s." % name, evoke=True, max_length=False)
        else:
            player.tell("Tell %s what?" % living.objective)


@cmd("emote")
@disabled_in_gamemode(GameMode.IF)
def do_emote(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Emit a custom 'emote' message literally, such as: 'emote looks stupid.' -> '<player> looks stupid."""
    if not parsed.unparsed:
        raise ParseError("Emote what message?")
    emote_msg = lang.capital(player.title) + " " + parsed.unparsed
    if not parsed.unparsed.endswith(("!", "?", ".")):
        emote_msg += "."
    player.tell("You emote: %s" % emote_msg, evoke=True, max_length=False)
    player.tell_others(emote_msg, evoke=True, max_length=False)


@cmd("yell", "shout", "scream")
def do_yell(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Yell something. People in nearby locations will also be able to hear you."""
    if not parsed.unparsed:
        raise ActionRefused("Yell what?")
    message = parsed.unparsed
    if not parsed.unparsed.endswith((".", "!", "?")):
        message += "!"
    player.tell("You %s: %s" % (parsed.verb, message), evoke=True, max_length=False)
    player.tell_others("{Actor} %ss: %s" % (parsed.verb, message), evoke=True, max_length=False)
    # send this to nearby locations as well:
    player.location.message_nearby_locations("Someone nearby is %s: %s" % (lang.fullverb(parsed.verb), message))


@cmd("say", "mention")
@no_soul_parse
def do_say(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Say something to people near you."""
    if not parsed.unparsed:
        raise ActionRefused("Say what?")
    message = parsed.unparsed    # this command is marked @no_soul_parse so everything on the cmd line ends up in here
    if not parsed.unparsed.endswith((".", "!", "?")):
        message += "."
    target = ""
    if parsed.who_count:
        possible_target = parsed.who_1
        if parsed.who_info[possible_target].previous_word == "to":
            if parsed.args[0] in (possible_target.name, possible_target.title) or parsed.args[0] in possible_target.aliases:
                target = " to " + possible_target.title
                _, _, message = message.partition(parsed.args[0])
                message = message.lstrip()
    player.tell("You say%s: %s" % (target, message), evoke=False, max_length=False)
    player.tell_others("{Actor} says%s: %s" % (target, message), evoke=True, max_length=False)


@cmd("wait")
@disabled_in_gamemode(GameMode.MUD)
@overrides_soul
def do_wait(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """
    Let someone know you are waiting for them. Alternatively, you can simply Let time pass.
    For the latter use, you can optionally specify how long you want to wait (in hours, minutes, seconds).
    """
    if "for" in parsed.unrecognized:
        if not parsed.who_info:
            raise ActionRefused("Who exactly do you want to wait for?")
    if parsed.who_count:
        # check if any of the targeted objects is a non-living
        if any(not isinstance(who, base.Living) for who in parsed.who_info):
            raise ActionRefused("You can't wait for something that's not alive.")
        if parsed.who_1 is player:
            player.tell("You wait for yourself to figure out what you just meant to do.")
        else:
            who = lang.join(who.title for who in parsed.who_info)
            player.tell("You wait for %s." % who)
            player.tell_others("{Actor} waits for %s." % who)
        return
    if parsed.args:
        if parsed.args[0] in ("till", "until"):
            # wait until an absolute time on the clock
            wait_time = util.parse_time(parsed.args[1:])
            now_dt = ctx.clock.clock
            wait_dt = datetime.datetime.combine(now_dt.date(), wait_time)
            if wait_dt == now_dt:
                raise ActionRefused("It is already that time.")
            if wait_dt < now_dt:
                wait_dt += datetime.timedelta(hours=24)
            duration = wait_dt - now_dt
        else:
            # wait a given duration
            duration = util.parse_duration(parsed.args)
    else:
        duration = datetime.timedelta(minutes=10)
    max_wait_hours = ctx.config.max_wait_hours
    if max_wait_hours == 0:
        raise ActionRefused("It is not possible to wait.")
    if duration.total_seconds() / 3600 > max_wait_hours:
        msg = lang.spell_number(max_wait_hours) + " " + lang.pluralize("hour", max_wait_hours)
        raise ActionRefused("You can't wait more than " + msg + " at once, who knows what might happen in that time?")
    ok, message = ctx.driver.do_wait(duration)
    if ok:
        player.tell("Time passes. You've waited %s." % util.duration_display(duration))
    else:
        player.tell(message)


@cmd("quit", "leave")
@disable_notify_action
def do_quit(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Quit the game."""
    if (yield "input", ("Are you sure you want to quit?", lang.yesno)):
        if ctx.config.server_mode != GameMode.MUD and ctx.config.savegames_enabled:
            if (yield "input", ("Would you like to save your progress?", lang.yesno)):
                yield from do_save(player, parsed, ctx)
        player.tell("\n")
        raise SessionExit()
    player.tell("Good, thank you for staying.")


def print_item_removal(player: Player, item: base.Item, container: base.MudObject, print_parentheses: bool=True) -> None:
    if print_parentheses:
        player.tell("<dim>(You take the %s from the %s).</>" % (item.name, container.name))
    else:
        player.tell("You take the %s from the %s." % (item.name, container.name))
    player.tell_others("{Actor} takes the %s from the %s." % (item.name, container.name))


def remove_is_are_args(args: List[str]) -> None:
    if args:
        if args[0] == "are":
            raise ActionRefused("Be more specific.")
        elif args[0] == "is":
            if len(args) >= 2:
                del args[0]   # skip 'is', but only if more args follow
            else:
                raise ActionRefused("Who do you mean?")


@cmd("who")
@disable_notify_action
def do_who(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Search for all players, a specific player or creature, and shows some information about them."""
    if parsed.args == ["am", "i"]:
        # who am i
        raise RetryParse("examine myself")      # 'who am i' -> 'examine myself')
    if ctx.config.server_mode == GameMode.IF:
        # in interactive fiction mode, revert to a simple substitute (examine)
        return do_examine(player, parsed, ctx)
    if parsed.args:
        remove_is_are_args(parsed.args)
        name = parsed.args[0].rstrip("?")
        found = False
        otherplayer = ctx.driver.search_player(name)  # global player search
        if otherplayer:
            found = True
            player.tell("%s is playing, %s is currently in '<location>%s</>'." %
                        (lang.capital(otherplayer.title), otherplayer.subjective, otherplayer.location.name))
        try:
            do_examine(player, parsed, ctx)
        except ActionRefused:
            pass
        if not found:
            player.tell("Right now, there's nobody here or playing with that name.")
    else:
        # print all players
        player.tell("All players currently in the game:", end=True)
        player.tell("\n")
        for conn in ctx.driver.all_players.values():
            other = conn.player
            player.tell("%s (%s): currently in <location>%s</>." %
                        (lang.capital(other.name), other.title, other.location.name), end=True)


@cmd("open", "close", "lock", "unlock")
def do_open(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Do something with a door, exit or item, possibly by using something. Example: open door,  unlock chest with key"""
    if len(parsed.args) not in (1, 2) or parsed.unrecognized:
        raise ParseError("%s what? With what?" % lang.capital(parsed.verb))
    if parsed.who_count:
        if isinstance(parsed.who_1, base.Living):
            raise ActionRefused("You can't do that with %s." % parsed.who_1.title)
    what_name = parsed.args[0]
    with_item_name = None
    with_item = None
    what = None   # type: Optional[base.MudObject]
    if len(parsed.args) == 2:
        with_item_name = parsed.args[1]
    what = player.search_item(what_name, include_inventory=True, include_location=True, include_containers_in_inventory=False)
    if not what:
        if what_name in player.location.exits:
            what = player.location.exits[what_name]
    if what:
        if with_item_name:
            with_item = player.search_item(with_item_name,
                                           include_inventory=True, include_location=False, include_containers_in_inventory=False)
            if not with_item:
                raise ActionRefused("You don't have %s." % lang.a(with_item_name))
        getattr(what, parsed.verb)(player, with_item)
        # no need to tell the player or the room, because the verb handler already did this
    else:
        raise ActionRefused("You don't see %s." % lang.a(what_name))


@cmd("what")
@disable_notify_action
def do_what(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Tries to answer your question about what something is.
    The topics range from game commands to location exits to creature and items.
    For more general help, try the 'help' command first."""
    p = player.tell
    if not parsed.args:
        raise ParseError("What do you mean?")
    if parsed.args[0] == "are" and len(parsed.args) > 2:
        raise ActionRefused("Be more specific.")
    if len(parsed.args) >= 2 and parsed.args[0] in ("is", "are"):
        del parsed.args[0]
    name = parsed.args[0].rstrip("?")
    if not name:
        raise ActionRefused("What do you mean?")
    found = False
    # is it an abbreviation?
    if name in abbreviations:
        name = abbreviations[name]
        p("It's an abbreviation for %s." % name)
    # is it a command?
    all_verbs = ctx.driver.current_verbs(player)
    if name in all_verbs:
        found = True
        doc = all_verbs[name].strip()
        if doc:
            p(doc)
        else:
            p("It is a command that you can use to perform some action.")
    # is it a soul verb?
    if name in VERBS:
        found = True
        try:
            parsed = base.ParseResult(name)
            playermessage, roommessage = player.soul.process_verb_parsed(player, parsed)[1:3]
        except ParseError:
            # try again with a person
            parsed = base.ParseResult(name, who_list=[player])
            playermessage, roommessage = player.soul.process_verb_parsed(player, parsed)[1:3]
        p("It is a soul emote you can do. <dim>%s: %s</>" % (name, playermessage))
        if name in AGGRESSIVE_VERBS:
            p("It might be regarded as offensive to certain people or beings.")
    if name in BODY_PARTS:
        found = True
        parsed = base.ParseResult("pat", who_list=[player], bodypart=name, message="hi")
        playermessage, roommessage = player.soul.process_verb_parsed(player, parsed)[1:3]
        p("It denotes a body part. <dim>pat myself %s -> %s</>" % (name, playermessage))
    if name in ACTION_QUALIFIERS:
        found = True
        parsed = base.ParseResult("smile", qualifier=name)
        playermessage, roommessage = player.soul.process_verb_parsed(player, parsed)[1:3]
        p("It is a qualifier for something. <dim>%s smile -> %s</>" % (name, playermessage))
    if name in lang.ADVERBS:
        found = True
        parsed = base.ParseResult("smile", adverb=name)
        playermessage, roommessage = player.soul.process_verb_parsed(player, parsed)[1:3]
        p("That's an adverb you can use with the soul emote commands.")
        p("<dim>smile %s -> %s</>" % (name, playermessage))
    if name in races.races:
        found = True
        race = races.races[name]
        size_msg = race.size.text
        body_msg = race.body.value
        lang_msg = race.language
        p("That's a race. They're %s, their body type is %s, and they usually speak %s." % (size_msg, body_msg, lang_msg))
    # is it an exit in the current room?
    if name in player.location.exits:
        found = True
        p("It's a possible way to leave your current location: %s" % player.location.exits[name].short_description)
    # is it a npc here?
    living = player.location.search_living(name)
    if living:
        found = True
        if living is player:
            p("That's you.")
        else:
            title = lang.capital(living.title)
            gender = lang.GENDERS[living.gender]
            subj = lang.capital(living.subjective)
            if isinstance(living, Player):
                p("%s is a %s %s (player). %s's here." % (title, gender, living.stats.race or "creature", subj))
            else:
                p("%s is a %s %s. %s's here." % (title, gender, living.stats.race or "creature", subj))
    # is it an item somewhere?
    item, container = player.locate_item(name, include_inventory=True, include_location=True, include_containers_in_inventory=True)
    if item:
        found = True
        p("It's an item in your vicinity or perhaps even in your pockets. You should maybe try to examine it.")
    if name == "soul":
        # if player is asking about the soul, give some general info
        found = True
        p("Your soul provides a large amount of 'emotes' or 'verbs' that you can perform.")
        p("An emote is a command that you can do to perform something, or tell something.")
        p("They usually are just for socialization or fun and are not normally considered")
        p("considered to be a command to actually do something or interact with things.")
        p("Your soul knows %d emotes. See them all by asking about 'emotes'." % len(VERBS))
        p("Your soul knows %d adverbs. You can use them by their full name, or make" % len(lang.ADVERBS))
        p("a selection by using prefixes (sa/sar/sarcas -> sarcastically).")
        p("\n")
        p("There are all sorts of emote possibilities, for instance:")
        p("\n")
        p("  fail sit zen  ->  You try to sit zen-likely, but fail miserably.", end=True)
        p("  pat max on the back  ->  You pat Max on the back.", end=True)
        p("  reply max sure thing  ->  You reply to Max: sure thing.", end=True)
        p("  die  ->  You fall down and play dead. (others see: XYZ falls, dead.)", end=True)
        p("  slap all  ->  You slap X, Y and Z in the face.", end=True)
        p("  slap all and me  ->  You slap yourself, X, Y and Z in the face.", end=True)
        p("Often you can target a specific bodypart (try 'what is bodyparts' or ?bodyparts).")
        p("It's sometimes also possible to qualify your action to make it mean something else, such as fail ... or pretend...")
        p("(try 'what are qualifiers' or ?qualifiers).", end=True)
    if name == "emotes":
        # if player asks about the emotes, print all soul emote verbs
        found = True
        p("All available soul verbs (emotes):")
        p("\n")
        columns = player.screen_width // 15
        lines = [""] * (len(VERBS) // columns + 1)
        index = 0
        for verb in sorted(VERBS):
            lines[index % len(lines)] += "%-15s" % verb
            index += 1
        p("\n".join(lines), format=False)
    if name in ("adverb", "adverbs"):
        found = True
        p("You can use adverbs such as 'happily', 'zen', 'aggressively' with soul emotes.")
        p("Your soul knows %d adverbs. You can use them by their full name, or make" % len(lang.ADVERBS))
        p("a selection by using prefixes (sa/sar/sarcas -> sarcastically).")
    if name in ("bodypart", "bodyparts"):
        found = True
        p("You can sometimes use a specific body part with certain soul emotes.")
        p("For instance, 'hit max knee' -> You hit Max on the knee.")
        p("Recognised body parts: " + ", ".join(BODY_PARTS))
    if name in ("qualifier", "qualifiers"):
        found = True
        p("You can use an action qualifier to change the meaning of a soul emote.")
        p("For instance, 'fail stand' -> You try to stand up, but fail miserably.")
        p("Recognised qualifiers: " + ", ".join(ACTION_QUALIFIERS))
    if name in ("that", "this", "they", "them", "it"):
        raise ActionRefused("Be more specific.")
    if not found:
        # too bad, no help available
        p("Sorry, there is no information available about that.")
        if "wizard" in player.privileges:
            p("Maybe you meant to type a wizard command like '!%s'?" % name)


@cmd("where")
@disable_notify_action
def do_where(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Gives some information on your current whereabouts, or that of something else perhaps. Similar to 'locate'."""
    if not parsed.args:
        raise ParseError("Where is what or who?")
    if len(parsed.args) == 2 and parsed.args[0] == "am":
        if parsed.args[1].rstrip("?") in ("i", "I"):
            player.tell("You're in %s." % player.location.title)
            player.tell("Perhaps you want to look around to get your bearings?")
            return
    if parsed.args[0] in ("is", "are") and len(parsed.args) > 2:
        raise ActionRefused("Be more specific.")
    if len(parsed.args) >= 2 and parsed.args[0] in ("is", "are"):
        del parsed.args[0]
    name = parsed.args[0].rstrip("?")
    raise RetryParse("locate " + name)


@cmd("exits")
@disable_notify_action
def do_exits(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Provides a tiny clue about possible exits from your current location."""
    if "wizard" in player.privileges:
        player.tell("The following exits are defined for your current location:", end=True)
        for direction, exit in player.location.exits.items():
            if exit.target:
                player.tell("%s <dim>--></> <location>%s</>" % (direction, exit.target.name), end=True)
            else:
                player.tell("%s <dim>--></> (unbound)" % direction, end=True)
    else:
        player.tell("If you want to know about the possible exits from your location,")
        player.tell("look around the room. Usually the exits are easily visible.")
        if len(player.location.exits) == 1:
            player.tell("Your current location seems to have a possible exit.")
        elif len(player.location.exits) > 1:
            player.tell("Your current location seems to have some possible exits.")
        else:
            player.tell("Your current location doesn't seem to have any obvious exits.")


@cmd("use")
def do_use(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """General object use. Most of the time, you'll need to be more specific to say exactly what you want to do with it."""
    if not parsed.who_count:
        raise ActionRefused("Use what?")
    if parsed.who_count > 1:
        # check if there are exactly 2 items mentioned that the player is carrying, assume 'combine' in that case
        if parsed.who_count == 2:
            item1, item2 = tuple(parsed.who_info)
            if item1 in player and item2 in player:
                player.tell("<dim>(It is assumed that you want to combine them.)</>")
                return do_combine_two(player, parsed, ctx)
        subj = "them"
    else:
        who = parsed.who_1
        if isinstance(who, base.Living):
            if who is player:
                raise ActionRefused("Please be more specific: what do you want to do?")
            subj = who.objective
        else:
            subj = "it"
    raise ActionRefused("Please be more specific: what do you want to do with %s?" % subj)


@cmd("dice", "roll")
def do_dice(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Roll a 6-sided die. Use the familiar '3d6' argument style if you want to roll multiple dice."""
    if not parsed.args:
        if parsed.verb == "roll":
            raise RetrySoulVerb
        number = 1
        sides = 6
    else:
        try:
            if 'd' in parsed.args[0]:
                n, _, s = parsed.args[0].partition("d")
                number, sides = int(n), int(s)
            else:
                if parsed.args[0] == 'a':
                    number = 1
                else:
                    number = int(parsed.args[0])
                sides = 6
        except ValueError:
            raise ActionRefused("What kind of dice do you want to roll (such as 3d6)?")
    if not (1 <= number <= 20 and sides >= 2):
        raise ActionRefused("Please try a bit more sensible values.")
    total, values = util.roll_dice(number, sides)
    die = "a die"
    if (number, sides) != (1, 6):
        die = "%dd%d" % (number, sides)
    player.tell("You roll %s. The result is: %d." % (die, total), evoke=True, max_length=True)
    player.tell_others("{Actor} rolls %s. The result is: %d." % (die, total), evoke=True, max_length=True)
    if number > 1:
        player.location.tell("The individual rolls were: %s" % values, evoke=True, max_length=True)


@cmd("coin")
def do_coin(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Toss a coin."""
    number, _ = util.roll_dice(sides=2)
    result = ["heads", "tails"][number - 1]
    player.tell("You toss a coin. The result is: %s!" % result, evoke=True, max_length=True)
    player.tell_others("{Actor} tosses a coin. The result is: %s!" % result, evoke=True, max_length=True)


@cmd("motd")
@disable_notify_action
@disabled_in_gamemode(GameMode.IF)
def do_motd(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Show the message-of-the-day again."""
    ctx.driver.show_motd(player, notify_no_motd=True)


@cmd("flee", "run", "evade")
def do_flee(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Flee/run in a random or given direction, possibly escaping a combat situation, or shaking off pursuers."""
    exit = None
    if parsed.who_count == 1:
        exit = parsed.who_1
        if not isinstance(exit, base.Exit):
            raise ParseError("You can't flee there.")
        exit.allow_passage(player)
    elif parsed.args:
        if parsed.args[0] != "away":
            raise ParseError("Flee where?")
    random_direction = not exit
    if random_direction:
        # choose a random exit direction
        if not player.location.exits:
            raise ActionRefused("You can't run anywhere!")
        exit = random.choice(list(player.location.exits.values()))
    exits_to_try = list(player.location.exits.values())
    if isinstance(exit, base.Exit):
        exits_to_try.insert(0, exit)
    for exit in exits_to_try:
        try:
            exit.allow_passage(player)
            player.tell("You run away in a random direction!" if random_direction else "You run away!", end=True, evoke=True, max_length=True)
            player.tell("\n")
            # @todo stop combat
            for liv in player.location.livings:
                if liv.following is player:
                    liv.following = None   # stop followers
            player.move(exit.target)
            player.look()
            return
        except ActionRefused:
            pass
    raise ActionRefused("You can't flee anywhere!")


@cmd("save")
@disable_notify_action
@disabled_in_gamemode(GameMode.MUD)
def do_save(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Save your game."""
    if not ctx.driver.do_check_savefile_free(player):
        if not (yield "input", ("Are you sure you want to overwrite the previous save game?", lang.yesno)):
            player.tell("Ok, not saved.")
            return
    ctx.driver.do_save(player)


@cmd("load", "reload", "restore", "restart")
@disable_notify_action
@disabled_in_gamemode(GameMode.MUD)
def do_load(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Load a previously saved game."""
    if ctx.config.savegames_enabled:
        player.tell("If you want to restart or reload a previously saved game, please quit the game (without saving!) "
                    "and start it again. During startup, select the appropriate option to start from a saved game, "
                    "or start a new game.")
    else:
        player.tell("It is not possible to save or restore your progress.")


@cmd("transcript")
@disable_notify_action
@disabled_in_gamemode(GameMode.MUD)
def do_transcript(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Makes a transcript of your game session to the specified file, or switches transcript off again."""
    if parsed.unparsed == "off" or (parsed.args and parsed.args[0] == "off"):
        player.deactivate_transcript()
    elif not parsed.args:
        raise ParseError("Transcript to what file? (or off)")
    else:
        player.activate_transcript(parsed.args[0], ctx.driver.user_resources)


@cmd("show")
def do_show(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Shows something to someone else."""
    if parsed.who_count != 2:
        raise ParseError("Show what to whom?")
    shown, target = parsed.who_12
    if shown not in player:
        raise ActionRefused("You don't have %s." % lang.a(shown.title))
    if target is player:
        player.tell("You show the %s to yourself. Well, that was interesting." % shown.title, evoke=True, max_length=True)
    else:
        player.tell("You show the %s to %s." % (shown.title, target.title), evoke=True, max_length=True)
    room_msg = "%s shows %s to %s." % (lang.capital(player.title), lang.a(shown.title), target.title)
    target_msg = "%s shows you %s." % (lang.capital(player.title), lang.a(shown.title))
    player.location.tell(room_msg, exclude_living=player, specific_target_msg=target_msg, specific_targets={target}, evoke=True, max_length=True)


@cmd("time", "date")
@disable_notify_action
def do_time(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Query the current date and/or time of day."""
    if "wizard" in player.privileges:
        real_time = datetime.datetime.now()
        real_time = real_time.replace(microsecond=0)
        player.tell("The game time is: %s" % ctx.clock)
        player.tell("\n")
        player.tell("Real time is: %s" % real_time)
        return
    if ctx.config.display_gametime:
        for item in player.inventory:
            if isinstance(item, GameClock):
                player.tell("You glance at your %s." % item.name)
                player.tell(item.description)
                return
        raise ActionRefused("You don't have a watch, so you're unsure what %s it is." % parsed.verb)
    raise ActionRefused("You have no idea what %s it is." % parsed.verb)


@cmd("brief")
@disable_notify_action
def do_brief(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Configure the verbosity of location descriptions. 'brief' mode means: show short description
    for locations that you've already visited at least once.
    'brief all' means: show short descriptions for all locations even if you've not been there before.
    'brief off': disable brief mode, always show long descriptions.
    'brief reset': disable brief mode and forget about the known locations as well.
    Note that when you explicitly use the 'look' or 'examine' commands, the brief setting is ignored.
    """
    if parsed.unparsed == "off" or (parsed.args and parsed.args[0] == "off"):
        player.brief = 0
        player.tell("Verbose location descriptions restored.")
    elif not parsed.args:
        player.brief = 1
        player.tell("Brief location descriptions enabled for known locations.")
    elif parsed.args[0] == "all":
        player.brief = 2
        player.tell("Brief location descriptions enabled for all locations.")
    elif parsed.args[0] == "reset":
        player.brief = 0
        count = len(player.known_locations)
        player.known_locations.clear()
        player.tell("Verbose location descriptions have been restored, and you've forgotten about %d previously visited locations." % count)
    else:
        raise ParseError("That's not recognised by this command.")


@cmd("activate")
def do_activate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Activate something, turn it on, or switch it on."""
    if not parsed.who_count:
        raise ParseError("Activate what?")
    for what in parsed.who_info:
        try:
            what.activate(player)
        except ActionRefused as ex:
            msg = str(ex)
            if parsed.who_count > 1:
                player.tell("%s: %s" % (what.name, msg), evoke=True, max_length=True)
            else:
                player.tell(msg, evoke=True, max_length=True)


@cmd("deactivate")
def do_deactivate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Deactivate something, turn it of, or switch it off."""
    if not parsed.who_count:
        raise ParseError("Deactivate what?")
    for what in parsed.who_info:
        try:
            what.deactivate(player)
        except ActionRefused as ex:
            msg = str(ex)
            if parsed.who_count > 1:
                player.tell("%s: %s" % (what.name, msg), evoke=True, max_length=True)
            else:
                player.tell(msg, evoke=True, max_length=True)


@cmd("switch")
def do_switch(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Switch something on or off."""
    if parsed.who_count == 1:
        who = parsed.who_1
        if parsed.who_info[who].previous_word == "on" or parsed.unparsed.endswith(" on"):
            do_activate(player, parsed, ctx)
            return
        elif parsed.who_info[who].previous_word == "off" or parsed.unparsed.endswith(" off"):
            do_deactivate(player, parsed, ctx)
            return
    elif parsed.who_count == 0:
        arg = parsed.unparsed.partition(" ")[0]
        if arg in ("on", "off"):
            raise ParseError("Switch %s what?" % arg)
    raise RetrySoulVerb


@cmd("turn")
def do_turn(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Turn something (rotate it), or turn something on or off."""
    if parsed.who_count == 1:
        who = parsed.who_1
        if parsed.who_info[who].previous_word == "on" or parsed.unparsed.endswith(" on"):
            do_activate(player, parsed, ctx)
            return
        elif parsed.who_info[who].previous_word == "off" or parsed.unparsed.endswith(" off"):
            do_deactivate(player, parsed, ctx)
            return
    elif parsed.who_count == 0:
        arg = parsed.unparsed.partition(" ")[0]
        if arg in ("on", "off"):
            raise ParseError("Turn %s what?" % arg)
    # "turn X" -> same as rotate, see below
    do_manipulate(player, parsed, ctx)


@cmd("move", "shove", "swivel", "shift", "manipulate", "manip", "rotate", "press", "poke", "push")
def do_manipulate(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Manipulate something."""
    if parsed.verb == "manip":
        parsed.verb = "manipulate"
    if parsed.who_count == 1:
        what = parsed.who_1
        try:
            what.manipulate(parsed.verb, player)
            return
        except ActionRefused:
            if player.soul.is_verb(parsed.verb):
                raise RetrySoulVerb
            raise
    if player.soul.is_verb(parsed.verb):
        raise RetrySoulVerb  # some of these commands are also soul verbs
    raise ParseError("%s what?" % lang.capital(parsed.verb))


@cmd("read")
def do_read(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Read something."""
    if parsed.who_count == 1:
        what = parsed.who_1
        what.read(player)
    else:
        if parsed.args:
            # check if name is in location's or an item's extradesc
            text = player.search_extradesc(parsed.args[0])
            if text:
                player.tell(text)
                return
        raise ParseError("Read what?")


@cmd("license")
def do_license(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Show information about the game and about Tale, and show the software license."""
    t = player.tell
    config = ctx.config
    author_addr = " (%s)" % config.author_address if config.author_address else ""
    t("This game, '<bright>%s</>' v%s," % (config.name, config.version))
    t("is written by <bright>%s%s</>" % (config.author, author_addr))
    t("\n")
    # print optional game specific license info
    if ctx.config.license_file:
        t("\n")
        t(ctx.resources[ctx.config.license_file].text, end=True, format=False)
        t("\n")
    # print LGPL 3.0 banner
    t("<bright>Tale: mud driver, mudlib and interactive fiction framework.", end=True)
    t("Copyright (c) by Irmen de Jong.</>", end=True)
    t("This program comes with ABSOLUTELY NO WARRANTY. This is free software,")
    t("and you are welcome to redistribute it under the terms and conditions")
    t("of the GNU Lesser General Public License version 3, see LICENSE.txt", end=True)
    t("-- -- -- --", end=True)


@cmd("config")
def do_config(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Show or change player configuration parameters."""
    if parsed.args:
        if len(parsed.args) != 1:
            raise ParseError("Configure what? Usage is: config parameter=value")
        param, _, value = parsed.args[0].partition("=")
        if not value:
            raise ParseError("You must provide a value.")
        if param == "delay":
            delay = int(value)
            if 0 <= delay <= 100:
                player.output_line_delay = delay
            else:
                raise ActionRefused("Invalid delay value, range is 0..100")
        elif param == "width":
            width = int(value)
            if 40 <= width <= 200:
                player.screen_width = width
            else:
                raise ActionRefused("Invalid screen width, range is 40..200")
        elif param == "styles":
            player.screen_styles_enabled = value.lower() in ("y", "yes", "true", "enable", "enabled", "on")
        elif param == "smartquotes":
            player.smartquotes_enabled = value.lower() in ("y", "yes", "true", "enable", "enabled", "on")
        elif param == "prompttk":
            player.prompt_toolkit_enabled = value.lower() in ("y", "yes", "true", "enable", "enabled", "on")
        else:
            raise ActionRefused("Invalid parameter name.")
        player.tell("Configuration modified.", end=True)
        player.tell("\n")
    player.tell("Configuration:", end=True)
    player.tell("  delay <dim>(output line delay) =</> %d" % player.output_line_delay, format=False)
    player.tell("  width <dim>(screen width) =</> %d" % player.screen_width, format=False)
    player.tell("  styles <dim>(enable text styles) =</> %s" % player.screen_styles_enabled, format=False)
    player.tell("  smartquotes <dim>(use typographic quotes) =</> %s" % player.smartquotes_enabled, format=False)
    player.tell("  prompttk <dim>(use prompt_toolkit input) =</> %s" % player.prompt_toolkit_enabled, format=False)


@cmd("@cls")
def do_cls(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Clears the screen (if the output device supports it)."""
    ctx.conn.clear_screen()


@cmd("@teststyles")
def do_teststyles(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Test the text output styling."""
    style_tests = [
        ("normal", "This is NORMAL."),
        ("dim", "<dim>This is DIM.</>"),
        ("bright", "<bright>This is BRIGHT.</>"),
        ("ul", "<ul>This is UNDERLINED.</>"),
        ("it", "<it>This is ITALIC.</>"),
        ("rev", "<rev>This is REVERSE VIDEO.</>"),
        ("location", "<location>This is LOCATION.</>"),
        ("(combined)", "<ul><bright>Bright underlined. <rev>(and reverse video even)</>")
    ]
    player.tell("Text style tests. Depending on the capabilities of the output device,")
    player.tell("you should see various text formatting styles being used.")
    player.tell("Note that some styles are not widely supported (italic, underlined).", end=True)
    for style, example in style_tests:
        player.tell("  %s -- %s" % (style, example), end=True)
    player.tell("\n")


@cmd("@change_password")
@disabled_in_gamemode(GameMode.IF)
def do_change_pw(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Lets you change your account password."""
    player.tell("<it>Changing your password.</>")
    current_pw = yield "input-noecho", "Type your current password."
    new_pw = yield "input-noecho", ("Type your new password.", MudAccounts.accept_password)
    try:
        ctx.driver.mud_accounts.change_password_email(player.name, current_pw, new_password=new_pw)
        player.tell("Password updated.")
    except ValueError as x:
        raise ActionRefused("<it>%s</it>" % x)


@cmd("@change_email")
@disabled_in_gamemode(GameMode.IF)
def do_change_email(player: Player, parsed: base.ParseResult, ctx: util.Context) -> Generator:
    """Lets you change the email address on file for your account."""
    account = ctx.driver.mud_accounts.get(player.name)
    player.tell("<it>Changing your email. It is currently set to: %s</>" % account.email)
    current_pw = yield "input-noecho", "Type your current password."
    new_email = yield "input", ("Type your new email address.", MudAccounts.accept_email)
    try:
        ctx.driver.mud_accounts.change_password_email(player.name, current_pw, new_email=new_email)
        player.tell("Email address updated.")
    except ValueError as x:
        raise ActionRefused("<it>%s</it>" % x)


@cmd("@account")
@disabled_in_gamemode(GameMode.IF)
def do_account(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Displays your player account data."""
    account = ctx.driver.mud_accounts.get(player.name)
    player.tell("<ul>Your account data.</ul>", end=True)
    player.tell("name: %s" % account.name, end=True)
    player.tell("email: %s" % account.email, end=True)
    player.tell("privileges: %s" % (lang.join(account.privileges, "") or "-"), end=True)
    gender = lang.GENDERS[account.stats.gender]
    race = account.stats.race or "creature"
    player.tell("character: level %d %s %s" % (account.stats.level, gender, race), end=True)
    days_ago = datetime.datetime.now() - account.created
    player.tell("created: %s (%d days ago)" % (account.created, days_ago.days), end=True)
    player.tell("last login: %s" % account.logged_in, end=True)
    player.tell("\n")

@cmd("load_character")
def do_load_character(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Load a companion character from file."""
    if len(parsed.args) != 1:
        raise ParseError("You need to specify the path to the character file")
    try:
        path = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))

    ctx.driver.load_character(player, path)

@cmd("wield")
def do_wield(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Wield a weapon."""
    if len(parsed.args) != 1:
        raise ParseError("You need to specify the weapon to wield")
    try:
        weapon = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    result = player.locate_item(weapon, include_location=False)
    if not result:
        raise ActionRefused("You don't have that weapon")
    player.wielding = result[0]

@cmd("unwield")
def do_unwield(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Unwield a weapon."""
    player.wielding = None

@cmd("wear")
def do_wear(player: Player, parsed: base.ParseResult, ctx: util.Context) -> None:
    """Wear an item."""
    if len(parsed.args) < 1:
        raise ParseError("You need to specify the item to wear")
    try:
        item = str(parsed.args[0])
    except ValueError as x:
        raise ActionRefused(str(x))
    if len(parsed.args) == 2:
        try:
            parsed_loc = str(parsed.args[1])
            location = WearLocation[parsed_loc.upper()]
        except ValueError:
            raise ActionRefused("Invalid location")
        

    result = player.locate_item(item, include_location=False)
    if not result:
        raise ActionRefused("You don't have that item")
    player.set_wearable(result[0], location=location)