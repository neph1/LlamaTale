"""
Unit tests for util functions

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import datetime
import os
import unittest

from tale import util, mud_context
from tale.base import Item, Container, Location
from tale.errors import ParseError, ActionRefused, TaleError
from tale.player import Player
from tale.story import MoneyType, StoryConfig
from tale.vfs import VirtualFileSystem, VfsError, Resource, is_text
from tests.supportstuff import FakeDriver


class TestUtil(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.resources = mud_context.driver.resources
        mud_context.config = StoryConfig()

    def test_print_location(self):
        p = Player("julie", "f")
        key = Item("key")
        bag = Container("bag")
        room = Location("room")
        bag.insert(key, p)
        p.insert(bag, p)
        room.insert(p, p)
        with self.assertRaises(Exception):
            p.tell_object_location(None, None)
        p.tell_object_location(key, None)
        self.assertEqual(["(It's not clear where key is).\n"], p.test_get_output_paragraphs())
        p.tell_object_location(key, None, print_parentheses=False)
        self.assertEqual(["It's not clear where key is.\n"], p.test_get_output_paragraphs())
        p.tell_object_location(key, bag)
        result = "".join(p.test_get_output_paragraphs())
        self.assertTrue("in bag" in result and "in your inventory" in result)
        p.tell_object_location(key, room)
        self.assertTrue("in your current location" in "".join(p.test_get_output_paragraphs()))
        p.tell_object_location(bag, p)
        self.assertTrue("in your inventory" in "".join(p.test_get_output_paragraphs()))
        p.tell_object_location(p, room)
        self.assertTrue("in your current location" in "".join(p.test_get_output_paragraphs()))

    def test_moneydisplay(self) -> None:
        # fantasy
        mf = util.MoneyFormatter.create_for(MoneyType.FANTASY)
        self.assertEqual("nothing", mf.display(0))
        self.assertEqual("zilch", mf.display(0, zero_msg="zilch"))
        self.assertEqual("nothing", mf.display(0.001))
        self.assertEqual("1 copper", mf.display(0.006))
        self.assertEqual("12 gold, 3 silver, and 2 copper", mf.display(12.324))
        self.assertEqual("12 gold, 3 silver, and 3 copper", mf.display(12.326))
        self.assertEqual("0g/0s/0c", mf.display(0, True))
        self.assertEqual("12g/3s/2c", mf.display(12.324, True))
        self.assertEqual("12g/3s/3c", mf.display(12.326, True))
        # modern
        mf = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.assertEqual("nothing", mf.display(0))
        self.assertEqual("zilch", mf.display(0, zero_msg="zilch"))
        self.assertEqual("nothing", mf.display(0.001))
        self.assertEqual("1 cent", mf.display(0.006))
        self.assertEqual("5 cents", mf.display(0.05))
        self.assertEqual("1 dollar and 1 cent", mf.display(1.01))
        self.assertEqual("123 dollars and 24 cents", mf.display(123.244))
        self.assertEqual("123 dollars and 25 cents", mf.display(123.246))
        self.assertEqual("$ 0.00", mf.display(0, True))
        self.assertEqual("$ 123.24", mf.display(123.244, True))
        self.assertEqual("$ 123.25", mf.display(123.246, True))

    def test_to_float(self):
        with self.assertRaises(ValueError):
            util.MoneyFormatter.create_for("bubblewrap")
        # fantasy
        mf = util.MoneyFormatter.create_for(MoneyType.FANTASY)
        self.assertEqual(0.0, mf.to_float({}))
        self.assertAlmostEqual(0.03, mf.to_float({"copper": 1.0, "coppers": 2.0}), places=4)
        self.assertAlmostEqual(32.56, mf.to_float({"gold": 22.5, "silver": 100.2, "copper": 4}), places=4)
        self.assertAlmostEqual(28.93, mf.to_float("22g/66s/33c"), places=4)
        # modern
        mf = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.assertEqual(0.0, mf.to_float({}))
        self.assertAlmostEqual(0.55, mf.to_float({"cent": 22, "cents": 33}), places=4)
        self.assertAlmostEqual(55.0, mf.to_float({"dollar": 22, "dollars": 33}), places=4)
        self.assertAlmostEqual(5.42, mf.to_float({"dollar": 5, "cent": 42}), places=4)
        self.assertAlmostEqual(3.45, mf.to_float("$3.45"), places=4)
        self.assertAlmostEqual(3.45, mf.to_float("$  3.45"), places=4)

    def test_words_to_money(self) -> None:
        # fantasy
        mf = util.MoneyFormatter.create_for(MoneyType.FANTASY)
        with self.assertRaises(ParseError):
            mf.parse([])
        with self.assertRaises(ParseError):
            mf.parse(["44"])
        with self.assertRaises(ParseError):
            mf.parse(["44g/s"])
        with self.assertRaises(ParseError):
            mf.parse(["gold"])
        self.assertAlmostEqual(45.16, mf.parse(["44", "gold", "5", "silver", "66", "copper"]), places=4)
        self.assertAlmostEqual(45.16, mf.parse(["44g/5s/66c"]), places=4)
        # modern
        mf = util.MoneyFormatter.create_for(MoneyType.MODERN)
        with self.assertRaises(ParseError):
            mf.parse([])
        with self.assertRaises(ParseError):
            mf.parse(["44"])
        with self.assertRaises(ParseError):
            mf.parse(["$xyz"])
        with self.assertRaises(ParseError):
            mf.parse(["dollar"])
        self.assertAlmostEqual(46.15, mf.parse(["44", "dollar", "215", "cent"]), places=4)
        self.assertAlmostEqual(46.15, mf.parse(["$46.15"]), places=4)
        self.assertAlmostEqual(46.15, mf.parse(["$ 46.15"]), places=4)
        self.assertAlmostEqual(46.15, mf.parse(["$", "46.15"]), places=4)

    def test_parse_money_decimals(self) -> None:
        mf = util.MoneyFormatter.create_for(MoneyType.FANTASY)
        self.assertEqual(2.34, mf.parse(["2g/3s/4c"]))
        self.assertEqual(2.0, mf.parse(["2g"]))
        self.assertEqual(2.90, mf.parse(["2.9g"]))
        self.assertEqual(2.98, mf.parse(["2.98g"]))
        self.assertEqual(2.99, mf.parse(["2.987g"]))
        self.assertEqual(2.99, mf.parse(["2.9876g"]))
        self.assertEqual(2.98, mf.parse(["2g/9s/8c"]))
        self.assertEqual(2.98, mf.parse(["2g/9s/8.1c"]))
        self.assertEqual(2.98, mf.parse(["2g/9s/8.123c"]))
        self.assertEqual(2.98, mf.parse(["2", "gold", "9", "silver", "8", "copper"]))
        self.assertEqual(2.99, mf.parse(["2.01", "gold", "9.02", "silver", "8.03", "copper"]))
        self.assertEqual(2.39, mf.parse(["2.01", "gold", "38.3", "copper"]))
        mf = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.assertEqual(23.40, mf.parse(["$ 23.401"]))
        self.assertEqual(23.40, mf.parse(["$ 23.40123"]))
        self.assertEqual(23.41, mf.parse(["$ 23.40567"]))
        self.assertEqual(23.50, mf.parse(["$ 23.49999"]))
        self.assertEqual(23.15, mf.parse(["23", "dollar", "15.0", "cent"]))
        self.assertEqual(23.15, mf.parse(["23", "dollar", "15.2", "cent"]))
        self.assertEqual(23.16, mf.parse(["23", "dollar", "15.5", "cent"]))
        self.assertEqual(23.16, mf.parse(["23", "dollar", "15.999", "cent"]))

    def test_roundoff(self):
        mf = util.MoneyFormatter.create_for(MoneyType.FANTASY)
        self.assertEqual(234.57, mf.roundoff(234.56789))
        mf = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.assertEqual(234.57, mf.roundoff(234.56789))

    def test_roll_dice(self):
        total, values = util.roll_dice()
        self.assertTrue(1 <= total <= 6)
        self.assertEqual(1, len(values))
        self.assertEqual(total, values[0])
        total, values = util.roll_dice(20, 10)   # 20d10
        self.assertEqual(20, len(values))
        with self.assertRaises(AssertionError):
            util.roll_dice(0, 10)
        with self.assertRaises(AssertionError):
            util.roll_dice(400, 10)

    def test_parse_duration(self):
        duration = util.parse_duration(["1", "hour", "1", "minute", "1", "second"])
        self.assertEqual(datetime.timedelta(hours=1, minutes=1, seconds=1), duration)
        duration = util.parse_duration(["3", "hours", "2", "minutes", "5", "seconds"])
        self.assertEqual(datetime.timedelta(hours=3, minutes=2, seconds=5), duration)
        duration = util.parse_duration(["3", "h", "2", "min", "5", "sec"])
        self.assertEqual(datetime.timedelta(hours=3, minutes=2, seconds=5), duration)
        duration = util.parse_duration(["3", "h", "2", "m", "5", "s"])
        self.assertEqual(datetime.timedelta(hours=3, minutes=2, seconds=5), duration)
        duration = util.parse_duration(["3h", "2m", "5s"])
        self.assertEqual(datetime.timedelta(hours=3, minutes=2, seconds=5), duration)
        duration = util.parse_duration(["2.5", "min"])
        self.assertEqual(datetime.timedelta(minutes=2, seconds=30), duration)
        with self.assertRaises(ParseError):
            util.parse_duration(None)
        with self.assertRaises(ParseError):
            util.parse_duration(["1", "2", "3"])
        with self.assertRaises(ParseError):
            util.parse_duration(["1", "apple"])
        with self.assertRaises(ParseError):
            util.parse_duration(["seconds", "2"])

    def test_duration_display(self):
        self.assertEqual("no time at all", util.duration_display(datetime.timedelta(0)))
        self.assertEqual("1 hour, 1 minute, and 1 second", util.duration_display(datetime.timedelta(hours=1, minutes=1, seconds=1)))
        self.assertEqual("2 hours, 3 minutes, and 4 seconds", util.duration_display(datetime.timedelta(hours=2, minutes=3, seconds=4)))
        self.assertEqual("2 minutes", util.duration_display(datetime.timedelta(minutes=2)))
        self.assertEqual("2 minutes and 1 second", util.duration_display(datetime.timedelta(minutes=2, seconds=1)))

    def test_formatdocstring(self):
        d = "hai"
        self.assertEqual("hai", util.format_docstring(d))
        d = """first
        second
        third

        """
        self.assertEqual("first\nsecond\nthird", util.format_docstring(d))
        d = """
        first
          second
            third
        """
        self.assertEqual("first\n  second\n    third", util.format_docstring(d))
        d = """
                    hello
        """
        self.assertEqual("hello", util.format_docstring(d))

    def test_gametime_realtime(self):
        epoch = datetime.datetime(2012, 4, 19, 14, 0, 0)
        gt = util.GameDateTime(epoch)  # realtime=1
        self.assertEqual(1, gt.times_realtime)
        self.assertEqual(epoch, gt.clock)
        # test realtime plus/minus
        gt2 = gt.plus_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertNotEqual(gt2, gt.clock)
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 2, 30), gt2)
        gt2 = gt.minus_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 13, 57, 30), gt2)
        # test realtime add/sub
        gt.add_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 2, 30), gt.clock)
        gt.sub_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(epoch, gt.clock)
        # test gametime add/sub
        gt.add_gametime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 2, 30), gt.clock)
        gt.sub_gametime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(epoch, gt.clock)

    def test_gametime_notrealtime(self):
        epoch = datetime.datetime(2012, 4, 19, 14, 0, 0)
        gt = util.GameDateTime(epoch, times_realtime=5)  # not realtime, 5 times as fast
        self.assertEqual(5, gt.times_realtime)
        self.assertEqual(epoch, gt.clock)
        # test realtime plus/minus (so in game-time, it should be 5 times faster)
        gt2 = gt.plus_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertNotEqual(gt2, gt.clock)
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 12, 30), gt2)
        gt2 = gt.minus_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 13, 47, 30), gt2)
        # test realtime add/sub (so in game-time, it should be 5 times faster)
        gt.add_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 12, 30), gt.clock)
        gt.sub_realtime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(epoch, gt.clock)
        # test gametime add/sub (directly manipulates the -ingame- clock, so no surprises here)
        gt.add_gametime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(datetime.datetime(2012, 4, 19, 14, 2, 30), gt.clock)
        gt.sub_gametime(datetime.timedelta(minutes=2, seconds=30))
        self.assertEqual(epoch, gt.clock)

    def test_parsetime(self):
        self.assertEqual(datetime.time(hour=13, minute=22, second=58), util.parse_time(["13:22:58"]))
        self.assertEqual(datetime.time(hour=13, minute=22, second=58), util.parse_time(["13:22:58"]))
        self.assertEqual(datetime.time(hour=13, minute=22, second=0), util.parse_time(["13:22"]))
        time = util.parse_time(["3", "h", "2", "m", "5", "s"])
        self.assertEqual(datetime.time(hour=3, minute=2, second=5), time)
        self.assertEqual(datetime.time(hour=0), util.parse_time(["midnight"]))
        self.assertEqual(datetime.time(hour=12), util.parse_time(["noon"]))
        util.parse_time(["sunrise"])
        util.parse_time(["sunset"])
        with self.assertRaises(ParseError):
            util.parse_time(None)
        with self.assertRaises(ParseError):
            util.parse_time([])
        with self.assertRaises(ParseError):
            util.parse_time(["some_weird_occasion"])

    def test_context(self):
        ctx = util.Context.from_global(player_connection=42)
        self.assertIs(mud_context.driver, ctx.driver)
        self.assertIs(mud_context.driver.game_clock, ctx.clock)
        self.assertIs(mud_context.config, ctx.config)
        self.assertEqual(42, ctx.conn)

    def test_storyname(self):
        self.assertEqual("name", util.storyname_to_filename("NaMe"))
        self.assertEqual("story_name_dot", util.storyname_to_filename("story name.dot"))
        self.assertEqual("name", util.storyname_to_filename("name\\/*"))
        self.assertEqual("name", util.storyname_to_filename("name'\""))

    def test_authorized(self):
        with self.assertRaises(TaleError):
            @util.authorized("wizard", "god")
            def func_no_actor(args):
                pass

        @util.authorized("wizard", "god")
        def func(args, actor=None):
            pass

        class Actor:
            pass
        actor = Actor()
        actor2 = Actor()
        actor2.privileges = {"nobody"}
        actor3 = Actor()
        actor3.privileges = {"wizard", "noob"}
        with self.assertRaises(ActionRefused):
            func(42)
        with self.assertRaises(ActionRefused):
            func(42, actor=actor)
        with self.assertRaises(ActionRefused):
            func(42, actor=actor2)
        func(42, actor=actor3)

    def test_periodical(self):
        def func(): pass
        util.call_periodically(42)(func)
        initial, low, high = func._tale_periodically
        self.assertEqual(42, low)
        self.assertEqual(42, high)
        self.assertGreater(initial, 0)
        self.assertLess(initial, low)
        util.call_periodically(3, 66)(func)
        initial, low, high = func._tale_periodically
        self.assertEqual(3, low)
        self.assertEqual(66, high)
        self.assertGreater(initial, 0)
        self.assertLess(initial, low)
        class X:
            @util.call_periodically(9,99)
            def method(self): pass
        x = X()
        periodicals = util.get_periodicals(x)
        self.assertEqual(1, len(periodicals))
        periodical = periodicals.popitem()
        self.assertEqual(x.method, periodical[0])
        self.assertEqual(9, periodical[1][1])
        self.assertEqual(99, periodical[1][2])
        self.assertEqual({}, util.get_periodicals(self))
        # test cancelation
        util.call_periodically(0)(func)
        self.assertIsNone(func._tale_periodically)

    def test_sortedby(self):
        a = Item("a", "big A")
        b = Item("b", "micro B")
        c = Item("c", "epic C")
        stuff = [c, b, a]
        self.assertEqual([a, b, c], util.sorted_by_name(stuff))
        self.assertEqual([a, c, b], util.sorted_by_title(stuff))


class TestVfs(unittest.TestCase):
    def test_resource_text(self):
        r = Resource("test", "hello", "text/plain")
        self.assertEqual("hello", r.text)
        self.assertEqual(5, len(r))
        self.assertEqual('o', r[4])
        with self.assertRaises(VfsError):
            _ = r.data
        with self.assertRaises(TypeError):
            Resource("test", b"hello", "text/plain")

    def test_resource_binary(self):
        r = Resource("test", b"hello", "image/jpeg")
        self.assertEqual(b"hello", r.data)
        self.assertEqual(5, len(r))
        self.assertEqual(111, r[4])
        with self.assertRaises(VfsError):
            _ = r.text
        with self.assertRaises(TypeError):
            Resource("test", "hello", "image/jpeg")

    def test_is_text(self):
        self.assertTrue(is_text("text/plain"))
        self.assertTrue(is_text("text/xml"))
        self.assertTrue(is_text("application/xml"))
        self.assertTrue(is_text("application/json"))
        self.assertFalse(is_text(""))
        self.assertFalse(is_text("application/octet-stream"))
        self.assertFalse(is_text("image/jpeg"))

    def test_vfs_load_and_names(self):
        vfs = VirtualFileSystem(root_package="tale")
        with self.assertRaises(VfsError):
            _ = vfs["a\\b"]
        with self.assertRaises(VfsError):
            _ = vfs["/abs/path"]
        with self.assertRaises(IOError):
            _ = vfs["normal/text"]
        with self.assertRaises(IOError):
            _ = vfs["normal/image"]
        vfs = VirtualFileSystem(root_path=".")
        with self.assertRaises(IOError):
            _ = vfs["test_doesnt_exist_999.txt"]
        with self.assertRaises(VfsError):
            _ = VirtualFileSystem(root_path="/@@@does_not_exist.foo@@@")
        with self.assertRaises(VfsError):
            _ = VirtualFileSystem(root_package="non.existing.package.name")
        with self.assertRaises(VfsError):
            _ = VirtualFileSystem(root_package="non_existing_package_name")

    def test_vfs_validate_path(self):
        vfs = VirtualFileSystem(root_path=".")
        vfs.validate_path(".")
        vfs.validate_path("./foo")
        vfs.validate_path("./foo/bar")
        vfs.validate_path(".")
        with self.assertRaises(VfsError):
            vfs.validate_path(r".\wrong\slash")
        with self.assertRaises(VfsError):
            vfs.validate_path(r"/absolute/not/allowed")
        with self.assertRaises(VfsError):
            vfs.validate_path(r"./foo/../../../../../rootescape/notallowed")

    def test_vfs_storage(self):
        with self.assertRaises(ValueError):
            _ = VirtualFileSystem(root_package="os", readonly=False)
        vfs = VirtualFileSystem(root_path=".", readonly=False)
        with self.assertRaises(IOError):
            _ = vfs["test_doesnt_exist_999.txt"]
        vfs["unittest.txt"] = "Test1\nTest2\n"
        rsc = vfs["unittest.txt"]
        self.assertEqual("Test1\nTest2\n", rsc.text)
        self.assertEqual("text/plain", rsc.mimetype)
        self.assertEqual(12, len(rsc))
        self.assertEqual("unittest.txt", rsc.name)
        vfs["unittest.txt"] = "Test1\nTest2\n"
        rsc = vfs["unittest.txt"]
        self.assertEqual("Test1\nTest2\n", rsc.text)
        vfs["unittest.jpg"] = b"imagedata\nblob"
        rsc = vfs["unittest.jpg"]
        self.assertEqual(b"imagedata\nblob", rsc.data)
        self.assertTrue(rsc.mimetype in ("image/jpeg", "image/pjpeg"))
        self.assertEqual(14, len(rsc))
        self.assertEqual("unittest.jpg", rsc.name)
        vfs["unittest.jpg"] = rsc
        del vfs["unittest.txt"]
        del vfs["unittest.jpg"]

    def test_vfs_readonly(self):
        vfs = VirtualFileSystem(root_path=".")
        with self.assertRaises(VfsError):
            vfs.open_write("test.txt")
        with self.assertRaises(VfsError):
            vfs["test.txt"] = "data"

    def test_vfs_write_stream(self):
        vfs = VirtualFileSystem(root_path=".", readonly=False)
        with vfs.open_write("unittest.txt") as f:
            f.write("test write")
        self.assertEqual("test write", vfs["unittest.txt"].text)
        with vfs.open_write("unittest.txt", append=False) as f:
            f.write("overwritten")
        self.assertEqual("overwritten", vfs["unittest.txt"].text)
        with vfs.open_write("unittest.txt", append=True) as f:
            f.write("appended")
        self.assertEqual("overwrittenappended", vfs["unittest.txt"].text)
        del vfs["unittest.txt"]

    def test_vfs_read_files(self):
        vfs = VirtualFileSystem(root_path=".", readonly=True)
        # text file
        resource = vfs["tests/files/test.txt"]
        mtime = os.path.getmtime("tests/files/test.txt")
        self.assertEqual(mtime, resource.mtime)
        self.assertTrue(resource.is_text)
        self.assertEqual("text/plain", resource.mimetype)
        self.assertEqual("€ This is a test text file. This is line 1.\n€ This is a test text file. This is line 2.\n", resource.text[:88])
        lines = resource.text.splitlines()
        self.assertEqual(10, len(lines))
        self.assertEqual(441, len(resource))
        self.assertEqual(441, len(resource.text))
        self.assertEqual("T", resource[2])
        # binary file
        resource = vfs["tests/files/image.png"]
        self.assertEqual("image/png", resource.mimetype)
        self.assertFalse(resource.is_text)
        self.assertEqual(487, len(resource))
        self.assertEqual(487, len(resource.data))
        self.assertEqual(78, resource[2])
        self.assertEqual(b"\x89PNG", resource.data[0:4])
        # text file but without proper suffix, so read as binary
        resource = vfs["tests/files/readme"]
        self.assertEqual("application/octet-stream", resource.mimetype)
        self.assertFalse(resource.is_text)
        self.assertEqual(471, len(resource.data))

    def test_vfs_everythingtext(self):
        vfs = VirtualFileSystem(root_path=".", everythingtext=True)
        # text file
        resource = vfs["tests/files/test.txt"]
        self.assertEqual(441, len(resource.text))
        # text file without proper suffix
        resource2 = vfs["tests/files/readme"]
        self.assertEqual("text/plain", resource2.mimetype)
        self.assertEqual(441, len(resource2.text))
        self.assertEqual(resource.text, resource2.text)
        # binary file, but is read as text
        with self.assertRaises(UnicodeError):
            resource = vfs["tests/files/image.png"]

    def test_vfs_read_compressed(self):
        vfs = VirtualFileSystem(root_path=".", readonly=True)
        uncompressed = vfs["tests/files/test.txt"].text
        resource = vfs["tests/files/test.txt.bz2"]
        self.assertEqual(uncompressed, resource.text)
        resource = vfs["tests/files/test.txt.gz"]
        self.assertEqual(uncompressed, resource.text)
        resource = vfs["tests/files/test.txt.xz"]
        self.assertEqual(uncompressed, resource.text)
        with self.assertRaises(VfsError) as x:
            resource = vfs["tests/files/test.txt.Z"]
        self.assertTrue(str(x.exception).startswith("unsupported compressor"))
        uncompressed = vfs["tests/files/image.png"].data
        resource = vfs["tests/files/image.png.gz"]
        self.assertEqual(uncompressed, resource.data)

    def test_vfs_read_autoselectcompressed(self):
        vfs = VirtualFileSystem(root_path=".", readonly=True)
        resource = vfs["tests/files/compressed.png"]
        self.assertEqual(487, len(resource))
        self.assertEqual("tests/files/compressed.png.gz", resource.name)

    def test_vfs_contents(self):
        vfs = VirtualFileSystem(root_package="tale")
        with self.assertRaises(VfsError):
            vfs.contents()
        vfs = VirtualFileSystem(root_path=".")
        self.assertIn("MANIFEST.in", vfs.contents())
        self.assertIn("make.bat", vfs.contents("docs"))
        with self.assertRaises(FileNotFoundError):
            vfs.contents("@dummy@")


if __name__ == '__main__':
    unittest.main()
