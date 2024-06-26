

from tale import parse_utils
from tale.base import Weapon
from tale.items import generic
from tale.items.basic import Food, Health, Note
from tale.weapon_type import WeaponType


class TestGenericItems():

    def test_load(self):
        assert(generic.items)

    def test_generic_items(self):
        assert(generic.generic_items)
        assert(generic.generic_items['fantasy'])
        assert(generic.generic_items['modern'])
        assert(generic.generic_items['postapoc'])
        assert(generic.generic_items['scifi'])
        assert(generic.generic_items[''])
        fantasy_weapon = generic.fantasy_weapons[0]
        assert(fantasy_weapon)
        assert(fantasy_weapon['name'] == 'Sword')
        items = parse_utils.load_items(generic.fantasy_weapons)
        assert(items)
        item = items['Sword']
        assert(isinstance(item, Weapon))
        assert(item.type == WeaponType.ONE_HANDED)

    def test_various(self):
        items = parse_utils.load_items(generic.generic_various)
        food = items['Bread']
        assert(isinstance(food, Food))
        assert(food.affect_fullness == 10)
        note = items['Note']
        assert(isinstance(note, Note))

    def test_health(self):
        items = parse_utils.load_items(generic.fantasy_items)
        assert(items)
        item = items['Potion of healing']
        assert(isinstance(item, Health))
        assert(item.healing_effect == 10)