"""
Unit tests for race data

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import unittest

import tale.races as races


class TestRaces(unittest.TestCase):
    def test_attributes(self):
        human = races._races["human"]
        self.assertEqual(72.0, human["mass"])
        self.assertEqual(races.BodyType.HUMANOID, human["body"])
        self.assertEqual(races.BodySize.HUMAN_SIZED, human["size"])
        self.assertEqual("English", human["language"])

    def test_generated_race(self):
        human = races.races["human"]
        self.assertEqual(72.0, human.mass)
        self.assertEqual(races.BodyType.HUMANOID, human.body)
        self.assertEqual(races.BodySize.HUMAN_SIZED, human.size)
        self.assertEqual("English", human.language)
        self.assertTrue(human.flags.playable)
        self.assertFalse(races.races["plant"].flags.playable)

    def test_enum_descriptions(self):
        self.assertEqual((8), races.BodySize.SOMEWHAT_LARGE.value)
        self.assertEqual("Somewhat large", races.BodySize.SOMEWHAT_LARGE.text)
        self.assertEqual(8, races.BodySize.SOMEWHAT_LARGE.order)
        self.assertEqual("biped", races.BodyType.BIPED.value)

    def test_bodysize_compare(self):
        self.assertEqual(races.BodySize.LARGE, races.BodySize.LARGE)
        self.assertNotEqual(races.BodySize.LARGE, races.BodySize.SMALL)
        self.assertLess(races.BodySize.TINY, races.BodySize.VAST)
        self.assertGreater(races.BodySize.LARGE, races.BodySize.SMALL)
        self.assertTrue(races.BodySize.LARGE > races.BodySize.SMALL)
        self.assertFalse(races.BodySize.TINY > races.BodySize.GIGANTIC)
        self.assertTrue(races.BodySize.LARGE <= races.BodySize.GIGANTIC)
        self.assertTrue(races.BodySize.LARGE <= races.BodySize.LARGE)
        self.assertTrue(races.BodySize.MICROSCOPIC == races.BodySize.MICROSCOPIC)
        self.assertEqual(0, races.BodySize.LARGE - races.BodySize.LARGE)
        self.assertEqual(4, races.BodySize.LARGE - races.BodySize.SMALL)
        self.assertEqual(races.BodySize.SOMEWHAT_SMALL, races.BodySize.LARGE.adjust(-3))
        self.assertEqual(races.BodySize.VAST, races.BodySize.LARGE.adjust(3))
        with self.assertRaises(LookupError):
            races.BodySize.LARGE.adjust(20)

    def test_globals(self):
        self.assertIn("human", races.playable_races)
        self.assertIn("elf", races.races)


if __name__ == '__main__':
    unittest.main()
