"""
Unittests for Mud base objects

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import pathlib
import sys
import tempfile
import time
import unittest
from io import StringIO

import tale
from tale import races, pubsub, mud_context
from tale.accounts import MudAccounts
from tale.base import Location, Exit, Item, Stats, Living, ParseResult
from tale.charbuilder import IFCharacterBuilder, MudCharacterBuilder, ValidRaceValidator, PlayerNaming
from tale.demo.story import Story as DemoStory
from tale.errors import ActionRefused, ParseError, NonSoulVerb
from tale.player import Player, TextBuffer, PlayerConnection
from tale.story import *
from tale.tio.console_io import ConsoleIo
from tale.tio.iobase import IoAdapterBase
from tests.supportstuff import FakeDriver, MsgTraceNPC


class TestPlayer(unittest.TestCase):
    def setUp(self):
        tale.mud_context.driver = FakeDriver()
        tale.mud_context.config = StoryConfig()
        tale.mud_context.config.server_mode = GameMode.IF
        tale.mud_context.resources = tale.mud_context.driver.resources

    def test_init(self):
        player = Player("fritz", "m")
        player.title = "Fritz the great"
        self.assertEqual("fritz", player.name)
        self.assertEqual("Fritz the great", player.title)
        self.assertEqual("", player.description)
        self.assertEqual("human", player.stats.race)
        self.assertEqual("m", player.gender)
        self.assertEqual("m", player.stats.gender)
        self.assertEqual("he", player.subjective)
        self.assertEqual(set(), player.privileges)
        self.assertGreater(player.output_line_delay, 1)
        player.init_gender("f")
        self.assertEqual("f", player.gender)
        self.assertEqual("f", player.stats.gender)
        self.assertEqual("she", player.subjective)

    def test_init_names(self):
        j = Player("julie", "f", race="human", descr="   this is julie    ", short_descr="     short descr of julie    ")
        self.assertEqual("julie", j.name)
        self.assertEqual("Julie", j.title)
        self.assertEqual("this is julie", j.description)
        self.assertEqual("short descr of julie", j.short_description)
        j.init_names("zoe", "great zoe", "   new descr   ", "    new short descr    ")
        self.assertEqual("zoe", j.name)
        self.assertEqual("Great zoe", j.title)
        self.assertEqual("new descr", j.description)
        self.assertEqual("new short descr", j.short_description)
        j.init_names("petra", None, None, None)
        self.assertEqual("petra", j.name)
        self.assertEqual("Petra", j.title)
        self.assertEqual("", j.description)
        self.assertEqual("", j.short_description)

    def test_tell(self) -> None:
        player = Player("fritz", "m")
        player.tell("5")
        self.assertEqual(["5\n"], player.test_get_output_paragraphs())
        player.tell("")
        self.assertEqual([], player.test_get_output_paragraphs())
        player.tell("")
        player.tell("")
        self.assertEqual([], player.test_get_output_paragraphs())
        player.tell("")
        player.tell("line1")
        player.tell("line2")
        player.tell("")
        self.assertEqual(["line1\nline2\n"], player.test_get_output_paragraphs())
        player.tell("", format=False)
        player.tell("line1", format=False)
        player.tell("", format=False)
        player.tell("line2", format=False)
        player.tell("", format=False)
        self.assertEqual(["\nline1\n\nline2\n\n"], player.test_get_output_paragraphs())
        player.tell("\n")
        self.assertEqual(["\n"], player.test_get_output_paragraphs())
        player.tell("line1")
        player.tell("line2")
        player.tell("hello\nnewline")
        player.tell("\n")
        player.tell("ints")
        player.tell("42")
        player.tell("999")
        self.assertEqual(["line1\nline2\nhello\nnewline\n", "ints\n42\n999\n"], player.test_get_output_paragraphs())
        self.assertEqual([], player.test_get_output_paragraphs())
        player.tell("para1", end=False)
        player.tell("para2", end=True)
        player.tell("para3")
        player.tell("\n")
        player.tell("para4")
        player.tell("\n")
        player.tell("para5")
        self.assertEqual(["para1\npara2\n", "para3\n", "para4\n", "para5\n"], player.test_get_output_paragraphs())
        player.tell("   xyz   \n  123", format=False)
        self.assertEqual(["   xyz   \n  123\n"], player.test_get_output_paragraphs())
        player.tell("line1", end=True)
        player.tell("\n")
        player.tell("line2", end=True)
        player.tell("\n")
        player.tell("\n")
        self.assertEqual(["line1\n", "\n", "line2\n", "\n", "\n"], player.test_get_output_paragraphs())
        player.tell("one two three", format=False)
        self.assertEqual(["one two three\n"], player.test_get_output_paragraphs())

    def test_tell_chain(self):
        player = Player("fritz", "m")
        player.tell("hi").tell("there")
        self.assertEqual(["hi\nthere\n"], player.test_get_output_paragraphs())

    def test_tell_emptystring(self):
        player = Player("fritz", "m")
        player.tell("", end=False)
        self.assertEqual([], player.test_get_output_paragraphs())
        player.tell("", end=True)
        self.assertEqual(["\n"], player.test_get_output_paragraphs())
        player.tell("", end=True)
        player.tell("", end=True)
        self.assertEqual(["\n", "\n"], player.test_get_output_paragraphs())

    def test_tell_formats(self):
        player = Player("fritz", "m")
        pc = PlayerConnection(player, ConsoleIo(None))
        player.set_screen_sizes(0, 100)
        player.tell("a b c", format=True)
        player.tell("d e f", format=True)
        self.assertEqual(["a b c\nd e f\n"], player.test_get_output_paragraphs())
        player.tell("a b c", format=True)
        player.tell("d e f", format=True)
        self.assertEqual("a b c d e f\n", pc.get_output())
        player.tell("a b c", format=False)
        player.tell("d e f", format=False)
        self.assertEqual(["a b c\nd e f\n"], player.test_get_output_paragraphs())
        player.tell("a b c", format=False)
        player.tell("d e f", format=False)
        self.assertEqual("a b c\nd e f\n", pc.get_output())
        player.tell("  a  \nb  c  \n  ", format=True)
        player.tell("  d  \ne  f  \n  ", format=False)
        self.assertEqual(["a  \nb  c\n", "  d  \ne  f  \n  \n"], player.test_get_output_paragraphs())
        player.tell("a b c", format=True)
        player.tell("d e f", format=False)
        self.assertEqual("a b c\nd e f\n", pc.get_output())

    def test_tell_formatted(self):
        player = Player("fritz", "m")
        pc = PlayerConnection(player, ConsoleIo(None))
        player.set_screen_sizes(0, 100)
        player.tell("line1")
        player.tell("line2")
        player.tell("\n")
        player.tell("hello\nnewline")
        player.tell("\n")  # paragraph separator
        player.tell("ints")
        player.tell(42)
        player.tell(999)
        self.assertEqual("line1 line2\nhello newline\nints 42 999\n", pc.get_output())
        player.tell("para1", end=False)
        player.tell("para2", end=True)
        player.tell("para3")
        player.tell("\n")
        player.tell("para4")
        player.tell("\n")
        player.tell("para5")
        self.assertEqual("para1 para2\npara3\npara4\npara5\n", pc.get_output())
        player.tell("word " * 30)
        self.assertNotEqual(("word " * 30).strip(), pc.get_output())
        player.tell("word " * 30, format=False)
        self.assertEqual(("word " * 30) + "\n", pc.get_output())  # when format=False output should be unformatted
        player.tell("   xyz   \n  123", format=False)
        self.assertEqual("   xyz   \n  123\n", pc.get_output())
        player.tell("line1", end=True)
        player.tell("\n")
        player.tell("line2", end=True)
        player.tell("\n")
        player.tell("\n")
        self.assertEqual(["line1\n", "\n", "line2\n", "\n", "\n"], player.test_get_output_paragraphs())
        player.tell("line1", end=True)
        player.tell("\n")
        player.tell("line2", end=True)
        player.tell("\n")
        player.tell("\n")
        self.assertEqual("line1\n\nline2\n\n\n", pc.get_output())

    def test_look(self):
        player = Player("fritz", "m")
        attic = Location("Attic", "A dark attic.")
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Limbo]", "The intermediate or transitional place or state. There's only nothingness. "
                                       "Living beings end up here if they're not in a proper location yet.\n"])
                         , player.test_get_output_paragraphs())
        player.move(attic, silent=True)
        player.look(short=True, evoke=False)
        self.assertEqual(["[Attic]\n"], player.test_get_output_paragraphs())
        julie = Living("julie", "f")
        julie.move(attic, silent=True)
        player.look(short=True, evoke=False)
        self.assertEqual(self._concat_list(["[Attic]", "Present here: julie\n"]), player.test_get_output_paragraphs())

    def test_look_brief(self):
        player = Player("fritz", "m")
        attic = Location("Attic", "A dark attic.")
        cellar = Location("Cellar", "A gloomy cellar.")
        julie = Living("julie", "f")
        julie.move(attic, silent=True)
        player.move(attic, silent=True)
        player.brief = 0  # default setting: always long descriptions
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Attic]", "A dark attic.", "Julie is here.\n"]), player.test_get_output_paragraphs())
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Attic]", "A dark attic.", "Julie is here.\n"]), player.test_get_output_paragraphs())
        player.look(short=True, evoke=False)   # override
        self.assertEqual(self._concat_list(["[Attic]", "Present here: julie\n"]), player.test_get_output_paragraphs())
        player.brief = 1  # short for known, long for new locations
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Attic]", "Present here: julie\n"]), player.test_get_output_paragraphs())
        player.move(cellar, silent=True)
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Cellar]", "A gloomy cellar.\n"]), player.test_get_output_paragraphs())
        player.look(evoke=False)
        self.assertEqual(["[Cellar]\n"], player.test_get_output_paragraphs())
        player.brief = 2  # short always
        player.known_locations.clear()
        player.look(evoke=False)
        self.assertEqual(["[Cellar]\n"], player.test_get_output_paragraphs())
        player.move(attic, silent=True)
        player.look(evoke=False)
        self.assertEqual(self._concat_list(["[Attic]", "Present here: julie\n"]), player.test_get_output_paragraphs())
        player.look(short=True, evoke=False)   # override
        self.assertEqual(self._concat_list(["[Attic]", "Present here: julie\n"]), player.test_get_output_paragraphs())
        player.look(short=False, evoke=False)  # override
        self.assertEqual(self._concat_list(["[Attic]", "A dark attic.", "Julie is here.\n"]), player.test_get_output_paragraphs())

    def _concat_list(self, input):
        return [', '.join(input)]

    def test_others(self):
        attic = Location("Attic", "A dark attic.")
        player = Player("merlin", "m")
        player.title = "wizard Merlin"
        julie = MsgTraceNPC("julie", "f", race="human")
        fritz = MsgTraceNPC("fritz", "m", race="human")
        julie.move(attic, silent=True)
        fritz.move(attic, silent=True)
        player.move(attic, silent=True)
        player.tell_others("one two three")
        self.assertEqual([], player.test_get_output_paragraphs())
        self.assertEqual(["one two three"], fritz.messages)
        self.assertEqual(["one two three"], julie.messages)
        fritz.clearmessages()
        julie.clearmessages()
        player.tell_others("{actor} and {Actor}", evoke=False)
        self.assertEqual(["wizard Merlin and Wizard Merlin"], fritz.messages)

    def test_wiretap(self):
        attic = Location("Attic", "A dark attic.")
        player = Player("fritz", "m")
        io = ConsoleIo(None)
        io.supports_smartquotes = False
        pc = PlayerConnection(player, io)
        player.set_screen_sizes(0, 100)
        julie = Living("julie", "f")
        julie.move(attic)
        player.move(attic)
        julie.tell("message for julie", evoke=False)
        attic.tell("message for room", evoke=False)
        self.assertEqual(["message for room\n"], player.test_get_output_paragraphs())
        with self.assertRaises(ActionRefused):
            player.create_wiretap(julie)
        player.privileges = {"wizard"}
        player.create_wiretap(julie)
        player.create_wiretap(attic)
        julie.tell("message for julie", evoke=False)
        attic.tell("message for room", evoke=False)
        pubsub.sync()
        output = pc.get_output()
        self.assertTrue("[wiretapped from `Attic': message for room]" in output)
        self.assertTrue("[wiretapped from `julie': message for julie]" in output)
        self.assertTrue("[wiretapped from `julie': message for room]" in output)
        self.assertTrue("message for room " in output)
        # test removing the wiretaps
        player.clear_wiretaps()
        import gc
        gc.collect()
        julie.tell("message for julie", evoke=False)
        attic.tell("message for room", evoke=False)
        self.assertEqual(["message for room\n"], player.test_get_output_paragraphs())

    def test_socialize(self):
        player = Player("fritz", "m")
        attic = Location("Attic", "A dark attic.")
        julie = Living("julie", "f")
        julie.move(attic)
        player.move(attic)
        parsed = player.parse("wave all")
        self.assertEqual("wave", parsed.verb)
        self.assertEqual(1, parsed.who_count)
        self.assertEqual(julie, parsed.who_1)
        self.assertEqual((julie, None, None), parsed.who_123)
        self.assertEqual(julie, parsed.who_last)
        self.assertEqual([julie], list(parsed.who_info))
        who, playermsg, roommsg, targetmsg = player.soul.process_verb_parsed(player, parsed)
        self.assertEqual({julie}, who)
        self.assertEqual("You wave happily at julie.", playermsg)
        with self.assertRaises(tale.errors.UnknownVerbException):
            player.parse("befrotzificate all and me")
        with self.assertRaises(NonSoulVerb) as x:
            player.parse("befrotzificate all and me", external_verbs={"befrotzificate"})
        parsed = x.exception.parsed
        self.assertEqual("befrotzificate", parsed.verb)
        self.assertEqual(2, parsed.who_count)
        self.assertEqual(julie, parsed.who_1)
        self.assertEqual((julie, player, None), parsed.who_123)
        self.assertEqual([julie, player], list(parsed.who_info))
        self.assertEqual(player, parsed.who_last)
        attic.add_exits([Exit("south", "target", "door")])
        try:
            player.parse("push south")
            self.fail("push south should throw a parse error because of the exit that is used")
        except ParseError:
            pass
        with self.assertRaises(NonSoulVerb):
            player.parse("fart south")
        parsed = player.parse("hug julie")
        player.validate_socialize_targets(parsed)

    def test_verbs(self):
        player = Player("julie", "f")
        player.verbs["smurf"] = ""
        self.assertTrue("smurf" in player.verbs)
        del player.verbs["smurf"]
        self.assertFalse("smurf" in player.verbs)

    def test_handle_and_notify_action(self):
        class SpecialPlayer(Player):
            def init(self):
                self.handled = False
                self.handle_verb_called = False
                self.notify_called = False
                self.notify_args = None

            def handle_verb(self, parsed, actor):
                self.handle_verb_called = True
                if parsed.verb in self.verbs:
                    self.handled = True
                    return True
                else:
                    return False

            def notify_action(self, parsed, actor):
                self.notify_called = True
                self.notify_args = (parsed, actor)

        player = SpecialPlayer("julie", "f")
        player.verbs["xywobble"] = ""
        room = Location("room")

        class Chair(Item):
            def init(self):
                self.handled = False
                self.handle_verb_called = False
                self.notify_called = False
                self.notify_args = None

            def handle_verb(self, parsed, actor):
                self.handle_verb_called = True
                if parsed.verb in self.verbs:
                    self.handled = True
                    return True
                else:
                    return False

            def notify_action(self, parsed, actor):
                self.notify_called = True
                self.notify_args = (parsed, actor)

        chair_in_inventory = Chair("littlechair")
        chair_in_inventory.verbs["kerwaffle"] = ""
        player.insert(chair_in_inventory, player)
        chair = Chair("chair")
        chair.verbs["frobnitz"] = ""
        room.init_inventory([player, chair])

        # first check if the handle_verb passes to all objects including inventory
        parsed = ParseResult("kowabungaa12345")
        handled = room.handle_verb(parsed, player)
        self.assertFalse(handled)
        self.assertTrue(chair.handle_verb_called)
        self.assertTrue(player.handle_verb_called)
        self.assertTrue(chair_in_inventory.handle_verb_called)
        self.assertFalse(chair.handled)
        self.assertFalse(player.handled)
        self.assertFalse(chair_in_inventory.handled)

        # check item handling
        player.init()
        chair.init()
        chair_in_inventory.init()
        parsed = ParseResult("frobnitz")
        handled = room.handle_verb(parsed, player)
        self.assertTrue(handled)
        self.assertTrue(chair.handled)
        self.assertFalse(player.handled)
        self.assertFalse(chair_in_inventory.handled)

        # check living handling
        player.init()
        chair.init()
        chair_in_inventory.init()
        parsed = ParseResult("xywobble")
        handled = room.handle_verb(parsed, player)
        self.assertTrue(handled)
        self.assertFalse(chair.handled)
        self.assertTrue(player.handled)
        self.assertFalse(chair_in_inventory.handled)

        # check inventory handling
        player.init()
        chair.init()
        chair_in_inventory.init()
        parsed = ParseResult("kerwaffle")
        handled = room.handle_verb(parsed, player)
        self.assertTrue(handled)
        self.assertFalse(chair.handled)
        self.assertFalse(player.handled)
        self.assertTrue(chair_in_inventory.handled)

        # check notify_action
        player.init()
        chair.init()
        chair_in_inventory.init()
        room._notify_action_all(parsed, player)
        self.assertTrue(chair.notify_called)
        self.assertTrue(player.notify_called)
        self.assertTrue(chair_in_inventory.notify_called)
        parsed, actor = chair.notify_args
        self.assertIs(player, actor)
        self.assertEqual("kerwaffle", parsed.verb)
        parsed, actor = player.notify_args
        self.assertIs(player, actor)
        self.assertEqual("kerwaffle", parsed.verb)
        parsed, actor = chair_in_inventory.notify_args
        self.assertIs(player, actor)
        self.assertEqual("kerwaffle", parsed.verb)

    def test_move_notify(self):
        class LocationNotify(Location):
            def notify_npc_left(self, npc, target_location):
                self.npc_left = npc
                self.npc_left_target = target_location

            def notify_npc_arrived(self, npc, previous_location):
                self.npc_arrived = npc
                self.npc_arrived_from = previous_location

            def notify_player_left(self, player: Player, target_location: Location) -> None:
                self.player_left = player
                self.player_left_target = target_location

            def notify_player_arrived(self, player: Player, previous_location: Location) -> None:
                self.player_arrived = player
                self.player_arrived_from = previous_location

        player = Player("julie", "f")
        room1 = LocationNotify("room1")
        room2 = LocationNotify("room2")
        room1.insert(player, player)
        player.move(room2)
        pubsub.sync()
        self.assertEqual(room2, player.location)
        self.assertEqual(player, room1.player_left)
        self.assertEqual(room2, room1.player_left_target)
        self.assertEqual(player, room2.player_arrived)
        self.assertEqual(room1, room2.player_arrived_from)


class TestPlayerConnection(unittest.TestCase):
    def setUp(self):
        tale.mud_context.driver = FakeDriver()
        tale.mud_context.config = StoryConfig()
        tale.mud_context.config.server_mode = GameMode.IF
        tale.mud_context.resources = tale.mud_context.driver.resources

    def test_input(self):
        player = Player("julie", "f")
        player.prompt_toolkit_enabled = False
        with WrappedConsoleIO(None) as io:
            pc = PlayerConnection(player, io)
            player.tell("first this text")
            player.store_input_line("      input text     \n")
            x = pc.input_direct("inputprompt")
            self.assertEqual("input text", x)
            self.assertEqual("  first this text\ninputprompt ", sys.stdout.getvalue())  # should have outputted the buffered text

    def test_peek_output(self):
        player = Player("fritz", "m")
        pc = PlayerConnection(player, ConsoleIo(None))
        player.prompt_toolkit_enabled = False
        player.set_screen_sizes(0, 100)
        player.tell("line1")
        player.tell("line2")
        self.assertEqual(["line1\nline2\n"], player.test_peek_output_paragraphs())
        self.assertEqual("line1 line2\n", pc.get_output())
        self.assertEqual([], player.test_peek_output_paragraphs())

    def test_write_output(self):
        player = Player("julie", "f")
        player.prompt_toolkit_enabled = False
        with WrappedConsoleIO(None) as io:
            pc = PlayerConnection(player, io)
            player.tell("hello 1", end=True)
            player.tell("hello 2", end=True)
            pc.write_output()
            self.assertEqual("  hello 2", pc.last_output_line)
            self.assertEqual("  hello 1\n  hello 2\n", sys.stdout.getvalue())

    def test_destroy(self):
        pc = PlayerConnection(None, ConsoleIo(None))
        pc.destroy()
        self.assertIsNone(pc.player)
        self.assertIsNone(pc.io)


class TestTextbuffer(unittest.TestCase):
    def test_empty_lines(self):
        output = TextBuffer()
        output.print("")
        output.print("")
        self.assertEqual([], output.get_paragraphs(), "empty strings shouldn't be stored")
        output.print("", format=False)
        output.print("", format=False)
        self.assertEqual([("\n\n", False)], output.get_paragraphs(), "2 empty strings without format should be stored in 1 paragraph with 2 new lines")
        output.print("", end=True)
        output.print("", end=True)
        self.assertEqual([("\n", True), ("\n", True)], output.get_paragraphs(), "2 empty strings with end=true should be stored in 2 paragraphs")
        output.print("", end=True)
        output.print("", end=True)
        output.print("", end=True)
        self.assertEqual([("\n", True), ("\n", True), ("\n", True)], output.get_paragraphs())
        output.print("")
        output.print("1")
        output.print("2")
        output.print("")
        self.assertEqual([("1\n2\n", True)], output.get_paragraphs())

    def test_end(self):
        output = TextBuffer()
        output.print("1", end=True)
        output.print("2", end=True)
        self.assertEqual([("1\n", True), ("2\n", True)], output.get_paragraphs())
        output.print("one")
        output.print("1", end=True)
        output.print("two")
        output.print("2", end=True)
        output.print("three")
        self.assertEqual([("one\n1\n", True), ("two\n2\n", True), ("three\n", True)], output.get_paragraphs())

    def test_whitespace(self):
        output = TextBuffer()
        output.print("1")
        output.print("2")
        output.print("3")
        self.assertEqual([("1\n2\n3\n", True)], output.get_paragraphs())

    def test_strip(self):
        output = TextBuffer()
        output.print("   1   ", format=True)
        self.assertEqual([("1\n", True)], output.get_paragraphs())
        output.print("   1   ", format=False)
        self.assertEqual([("   1   \n", False)], output.get_paragraphs())


class TestCharacterBuilders(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources

    def test_if_build(self):
        conn = PlayerConnection()
        conf = StoryConfig()
        with WrappedConsoleIO(conn) as io:
            conn.io = io
            b = IFCharacterBuilder(conn, conf)
            builder = b.build_character()
            why, what = next(builder)
            self.assertEqual("input", why)
            self.assertEqual("What shall you be known as?", what[0])

    def test_mud_build(self):
        conn = PlayerConnection()
        conf = StoryConfig()
        with WrappedConsoleIO(conn) as io:
            conn.io = io
            b = MudCharacterBuilder(conn, "PETER", conf)
            self.assertEqual("peter", b.naming.name)
            builder = b.build_character()
            why, what = next(builder)
            self.assertEqual("input-noecho", why)
            self.assertEqual("Please type in the desired password.", what[0])

    def test_validate_race(self):
        validator = ValidRaceValidator(races.playable_races)
        self.assertEqual("human", validator("human"))
        self.assertEqual("human", validator("HUMAN"))
        with self.assertRaises(ValueError):
            validator("elemental")
        with self.assertRaises(ValueError):
            validator("xyz12343")
        with self.assertRaises(ValueError):
            validator("")
        with self.assertRaises(ValueError):
            validator(None)

    def test_playernaming(self):
        n = PlayerNaming()
        n.gender = "m"
        n.name = "RINZWIND"
        n.description = "a wizard"
        n.money = 999
        n.stats = Stats.from_race("elemental")
        n.title = "grand master"
        self.assertEqual("rinzwind", n.name)
        p = Player("dummy", "f")
        p.privileges.add("wiz")
        n.apply_to(p)
        self.assertEqual("rinzwind", p.name)
        self.assertEqual("m", p.gender)
        self.assertEqual({"wiz"}, p.privileges)
        self.assertEqual("a wizard", p.description)
        self.assertEqual(999, p.money)
        self.assertEqual("elemental", p.stats.race)
        self.assertEqual("n", p.stats.gender)
        self.assertEqual(races.BodyType.NEBULOUS, p.stats.bodytype)
        self.assertEqual("Grand master", p.title)

    def test_idle(self):
        p = Player("dummy", "f")
        c = PlayerConnection(p, WrappedConsoleIO(None))
        self.assertLess(p.idle_time, 0.1)
        self.assertLess(c.idle_time, 0.1)
        time.sleep(0.2)
        self.assertGreater(p.idle_time, 0.1)
        self.assertGreater(c.idle_time, 0.1)
        p.store_input_line("input")
        self.assertLess(p.idle_time, 0.1)
        self.assertLess(c.idle_time, 0.1)


class TestTabCompletion(unittest.TestCase):
    def test_complete_c(self):
        player = Player("fritz", "m")
        driver = FakeDriver()
        conn = PlayerConnection(player)
        io = IoAdapterBase(conn)
        conn.io = io
        result = io.tab_complete("c", driver)
        self.assertGreater(len(result), 20)
        self.assertTrue("cackle" in result)
        self.assertTrue("criticize" in result)
        result = io.tab_complete("h", driver)
        self.assertGreater(len(result), 10)
        self.assertTrue("hiss" in result)

    def test_complete_one(self):
        player = Player("fritz", "m")
        driver = FakeDriver()
        conn = PlayerConnection(player)
        io = IoAdapterBase(conn)
        conn.io = io
        self.assertEqual(["criticize"], io.tab_complete("critic", driver))


class TestMudAccounts(unittest.TestCase):
    def setUp(self):
        tale.mud_context.driver = FakeDriver()
        tale.mud_context.config = StoryConfig()
        tale.mud_context.config.server_mode = GameMode.IF
        tale.mud_context.resources = tale.mud_context.driver.resources

    def test_accept_name(self):
        self.assertEqual("irm", MudAccounts.accept_name("irm"))
        self.assertEqual("irmendejongyeahz", MudAccounts.accept_name("irmendejongyeahz"))
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("irmendejongyeahxy")   # too long
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("aa")   # too short
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("Irmen")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("irmen de jong")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("irmen_de_jong")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("irmen444")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name(" irmen")
        with self.assertRaises(ValueError):
            MudAccounts.accept_name("irmen ")

    def test_accept_email(self):
        self.assertEqual("x@y", MudAccounts.accept_email("x@y"))
        self.assertEqual("test@some.domain.com", MudAccounts.accept_email("test@some.domain.com"))
        with self.assertRaises(ValueError):
            MudAccounts.accept_email("@")
        with self.assertRaises(ValueError):
            MudAccounts.accept_email("test@")
        with self.assertRaises(ValueError):
            MudAccounts.accept_email("@test.com")
        with self.assertRaises(ValueError):
            MudAccounts.accept_email(" x@y")
        with self.assertRaises(ValueError):
            MudAccounts.accept_email("x@y ")

    def test_accept_password(self):
        pw = "hello3"
        self.assertEqual(pw, MudAccounts.accept_password(pw))
        pw = "hello this is a long pass pharse 12345"
        self.assertEqual(pw, MudAccounts.accept_password(pw))
        pw = "he44zzz"
        self.assertEqual(pw, MudAccounts.accept_password(pw))
        pw = "   test  2  "
        self.assertEqual(pw, MudAccounts.accept_password(pw))
        with self.assertRaises(ValueError):
            MudAccounts.accept_password("")
        with self.assertRaises(ValueError):
            MudAccounts.accept_password("shrt2")
        with self.assertRaises(ValueError):
            MudAccounts.accept_password("no digits")
        with self.assertRaises(ValueError):
            MudAccounts.accept_password("223242455")

    def test_pwhash(self):
        pw, salt = MudAccounts._pwhash("secret")
        pw2, salt2 = MudAccounts._pwhash("secret")
        self.assertNotEqual(pw, pw2)
        self.assertNotEqual(salt, salt2)
        pw, salt = MudAccounts._pwhash("secret", "some salt")
        pw2, salt2 = MudAccounts._pwhash("secret", "some salt")
        self.assertEqual(pw, pw2)
        self.assertEqual(salt, salt2)

    def test_accountcreate_fail(self):
        stats = Stats()  # uninitialized stats
        accounts = MudAccounts(":memory:")
        with self.assertRaises(ValueError):
            accounts.create("testname", "s3cr3t", "test@invalid", stats, {"wizard"})

    def test_ban(self):
        dbfile = pathlib.Path(tempfile.gettempdir()) / "tale_test_accdb_{0:f}.sqlite".format(time.time())
        actor = Living("normal", gender="f")
        wizard = Living("wizz", gender="f")
        wizard.privileges.add("wizard")
        try:
            accounts = MudAccounts(str(dbfile))
            stats = Stats.from_race("elf", gender='f')
            accounts.create("testname", "s3cr3t", "test@invalid", stats, {"wizard"})
            account = accounts.get("testname")
            self.assertFalse(account.banned)
            with self.assertRaises(ActionRefused):
                accounts.ban("testname", actor)
            with self.assertRaises(LookupError):
                accounts.ban("zerp", wizard)
            accounts.ban("testname", wizard)
            account = accounts.get("testname")
            self.assertTrue(account.banned)
            with self.assertRaises(LookupError):
                accounts.unban("zerp", wizard)
            accounts.unban("testname", wizard)
            account = accounts.get("testname")
            self.assertFalse(account.banned)
        finally:
            dbfile.unlink()

    def test_dbcreate(self):
        dbfile = pathlib.Path(tempfile.gettempdir()) / "tale_test_accdb_{0:f}.sqlite".format(time.time())
        try:
            accounts = MudAccounts(str(dbfile))
            stats = Stats.from_race("elf", gender='f')
            account = accounts.create("testname", "s3cr3t", "test@invalid", stats, {"wizard"})
            self.assertEqual(60.0, account.stats.weight)
            accs = list(accounts.all_accounts())
            self.assertEqual(1, len(accs))
            account = accs[0]
            self.assertEqual("testname", account.name)
            self.assertEqual({"wizard"}, account.privileges)
            self.assertEqual({}, account.story_data)
            self.assertEqual("f", account.stats.gender)
            self.assertEqual(races.BodyType.HUMANOID, account.stats.bodytype)
            self.assertEqual(60.0, account.stats.weight)
            self.assertEqual(races.BodySize.HUMAN_SIZED, account.stats.size)
            self.assertEqual("Edhellen", account.stats.language)
        finally:
            dbfile.unlink()

    def test_storydata(self):
        dbfile = pathlib.Path(tempfile.gettempdir()) / "tale_test_accdb_{0:f}.sqlite".format(time.time())
        try:
            accounts = MudAccounts(str(dbfile))
            stats = Stats.from_race("elf", gender='f')
            accounts.create("testname", "s3cr3t", "test@invalid", stats, {"wizard"})
            account = accounts.get("testname")
            self.assertEqual({}, account.story_data)
            account.story_data = {"test": 42, "thing": [1.2, 3.4]}
            with self.assertRaises(TypeError):
                accounts.save_story_data("testname", "must_be_dictionary")
            accounts.save_story_data("testname", account.story_data)
            account = accounts.get("testname")
            self.assertEqual({"test": 42, "thing": [1.2, 3.4]}, account.story_data)
        finally:
            dbfile.unlink()


class WrappedConsoleIO(ConsoleIo):
    def __init__(self, connection: PlayerConnection) -> None:
        super().__init__(connection)
        self.do_prompt_toolkit = False

    def __enter__(self):
        self._old_stdout = sys.stdout
        sys.stdout = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._old_stdout


if __name__ == '__main__':
    unittest.main()
