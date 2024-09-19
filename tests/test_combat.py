import tale
from tale import lang
from tale.base import Location, Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.combat import Combat
from tale.llm.contexts.CombatContext import CombatContext
from tale.player import Player
from tale.races import BodyType
from tale.skills.weapon_type import WeaponType
from tale.wearable import WearLocation
from tests.supportstuff import FakeDriver
from tale.wearable import WearLocation
import tale.util as util



class TestCombat():

    def test_resolve_attack(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()

        self._assert_combat(attacker, defender, text)
        
        attacker.stats.level = 10
        attacker.stats.set_weapon_skill(WeaponType.UNARMED, 100)

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()
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

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()
        assert(defender.stats.hp < defender.stats.max_hp)
        assert('defender is injured' in text)
        assert('defender dies' in text)

    def test_block_with_ranged_fails(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')
        attacker.stats.set_weapon_skill(WeaponType.UNARMED, 100)
        bow = Weapon(name='bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)

        defender.wielding = bow
        defender.stats.set_weapon_skill(WeaponType.TWO_HANDED_RANGED, 100)

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()
        assert(defender.stats.hp < defender.stats.max_hp)
        assert('defender is injured' in text)
        assert('defender dies' in text)
        

    def test_produce_remains(self):
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')
        rat.should_produce_remains = True
        remains = rat.do_on_death()
        assert not rat.alive
        assert(remains)
        assert(remains.location == rat.location)
        remains.location.remove(remains, None)

    def test_not_produce_remains(self):
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        bunny = LivingNpc(name='Bunny rabbit', gender='m', age=4, personality='Nice and fluffy')
        bunny.should_produce_remains = False
        remains = bunny.do_on_death()
        assert not bunny.alive
        assert(not remains)

    def _assert_combat(self, attacker, defender, text):
        if attacker.stats.hp < attacker.stats.max_hp:
            assert('attacker is injured' in text)
        if defender.stats.hp < defender.stats.max_hp:
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


        combat_prompt, msg = driver.prepare_combat_prompt(attackers=[attacker], 
                                                     defenders=[rat],
                                                     attacker_msg='attacker hits',
                                                     combat_result='attacker hits',
                                                     location_title='the arena')
        
        assert(lang.capital(attacker.title) in combat_prompt)
        assert('the arena' in combat_prompt)
        assert(lang.capital(rat.title) in combat_prompt)
        assert('attacker hits' in combat_prompt)
        assert msg == 'attacker hits'

    def test_combat_context(self):
        location = Location('Test Location', 'Test Location')
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')

        combat_context = CombatContext(attackers=[attacker], defenders=[defender], location_description=location.description)

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

        assert body_part != WearLocation.FULL_BODY

        body_part = combat.resolve_body_part(defender, size_factor=1000.0)

        assert body_part != WearLocation.FEET
        assert body_part != WearLocation.LEGS

        body_part = combat.resolve_body_part(defender, size_factor=0.001)

        assert body_part != WearLocation.HEAD
        assert body_part != WearLocation.TORSO

    def test_resolve_body_part_quadruped(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='giant rat', gender='m', age=2, personality='A squeeky fighter')
        defender.stats.bodytype = BodyType.QUADRUPED

        combat = Combat(attacker, defender)

        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part != WearLocation.FULL_BODY
        assert body_part != WearLocation.BACK
        assert body_part != WearLocation.HANDS

    def test_resolve_body_part_others(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='giant rat', gender='m', age=2, personality='A squeeky fighter')
        combat = Combat(attacker, defender)

        defender.stats.bodytype = BodyType.BIPED
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = BodyType.INSECTOID
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = BodyType.AVIAN
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY

        defender.stats.bodytype = BodyType.FISH
        body_part = combat.resolve_body_part(defender, size_factor=1.0)

        assert body_part == WearLocation.FULL_BODY


    def test_parse_attack(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='giant rat', gender='m', age=2, personality='A squeeky fighter')
        location = Location('Test Location', 'Test Location')
        location.init_inventory([attacker, defender])

        command = "attack giant rat head"
        parsed = attacker.parse(command, external_verbs=[])

        assert parsed.verb == 'attack'
        assert parsed.args == ['giant rat', 'head']

        assert parsed.args[1].upper() in WearLocation.__members__

        command = "attack giant rat tail"
        parsed = attacker.parse(command, external_verbs=[])

        assert parsed.verb == 'attack'
        assert parsed.args == ['giant rat', 'tail']

        assert parsed.args[1].upper() not in WearLocation.__members__

    def test_resolve_attack_group(self):
        
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        attacker2 = LivingNpc(name='attacker2', gender='m', age=42, personality='A fierce fighter')

        attacker.stats.level = 10
        attacker.stats.set_weapon_skill(WeaponType.UNARMED, 100)
        attacker2.stats.level = 10
        attacker2.stats.set_weapon_skill(WeaponType.UNARMED, 100)

        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')

        combat = Combat(attackers=[attacker, attacker2], defenders=[defender])

        text = combat.resolve_attack()

        self._assert_combat(attacker, defender, text)
        assert('attacker hits' in text or 'attacker performs a critical hit' in text)
        assert('attacker2 hits' in text or 'attacker2 performs a critical hit' in text)

    def test_start_attack_no_combat_points(self):
        attacker = Player(name='att', gender='m')
        attacker.stats.action_points = 0
        defender = LivingNpc(name='lucky rat', gender='m', age=2, personality='A squeeky fighter')

        assert attacker.start_attack(defender) == None
        assert ['You are too tired to attack.\n'] == attacker.test_get_output_paragraphs()