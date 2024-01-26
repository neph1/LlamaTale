from tale import driver
from tale.base import Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.combat import Combat
from tale.weapon_type import WeaponType
from tests.supportstuff import FakeDriver
import tale.combat as combat
import tale.util as util
import tale.combat



class TestCombat():

    def test_resolve_attack(self):
        

        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')

        combat = Combat(attacker, defender)

        text, damage_to_attacker, damage_to_defender = combat.resolve_attack()

        self._assert_combat(attacker, defender, text, damage_to_attacker, damage_to_defender)
        
        attacker.stats.level = 10
        attacker.stats.set_weapon_skill(WeaponType.UNARMED, 100)

        combat = Combat(attacker, defender)

        text, damage_to_attacker, damage_to_defender = combat.resolve_attack()
        assert('attacker hits' in text or 'attacker performs a critical hit' in text)
        assert('defender is injured' in text)
        assert('defender dies' in text)


    def test_block_ranged_fails(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A ranged fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')
        defender.stats.set_weapon_skill(WeaponType.UNARMED, 100)
        bow = Weapon(name='bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)

        attacker.wielding = bow
        attacker.stats.set_weapon_skill(WeaponType.TWO_HANDED_RANGED, 100)

        combat = Combat(attacker, defender)

        text, damage_to_attacker, damage_to_defender = combat.resolve_attack()
        assert(damage_to_defender > 0)
        assert('defender is injured' in text)
        assert('defender dies' in text)

    def test_block_with_ranged_fails(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')
        attacker.stats.set_weapon_skill(WeaponType.UNARMED, 100)
        bow = Weapon(name='bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)

        defender.wielding = bow
        defender.stats.set_weapon_skill(WeaponType.TWO_HANDED_RANGED, 100)

        combat = Combat(attacker, defender)

        text, damage_to_attacker, damage_to_defender = combat.resolve_attack()
        assert(damage_to_defender > 0)
        assert('defender is injured' in text)
        assert('defender dies' in text)
        

    def test_produce_remains(self):
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')
        rat.should_produce_remains = True
        remains = rat.do_on_death(ctx)
        assert(remains)
        remains.location.remove(remains, None)

    def test_not_produce_remains(self):
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        bunny = LivingNpc(name='Bunny rabbit', gender='m', age=4, personality='Nice and fluffy')
        bunny.should_produce_remains = False
        remains = bunny.do_on_death(ctx)
        assert(not remains)

    def _assert_combat(self, attacker, defender, text, damage_to_attacker, damage_to_defender):
        assert(damage_to_attacker >= 0)
        assert(damage_to_defender >= 0)

        if damage_to_attacker > 0:
            assert('attacker is injured' in text)
        if damage_to_defender > 0:
            assert('defender is injured' in text)
        if attacker.stats.hp < 1:
            assert('attacker dies' in text)
        if defender.stats.hp < 1:
            assert('defender dies' in text)


    def test_prepare_combat_prompt(self):
        driver = tale.driver.Driver()
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        bow = Weapon(name='Bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)
        attacker.wielding = bow  

        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')


        combat_prompt = driver.prepare_combat_prompt(attacker=attacker, 
                                                     victim=rat,
                                                     attacker_msg='attacker hits',
                                                     location_title='the arena',
                                                     location_description='A large arena')
        
        assert('Bow' in combat_prompt)
        assert('attacker hits' in combat_prompt)
        assert('the arena' in combat_prompt)
        assert('A large arena' in combat_prompt)
        assert('Giant Rat' in combat_prompt)

