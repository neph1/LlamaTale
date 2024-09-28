"""
Shopping and shopkeepers.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)

Shopping related commands will be roughly::

    SHOP/LIST [item type]
        list what the shop has for sale
    INFO/INQUIRE/ASK about [item/number]
        same as "ask [shopkeeper] about [item/number]"
        It will display info about the item on sale, as if you examined it.
    BUY
      > buy sword        (buy the first sword on the list)
      > buy #3           (buy the third item on the list)
    SELL
      > sell sword       (sell the first sword in your inventory)
    VALUE/APPRAISE
        asks shop keeper how much he is willing to pay for an item:
      > value sword      (appraise the first sword in your inventory)

"""

import datetime
import random
from typing import Tuple, Set, Optional

from tale.llm.LivingNpc import LivingNpc

from . import lang
from . import mud_context
from .base import Item, Living, ParseResult
from .errors import ActionRefused, ParseError, RetrySoulVerb
from .items.basic import Trash
from .util import sorted_by_title

banking_money_limit = 15000.0


class ShopBehavior:
    """the data describing the behavior of a particular shop"""
    def __init__(self) -> None:
        self.shopkeeper_vnum = -1   # used for circle data to designate the shopkeeper belonging to this shop
        self.banks_money = False
        self.will_fight = False
        self._buyprofit = 0.3     # price factor when shop buys item
        self._sellprofit = 1.6    # price factor when shop sells item
        self.open_hours = [(9, 17), (18, 22)]
        # items the shop always sells no matter how many are bought (should be in shopkeeper's inventory as well!):
        self.forsale = set()    # type: Set[Item]
        self.msg_playercantafford = "No cash, no goods!"
        self.msg_playercantbuy = "We don't sell that."
        self.msg_playercantsell = "I don't think you have that."
        self.msg_shopboughtitem = "Thank-you very much.  Here are your %s as payment."
        self.msg_shopcantafford = "I can't afford to buy anything, I'm only a poor peddler."
        self.msg_shopdoesnotbuy = "I don't buy that stuff.  Try another shop."
        self.msg_shopsolditem = "Here you go.  That'll be... %s."
        self.action_temper = "smoke"
        self.willbuy = set()   # type: Set[str]
        self.wontdealwith = set()   # type: Set[str]   # @todo implement

    @property
    def buyprofit(self) -> float:
        return self._buyprofit

    @buyprofit.setter
    def buyprofit(self, value: float) -> None:
        assert value <= 1.0
        self._buyprofit = value

    @property
    def sellprofit(self) -> float:
        return self._sellprofit

    @sellprofit.setter
    def sellprofit(self, value: float) -> None:
        assert value >= 1.0
        self._sellprofit = value


