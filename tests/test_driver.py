"""
Unittests for the driver

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import heapq
import os
import unittest
from tale import story

import tale.base
import tale.demo
import tale.driver
import tale.driver_if
import tale.driver_mud
from tale.player import Player, PlayerConnection
import tale.util
from tale.cmds import cmd, wizcmd, disabled_in_gamemode
from tale.story import GameMode, StoryBase
from tests.supportstuff import Thing, FakeDriver


def module_level_func(ctx):
    assert ctx is not None


def module_level_func_without_ctx():
    pass


class TestDriverCreation(unittest.TestCase):
    def testBase(self):
        d = tale.driver.Driver()
        self.assertEqual({}, d.all_players)
        self.assertIsNone(d.story)
        self.assertIsNone(d.zones)
        self.assertIsNone(d.game_clock)
        self.assertIsNone(d.resources)
        self.assertIsNone(d.user_resources)

    def testIF(self):
        d = tale.driver_if.IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        self.assertEqual(GameMode.IF, d.game_mode)
        self.assertEqual(99, d.screen_delay)
        self.assertTrue(d.wizard_override)
        self.assertEqual("web", d.io_type)
        self.assertIsNone(d.story)
        self.assertIsNone(d.zones)
        self.assertIsNone(d.game_clock)
        self.assertIsNone(d.resources)
        self.assertIsNone(d.user_resources)

    def testMud(self):
        d = tale.driver_mud.MudDriver(True)
        self.assertEqual(GameMode.MUD, d.game_mode)
        self.assertTrue(d.restricted)
        self.assertIsNone(d.story)
        self.assertIsNone(d.zones)
        self.assertIsNone(d.game_clock)
        self.assertIsNone(d.resources)
        self.assertIsNone(d.user_resources)


class TestDeferreds(unittest.TestCase):
    def testSortable(self):
        t1 = datetime.datetime(1995, 1, 1)
        t2 = datetime.datetime(1996, 1, 1)
        t3 = datetime.datetime(1997, 1, 1)
        t4 = datetime.datetime(1998, 1, 1)
        t5 = datetime.datetime(1999, 1, 1)
        d1 = tale.driver.Deferred(t5, os.getcwd, None, None)
        d2 = tale.driver.Deferred(t2, os.getcwd, None, None)
        d3 = tale.driver.Deferred(t4, os.getcwd, None, None)
        d4 = tale.driver.Deferred(t1, os.getcwd, None, None)
        d5 = tale.driver.Deferred(t3, os.getcwd, None, None)
        deferreds = sorted([d1, d2, d3, d4, d5])
        dues = [d.due_gametime for d in deferreds]
        self.assertEqual([t1, t2, t3, t4, t5], dues)

    def test_numeric_deferreds(self):
        thing = tale.base.Item("thing")
        driver = tale.driver.Driver()
        now = datetime.datetime.now()
        driver.game_clock = tale.util.GameDateTime(now, 1)
        with self.assertRaises(ValueError):
            driver.defer("blerp", thing.move)
        driver.defer(3601, thing.move)
        deferred = driver.deferreds[0]
        after = deferred.due_gametime - now
        self.assertEqual(3601, after.seconds)

    def test_datetime_deferreds(self):
        thing = tale.base.Item("thing")
        driver = tale.driver.Driver()
        now = datetime.datetime.now()
        driver.game_clock = tale.util.GameDateTime(now, 1)
        due = driver.game_clock.plus_realtime(datetime.timedelta(seconds=3601))
        driver.defer(due, thing.move)
        deferred = driver.deferreds[0]
        after = deferred.due_gametime - now
        self.assertEqual(3601, after.seconds)

    def testHeapq(self):
        t1 = datetime.datetime(1995, 1, 1)
        t2 = datetime.datetime(1996, 1, 1)
        t3 = datetime.datetime(1997, 1, 1)
        t4 = datetime.datetime(1998, 1, 1)
        t5 = datetime.datetime(1999, 1, 1)
        d1 = tale.driver.Deferred(t5, os.getcwd, None, None)
        d2 = tale.driver.Deferred(t2, os.getcwd, None, None)
        d3 = tale.driver.Deferred(t4, os.getcwd, None, None)
        d4 = tale.driver.Deferred(t1, os.getcwd, None, None)
        d5 = tale.driver.Deferred(t3, os.getcwd, None, None)
        heap = [d1, d2, d3, d4, d5]
        heapq.heapify(heap)
        dues = []
        while heap:
            dues.append(heapq.heappop(heap).due_gametime)
        self.assertEqual([t1, t2, t3, t4, t5], dues)

    def testCallable(self):
        def scoped_function():
            pass
        t = Thing()
        due = datetime.datetime.now()
        d = tale.driver.Deferred(due, t.append, [42], None)
        ctx = tale.util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        d(ctx=ctx)
        self.assertEqual([42], t.x)
        d = tale.driver.Deferred(due, module_level_func, [], None)
        d(ctx=ctx)
        d = tale.driver.Deferred(due, module_level_func_without_ctx, [], None)
        d(ctx=ctx)
        with self.assertRaises(ValueError):
            tale.driver.Deferred(due, scoped_function, [], None)
        with self.assertRaises(ValueError):
            d = tale.driver.Deferred(due, lambda a, ctx=None: 1, [42], None)

    def testDue_realtime(self):
        # test due timings where the gameclock == realtime clock
        game_clock = tale.util.GameDateTime(datetime.datetime(2013, 7, 18, 15, 29, 59, 123))
        due = game_clock.plus_realtime(datetime.timedelta(seconds=60))
        d = tale.driver.Deferred(due, os.getcwd, None, None)
        result = d.when_due(game_clock)
        self.assertIsInstance(result, datetime.timedelta)
        self.assertEqual(datetime.timedelta(seconds=60), result)
        result = d.when_due(game_clock, True)   # realtime
        self.assertEqual(datetime.timedelta(seconds=60), result)
        game_clock.add_gametime(datetime.timedelta(seconds=20))   # +20 gametime seconds
        result = d.when_due(game_clock)   # not realtime (game time)
        self.assertEqual(datetime.timedelta(seconds=40), result)
        result = d.when_due(game_clock, True)   # realtime
        self.assertEqual(datetime.timedelta(seconds=40), result)

    def testDue_gametime(self):
        # test due timings where the gameclock == 10 times realtime clock
        game_clock = tale.util.GameDateTime(datetime.datetime(2013, 7, 18, 15, 29, 59, 123), 10)   # 10 times realtime
        due = game_clock.plus_realtime(datetime.timedelta(seconds=60))      # due in (realtime) 60 seconds (600 gametime seconds)
        d = tale.driver.Deferred(due, os.getcwd, None, None)
        result = d.when_due(game_clock)   # not realtime
        self.assertIsInstance(result, datetime.timedelta)
        self.assertEqual(datetime.timedelta(seconds=10 * 60), result)
        result = d.when_due(game_clock, True)   # realtime
        self.assertEqual(datetime.timedelta(seconds=60), result)
        game_clock.add_gametime(datetime.timedelta(seconds=20))   # +20 gametime seconds (=2 realtime seconds)
        result = d.when_due(game_clock)   # not realtime (game time)
        self.assertEqual(datetime.timedelta(seconds=580), result)
        result = d.when_due(game_clock, True)   # realtime
        self.assertEqual(datetime.timedelta(seconds=58), result)

    def testTimevalueRanges(self):
        with self.assertRaises(AssertionError):
            tale.driver.Deferred(1, os.getcwd, None, None)
        tale.driver.Deferred(datetime.datetime.now(), os.getcwd, None, None)
        with self.assertRaises(ValueError):
            tale.driver.Deferred(datetime.datetime.now(), os.getcwd, None, None, periodical=(0.09, 0.09))
        driver = tale.driver.Driver()
        driver.game_clock = tale.util.GameDateTime(datetime.datetime.now())
        driver.defer(0.9, os.getcwd)
        driver.defer(1.0, os.getcwd)
        driver.defer(datetime.datetime.now(), os.getcwd)
        with self.assertRaises(ValueError):
            driver.defer((0.09, 0.01, 0.09), os.getcwd)
        with self.assertRaises(ValueError):
            driver.defer((0.01, 1, 2), os.getcwd)
        with self.assertRaises(ValueError):
            driver.defer((1, 0.02, 0.03), os.getcwd)
        d = driver.defer((1, 2, 3), os.getcwd)
        self.assertEqual("getcwd", d.action)
        self.assertTrue(d.owner.startswith("module:"))
        self.assertEqual((2, 3), d.periodical)

@cmd("test1")
@disabled_in_gamemode(GameMode.IF)
def func1(player, parsed, ctx):
    """docstring1"""
    pass


@cmd("test2")
def func2(player, parsed, ctx):
    """docstring2"""
    pass


@cmd("test3")
def func3(player, parsed, ctx):
    """docstring3"""
    pass


@wizcmd("test1w")
def func4(player, parsed, ctx):
    """docstring4"""
    pass


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.cmds = tale.driver.Commands()
        self.cmds.add("verb1", func1)
        self.cmds.add("verb2", func2)
        self.cmds.add("verb3", func2, "wizard")
        self.cmds.add("verb4", func3, "noob")

    def testCommandsOverrideFail(self):
        with self.assertRaises(LookupError):
            self.cmds.override("verbXYZ", func2)

    def testCommandsOverride(self):
        self.cmds.override("verb4", func2, "noob")

    def testCommandsAdjust(self):
        wiz = self.cmds.get(["wizard"])
        self.assertEqual({"verb1", "verb2", "verb3"}, set(wiz.keys()))
        wiz = self.cmds.get([None])
        self.assertEqual({"verb1", "verb2"}, set(wiz.keys()))
        self.cmds.adjust_available_commands(GameMode.IF)
        wiz = self.cmds.get(["wizard"])
        self.assertEqual({"verb2", "verb3"}, set(wiz.keys()))
        wiz = self.cmds.get([None])
        self.assertEqual({"verb2"}, set(wiz.keys()))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
