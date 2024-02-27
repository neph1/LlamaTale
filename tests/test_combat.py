import tale
from tale import lang
from tale.base import Location, Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.combat import Combat
from tale.llm.contexts.CombatContext import CombatContext
from tale.weapon_type import WeaponType
from tale.wearable import WearLocation
from tests.supportstuff import FakeDriver
from tale.wearable import WearLocation
import tale.util as util



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
        assert not rat.alive
        assert(remains)
        assert(remains.location == rat.location)
        remains.location.remove(remains, None)

    def test_not_produce_remains(self):
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        bunny = LivingNpc(name='Bunny rabbit', gender='m', age=4, personality='Nice and fluffy')
        bunny.should_produce_remains = False
        remains = bunny.do_on_death(ctx)
        assert not bunny.alive
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


        combat_prompt, msg = driver.prepare_combat_prompt(attacker=attacker, 
                                                     defender=rat,
                                                     attacker_msg='attacker hits',
                                                     combat_result='attacker hits',
                                                     location_title='the arena')
        
        assert(lang.capital(attacker.title) in combat_prompt)
        assert('the arena' in combat_prompt)
        assert(lang.capital(rat.title) in combat_prompt)
        assert(lang.capital(attacker.title) in combat_prompt)
        assert('the arena' in combat_prompt)
        assert(lang.capital(rat.title) in combat_prompt)
        assert('attacker hits' in combat_prompt)
        assert msg == 'attacker hits'

    def test_combat_context(self):
        location = Location('Test Location', 'Test Location')
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')

        combat_context = CombatContext(attacker_name=attacker.name, attacker_health=attacker.stats.hp / attacker.stats.max_hp, attacker_weapon=attacker.wielding.name, defender_name=defender.name, defender_health=defender.stats.hp / defender.stats.max_hp, defender_weapon=defender.wielding.name, location_description=location.description)

        context_string = combat_context.to_prompt_string()
        assert location.description in context_string
        assert attacker.name in context_string
        assert str(attacker.stats.hp / attacker.stats.max_hp) in context_string
        assert defender.name in context_string
        assert str(defender.stats.hp / defender.stats.max_hp) in context_string


    def test_resolve_body_part(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')

        combat = Combat(attacker, defender)

        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert isinstance(body_part, WearLocation)

        body_part = combat.resolve_body_part(defender, size_factor=1000.0)

        assert body_part != WearLocation.FEET
        assert body_part != WearLocation.LEGS

        body_part = combat.resolve_body_part(defender, size_factor=0.001)

        assert body_part != WearLocation.HEAD
        assert body_part != WearLocation.TORSO

    def test_resolve_body_part_quadruped(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='giant rat', gender='m', age=2, personality='A squeeky fighter')
        defender.stats.bodytype = 'QUADRUPED'

        combat = Combat(attacker, defender)

        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part != WearLocation.FULL_BODY
        assert body_part != WearLocation.BACK
        assert body_part != WearLocation.HANDS

    def test_resolbe_body_part_others(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='giant rat', gender='m', age=2, personality='A squeeky fighter')
        combat = Combat(attacker, defender)

        defender.stats.bodytype = 'BIPED'
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = 'INSECTOID'
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = 'AVIAN'
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = 'FISH'
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY


