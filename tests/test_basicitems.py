"""
Unit tests for basic items

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import datetime
import unittest

from tale import mud_context
from tale import util, player, base
from tale.errors import ActionRefused, TaleError
from tale.items import basic, board, bank
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver


class TestBasicItems(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = StoryConfig()
        mud_context.resources = mud_context.driver.resources
        self.actor = player.Player("julie", "f")

    def test_gameclock(self):
        mud_context.driver.game_clock = util.GameDateTime(datetime.datetime(2013, 9, 17, 13, 52, 30))
        c = basic.gameclock
        c.use_locale = False
        mud_context.config.display_gametime = False
        c.read(self.actor)
        out = self.actor.test_get_output_paragraphs()[0]
        self.assertEqual("It looks broken.\n", out)
        mud_context.config.display_gametime = True
        c.read(self.actor)
        out = self.actor.test_get_output_paragraphs()[0]
        self.assertEqual("It reads: 2013-09-17 13:52:30\n", out)

    def test_newspaper(self):
        n = basic.newspaper
        n.read(self.actor)
        out = self.actor.test_get_output_paragraphs()[0]
        self.assertTrue(out.startswith("The newspaper reads:"))

    def test_pouch(self):
        p = basic.pouch
        thing = base.Item("thing")
        self.assertEqual(0, p.inventory_size)
        p.insert(thing, self.actor)
        self.assertTrue(thing in p)
        self.assertEqual(1, p.inventory_size)
        p.remove(thing, self.actor)
        self.assertFalse(thing in p)

    def test_trashcan(self):
        t = basic.trashcan
        thing = base.Item("thing")
        with self.assertRaises(ActionRefused):
            t.insert(thing, self.actor)
        t.open(self.actor)
        t.insert(thing, self.actor)
        self.assertTrue(thing in t)
        t.close(self.actor)
        with self.assertRaises(ActionRefused):
            t.remove(thing, self.actor)
        t.open(self.actor)
        t.remove(thing, self.actor)
        self.assertFalse(thing in t)

    def test_make_catapult(self):
        stick = basic.woodenYstick
        elastic = basic.elastic_band
        thing = base.Item("thing")
        self.assertIsNone(stick.combine([thing], self.actor))
        self.assertIsNone(stick.combine([elastic, thing], self.actor))
        catapult = stick.combine([elastic], self.actor)
        self.assertIsInstance(catapult, basic.Catapult)

    def test_money(self):
        with self.assertRaises(ValueError):
            basic.Money("moneyz", 0.0)
        with self.assertRaises(ValueError):
            basic.Money("moneyz", -1.0)
        m = basic.Money("moneyz", 123.45, title="many coinz", short_descr="tremendous amount of moneys")
        self.assertEqual("many coinz", m.title)
        self.assertEqual("Tremendous amount of moneys", m.short_description)
        self.assertEqual("It looks to be about 100 dollars.", m.description)
        self.assertEqual(123.45, m.value)
        m = basic.Money("moneyz", 123.45, title="purse with coins")
        self.assertEqual("purse with coins", m.title)
        self.assertEqual("A purse with coins is lying here.", m.short_description)
        self.assertEqual("It looks to be about 100 dollars.", m.description)
        m = basic.Money("moneyz", 123.45)
        self.assertEqual("small pile of money", m.title)
        self.assertEqual("A small pile of money is lying here.", m.short_description)
        self.assertEqual("It looks to be about 100 dollars.", m.description)
        m = basic.Money("moneyz", 5123)
        self.assertEqual("large heap of money", m.title)
        self.assertEqual("A large heap of money is lying here.", m.short_description)
        self.assertTrue(m.description.startswith("You guess it is, maybe, "))
        m = basic.Money("moneyz", 512345)
        self.assertEqual("enormous mountain of money", m.title)
        self.assertEqual("An enormous mountain of money is lying here.", m.short_description)
        self.assertEqual("It is A LOT of money.", m.description)
        m = basic.Money("moneyz", 999512345)
        self.assertEqual("absolutely colossal mountain of money", m.title)
        self.assertEqual("An absolutely colossal mountain of money is lying here.", m.short_description)
        self.assertEqual("It is A LOT of money.", m.description)
        m = basic.Money("moneyz", 123.45)
        loc = base.Location("loc")
        m.add_to_location(loc, None)
        with self.assertRaises(TaleError):
            m.add_to_location(loc, None)  # cannot add to loc more than once
        self.assertIs(loc, m.location)
        m2 = list(loc.items)[0]
        self.assertIs(m, m2)
        m3 = basic.Money("mmmm", 999.99)
        m3.add_to_location(loc, None)
        m2 = list(loc.items)[0]
        self.assertEqual(1123.44, m2.value)
        # test cast to float
        self.assertEqual(1123.44, float(m2))

    def test_takability(self):
        p = base.Living("living", "m")
        item = base.Item("item")
        self.assertTrue(item.takeable)
        item.move(p, p)
        brd = board.BulletinBoard("board")
        self.assertFalse(brd.takeable)
        with self.assertRaises(ActionRefused) as x:
            brd.move(p, p, verb="frob")
        self.assertEqual("You can't frob board.", str(x.exception))
        bx = basic.Boxlike("box")
        self.assertTrue(bx.takeable)
        bx.move(p, p)
        bnk = bank.Bank("bank")
        self.assertFalse(bnk.takeable)
        with self.assertRaises(ActionRefused) as x:
            bnk.move(p, p, verb="frob")
        self.assertEqual("The bank won't budge.", str(x.exception))
        with self.assertRaises(ActionRefused) as x:
            bnk.allow_item_move(p, verb="frob")
        self.assertEqual("The bank won't budge.", str(x.exception))
        # now flip the flags around
        bnk.takeable = True
        bnk.allow_item_move(p)
        bnk.move(p, p)
        bx.takeable = False
        with self.assertRaises(ActionRefused) as x:
            bx.move(p, p, verb="frob")
        self.assertEqual("You can't frob box.", str(x.exception))
        brd.takeable = True
        brd.move(p, p)
        item.takeable = False
        with self.assertRaises(ActionRefused) as x:
            item.move(p, p, verb="frob")
        self.assertEqual("You can't frob item.", str(x.exception))

    def test_consumable(self):
        p = base.Living("living", "m")
        food = basic.Food("item")
        food.move(p, p)
        food.consume(p)

        drink = basic.Drink("item")
        drink.move(p, p)
        drink.consume(p)

        health = basic.Health("health")
        health.move(p, p)
        health.consume(p)

        not_consumable = base.Item("not_consumable")
        not_consumable.move(p, p)
        with self.assertRaises(ActionRefused) as x:
            not_consumable.consume(p)
        self.assertEqual("You can't consume that.", str(x.exception))

if __name__ == '__main__':
    unittest.main()