class Shopkeeper(LivingNpc):
    def __init__(self, name: str, gender: str, *, title: str = "", descr: str = "", short_descr: str = "", age: int, personality: str, occupation: str = "", race: str = "human", parse_occupation: bool = False) -> None:
        super(Shopkeeper, self).__init__(name=name, gender=gender,
                 title=title, descr=descr, short_descr=short_descr, age=age, personality=personality, occupation=occupation, race=race, parse_occupation=parse_occupation)
        self.privileges.add("shopkeeper")   # allow for some item transfers (buy/sell) that would otherwise be blocked
        self.shop = ShopBehavior()
        self.verbs = {
            "shop": "Go shopping! This shows some information about the shop, and what it has for sale.",
            "list": "Go shopping! This shows some information about the shop, and what it has for sale.",
            "sell": "Sell something you carry with you: sell <name>",
            "buy": "Buy something from the shop: buy <item-for-sale> or buy #<itemnumber> (see list)",
            "purchase": "Buy something from the shop: buy <item-for-sale> or buy #<itemnumber> (see list)",
            "haggle": "Try to haggle.",
            "value": "Ask the shopkeeper about what he or she's willing to pay for an item.",
            "appraise": "Ask the shopkeeper about what he or she's willing to pay for an item",
            "info": "Ask about an item on sale. Name the item or give its list number.",
            "inquire": "Ask about an item on sale. Name the item or give its list number.",
            "ask": "Ask about an item on sale. Name the item or give its list number."      # overrides default 'ask'
        }

    def set_shop(self, shop: ShopBehavior) -> None:
        if any(item not in self for item in shop.forsale):
            raise ValueError("not all items from shop.forsale are in the shopkeeper's inventory")
        self.shop = shop
        if self.shop.banks_money:
            self.money = min(self.money, banking_money_limit)   # make sure we don't have surplus cash

    def validate_open_hours(self, actor: Living=None, current_time: datetime.time=None) -> None:
        if actor and "wizard" in actor.privileges:
            return   # for wizards, shops are always open
        if current_time is None:
            current_time = mud_context.driver.game_clock.clock.time()
        assert isinstance(current_time, datetime.time)
        for from_hr, to_hr in self.shop.open_hours:
            from_t = datetime.time(from_hr)
            to_t = datetime.time(to_hr)
            if from_hr < to_hr:
                if from_t <= current_time < to_t:  # normal order such as 9..17
                    return  # we're open!
            else:
                if from_t <= current_time or current_time < to_t:  # reversed order, passes midnight, such as 20..3
                    return  # we're open!
        raise ActionRefused("The shop is currently closed! Come back another time, during opening hours.")

    def _parse_item(self, parsed: ParseResult, actor: Living) -> Tuple[Item, str]:
        if parsed.who_count != 1:
            raise ParseError("I don't understand what single item you're talking about.")
        item, info = parsed.who_info.popitem()
        if item not in actor:
            raise ActionRefused(self.shop.msg_playercantsell or "You don't have that.")
        if not isinstance(item, Item):
            raise ActionRefused("You can't sell %s, %s is not trade goods!" % (item.objective, item.subjective))
        designator = info.previous_word or ""
        return item, designator

    def _get_from_list(self, number: int) -> Item:
        shoplist = list(sorted_by_title(self.inventory))
        try:
            return shoplist[number - 1]
        except IndexError:
            raise ActionRefused("That number doesn't appear on the list of items that are for sale.")

    def allow_give_item(self, item: Item, actor: Optional['Living']) -> None:
        """Do we accept given items? Raise ActionRefused if not. Shopkeeper can only be sold items to!"""
        raise ActionRefused("You can't give stuff to %s just like that, try selling it instead." % self.title)

    def handle_verb(self, parsed: ParseResult, actor: Living) -> bool:
        if self.shop.banks_money:
            self.money = min(self.money, banking_money_limit)   # make sure we don't have surplus cash
        self.validate_open_hours(actor)
        if parsed.verb in ("shop", "list"):
            return self.shop_list(parsed, actor)
        elif parsed.verb in ("info", "inquire", "ask"):
            return self.shop_inquire(parsed, actor)
        elif parsed.verb in ("value", "appraise"):
            return self.shop_appraise(parsed, actor)
        elif parsed.verb in ("buy", "purchase"):
            return self.shop_buy(parsed, actor)
        elif parsed.verb == "sell":
            return self.shop_sell(parsed, actor)
        elif parsed.verb == "haggle":
            self.do_socialize("exclaim No haggling", evoke=True)
            return True
        else:
            return False  # unrecognised verb

    def shop_list(self, parsed: ParseResult, actor: Living, brief: bool = False) -> bool:
        if not brief:
            open_hrs = lang.join(["%d to %d" % hours for hours in self.shop.open_hours])
            joined_tell = "%s says: \"Welcome. Our opening hours are: %s" % (lang.capital(self.title), open_hrs)
            if "wizard" in actor.privileges:
                joined_tell += " (but for wizards, we're always open)"
            if self.shop.willbuy:
                joined_tell += ", and we buy " + lang.join(lang.pluralize(word) for word in self.shop.willbuy)
            actor.tell("\"\n", end=True, evoke=True)
        # don't show shop.forsale, it is for the code to know what items have limitless supply
        if self.inventory_size == 0:
            actor.tell("%s apologizes, \"I'm sorry, but our stuff is all gone for the moment. Come back later.\"" %
                       lang.capital(self.subjective), evoke=True)
        else:
            if not brief:
                actor.tell("%s shows you a list of what is in stock at the moment:" % lang.capital(self.subjective), end=True, evoke=True)
            txt = ["<ul>  # <dim>|</><ul>  item                        <dim>|</><ul> price     </>"]
            for i, item in enumerate(sorted_by_title(self.inventory), start=1):
                price = item.value * self.shop.sellprofit
                txt.append("%3d. %-30s  %s" % (i, item.title, mud_context.driver.moneyfmt.display(price)))
            actor.tell( "\n".join(txt), format=False)
        return True

    def shop_inquire(self, parsed: ParseResult, actor: Living) -> bool:
        item = None
        if parsed.who_count == 2:
            # 'ask lucy about clock/#5/5'
            item = parsed.who_12[0]
            if not isinstance(item, Item):
                item = parsed.who_12[1]
                if not isinstance(item, Item):
                    item = None
        elif parsed.who_count == 1:
            # 'ask about clock/#5/5'
            item = parsed.who_1
            if not isinstance(item, Item):
                item = None
        if item:
            # the parser found an item, check if there's one in the shop too with the same name.
            shop_item = Item.search_item(item.name, self.inventory)
            if shop_item:
                item = shop_item
        if not item:
            # no items in the question, try to extract name/number and look in the shop list #
            for word in parsed.unrecognized:
                if word in ("#", "about", "over", "concerning"):
                    continue
                if word.startswith("#"):
                    word = word[1:]
                try:
                    number = int(word)
                    if number <= 0:
                        continue
                except ValueError:
                    # not a number, search by name
                    item = Item.search_item(word, self.inventory)
                    if not item:
                        continue
                else:
                    # got a number in the shop
                    item = self._get_from_list(number)
        if item and isinstance(item, Item):
            # got an item, inquire about it
            if item not in self:
                raise ActionRefused("That is not something from the shop. You can examine the %s as usual." % item.name)
            actor.tell("The shop sells %s." % lang.a(item.title), evoke=True, short_len=True),
            if item.name in item.extra_desc:
                actor.tell(lang.fullstop(item.extra_desc[item.name]))
            elif item.description:
                actor.tell(lang.fullstop(item.description))
            return True
        if parsed.verb == "ask":
            raise RetrySoulVerb
        else:
            raise ParseError("It's unclear what item you want to inquire about.")

    def shop_appraise(self, parsed: ParseResult, actor: Living) -> bool:
        item, designator = self._parse_item(parsed, actor)
        if designator:
            raise ParseError("It's not clear what item you mean.")
        if item.value <= 0:
            actor.tell("%s tells you it's worthless." % lang.capital(self.title), evoke=True, short_len=True)
            return True
        if isinstance(item, Trash) or Item.search_item(item.title, self.shop.forsale):
            actor.tell("%s tells you: \"%s\"" % (lang.capital(self.title), self.shop.msg_shopdoesnotbuy), evoke=True, short_len=True)
            if self.shop.action_temper:
                self.do_socialize("%s %s" % (self.shop.action_temper, actor.name))
            return True
        # @todo charisma bonus/penalty
        price = item.value * self.shop.buyprofit
        value_str = mud_context.driver.moneyfmt.display(price)
        appraise_tell = "%s appraises the %s." % (lang.capital(self.title), item.name)
        appraise_tell += " \"I'll give you %s for it.\"" % value_str
        actor.tell(appraise_tell, evoke=True, short_len=True)
        return True

    def shop_buy(self, parsed: ParseResult, actor: Living) -> bool:
        if len(parsed.args) != 1:    # @todo support amount to buy?
            raise ParseError("I don't understand what you want to buy.")
        item = None
        name = parsed.args[0]
        if name[0] == '#':
            # it's the Nth from the list
            try:
                num = int(name[1:])
                if num <= 0:
                    raise ValueError("num must be 1 or higher")
                item = list(sorted_by_title(self.inventory))[num - 1]
                if Item.search_item(item.title, self.shop.forsale):
                    item = item.clone()  # make a clone and sell that, the forsale items should never run out
            except ValueError:
                raise ParseError("What number on the list do you mean?")
            except IndexError:
                raise ParseError("That number is not on the list.")
        if not item:
            item = Item.search_item(name, self.shop.forsale)
            if item:
                item = item.clone()  # make a clone and sell that, the forsale items should never run out
            else:
                # search inventory
                item = self.search_item(name, include_inventory=True, include_location=False, include_containers_in_inventory=False)
        if not item:
            actor.tell("%s says: \"%s\"" % (lang.capital(self.title), self.shop.msg_playercantbuy))
            return True
        # sell the item to the customer
        # @todo charisma bonus/penalty
        price = item.value * self.shop.sellprofit
        if price > actor.money:
            actor.tell("%s tells you: \"%s\"" % (lang.capital(self.title), self.shop.msg_playercantafford), evoke=True, short_len=True)
            if self.shop.action_temper:
                self.do_socialize("%s %s" % (self.shop.action_temper, actor.name))
            return True
        item.move(actor, self)   # works, because self has 'shopkeeper' privileges
        actor.money -= price
        self.money += price
        assert actor.money >= 0.0
        if self.shop.msg_shopsolditem:
            if "%d" in self.shop.msg_shopsolditem:
                # old-style (circle) message with just a numeric value for the money
                sold_msg = self.shop.msg_shopsolditem % price
            else:
                # new-style (tale) message with a %s placeholder for the money text
                sold_msg = self.shop.msg_shopsolditem % mud_context.driver.moneyfmt.display(price)
            actor.tell("%s says: \"%s\"" % (lang.capital(self.title), sold_msg), evoke=True, short_len=True)
        else:
            actor.tell("You paid %s for it." % mud_context.driver.moneyfmt.display(price), evoke=True, short_len=True)
        actor.tell("You've bought the %s!" % item.name)
        if self.shop.banks_money:
            # shopkeeper puts money over a limit in the bank
            if self.money > banking_money_limit:
                self.tell_others("Swiftly, {actor} puts some excess money away in a secret stash somewhere. "
                                 "You failed to see where it went.")
                self.money = banking_money_limit
        return True

    def shop_sell(self, parsed: ParseResult, actor: Living) -> bool:
        item, designator = self._parse_item(parsed, actor)
        if designator:
            raise ParseError("It's not clear what item you want to sell.")
        if item.value <= 0 or isinstance(item, Trash):
            actor.tell("%s tells you: \"%s\"" % (lang.capital(self.title), self.shop.msg_shopdoesnotbuy))
            if self.shop.action_temper:
                self.do_socialize("%s %s" % (self.shop.action_temper, actor.name))
            return True
        if Item.search_item(item.title, self.shop.forsale):
            # if the item is on the forsale list, don't buy it (we already have an endless supply)
            actor.tell("%s tells you: \"%s\"" % (lang.capital(self.title), self.shop.msg_shopdoesnotbuy))
            return True
        # @todo check wontdealwith
        # @todo check item type
        # check money  # @todo charisma bonus/penalty
        price = item.value * self.shop.buyprofit
        limit = self.money * 0.75   # shopkeeper should not spend more than 75% of his money on a single sale
        if price >= limit:
            actor.tell("%s says: \"%s\"" % (lang.capital(self.title), self.shop.msg_shopcantafford))
            return True
        item.move(self, actor)
        actor.money += price
        self.money -= price
        assert self.money >= 0.0
        actor.tell("You've sold the %s." % item.name)
        if self.shop.msg_shopboughtitem:
            if "%d" in self.shop.msg_shopboughtitem:
                # old-style (circle) message with just a numeric value for the money
                bought_msg = self.shop.msg_shopboughtitem % price
            else:
                # new-style (tale) message with a %s placeholder for the money text
                bought_msg = self.shop.msg_shopboughtitem % mud_context.driver.moneyfmt.display(price)
            actor.tell("%s says: \"%s\"" % (lang.capital(self.title), bought_msg), evoke=True, short_len=True)
        else:
            actor.tell("%s gave you %s for it." % (lang.capital(self.title), mud_context.driver.moneyfmt.display(price)))
        self.do_socialize("thank " + actor.name)
        return True
