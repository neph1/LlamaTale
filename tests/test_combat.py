import tale
from types import SimpleNamespace
from tale import lang
from tale.base import Location, Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.combat import Combat, apply_damage, lethality_guidance, parse_combat_type
from tale.llm.contexts.CombatContext import CombatContext
from tale.player import Player
from tale.races import BodyType
from tale.skills.weapon_type import WeaponType
from tale.story import CombatType, StoryConfig
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
        attacker.stats.weapon_skills.set(WeaponType.UNARMED, 100)

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()
        assert('hits' in text)
        assert('defender is injured' in text)
        assert('defender dies' in text)
        assert not 'defender attacks' in text


    def test_block_ranged_fails(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A ranged fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')
        defender.stats.weapon_skills.set(WeaponType.UNARMED, 100)
        bow = Weapon(name='bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)

        attacker.wielding = bow
        attacker.stats.weapon_skills.set(WeaponType.TWO_HANDED_RANGED, 100)

        combat = Combat([attacker], [defender])

        text = combat.resolve_attack()
        assert(defender.stats.hp < defender.stats.max_hp)
        assert('defender is injured' in text)
        assert('defender dies' in text)

    def test_block_with_ranged_fails(self):
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='m', age=42, personality='A ranged fighter')
        attacker.stats.weapon_skills.set(WeaponType.UNARMED, 100)
        bow = Weapon(name='bow', weapon_type=WeaponType.TWO_HANDED_RANGED, base_damage=10, weight=1, value=1)

        defender.wielding = bow
        defender.stats.weapon_skills.set(WeaponType.TWO_HANDED_RANGED, 100)

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
        # no story loaded: historical/lethal defaults are narrated to the LLM
        assert('historical' in combat_prompt)
        assert('lethal' in combat_prompt)
        assert('Death is possible' in combat_prompt)

    def test_prepare_combat_prompt_nonlethal_story(self):
        driver = tale.driver.Driver()
        config = StoryConfig()
        config.combat_type = CombatType.SPARRING.value
        config.lethal = False
        driver.story = SimpleNamespace(config=config)
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')

        combat_prompt, msg = driver.prepare_combat_prompt(attackers=[attacker],
                                                     defenders=[rat],
                                                     attacker_msg='attacker hits',
                                                     combat_result='attacker hits',
                                                     location_title='the arena')

        assert('sparring' in combat_prompt)
        assert('non-lethal' in combat_prompt)
        assert('controlled practice' in combat_prompt)
        assert('Death is possible' not in combat_prompt)

    def test_prepare_combat_prompt_custom_combat_type(self):
        driver = tale.driver.Driver()
        config = StoryConfig()
        config.combat_type = 'wuxia wire-fu choreography'
        config.lethal = False
        driver.story = SimpleNamespace(config=config)
        attacker = LivingNpc(name='attacker', gender='f', age=37, personality='A fierce fighter')
        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')

        combat_prompt, msg = driver.prepare_combat_prompt(attackers=[attacker],
                                                     defenders=[rat],
                                                     attacker_msg='attacker hits',
                                                     combat_result='attacker hits',
                                                     location_title='the arena')

        # free-text tone is passed verbatim, lethal flag picks the guidance
        assert('wuxia wire-fu choreography' in combat_prompt)
        assert('non-lethal' in combat_prompt)
        assert('Nobody dies' in combat_prompt)

    def test_nonlethal_combat_floors_hp_at_one(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')
        attacker.stats.weapon_skills.set(WeaponType.UNARMED, 100)
        attacker.stats.wc = 100
        defender.stats.hp = 5
        defender.stats.max_hp = 5

        combat = Combat([attacker], [defender], lethal=False)
        text = combat.resolve_attack()

        assert defender.stats.hp == 1
        assert defender.alive
        assert 'defender is knocked out and yields.' in text
        assert 'dies' not in text

        # further hits cannot push hp below 1 either
        text = combat.resolve_attack()
        assert defender.stats.hp == 1
        assert defender.alive
        assert 'dies' not in text

    def test_lethal_combat_can_kill(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')
        attacker.stats.weapon_skills.set(WeaponType.UNARMED, 100)
        attacker.stats.wc = 100
        defender.stats.hp = 5
        defender.stats.max_hp = 5

        combat = Combat([attacker], [defender], lethal=True)
        text = combat.resolve_attack()

        assert defender.stats.hp < 1
        assert 'defender dies from their injuries.' in text

    def test_apply_damage_floor(self):
        rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')
        rat.stats.hp = 5
        assert apply_damage(rat, 100, lethal=False) == 4
        assert rat.stats.hp == 1
        assert apply_damage(rat, 3, lethal=False) == 0
        assert rat.stats.hp == 1
        assert apply_damage(rat, 3, lethal=True) == 3
        assert rat.stats.hp == -2

    def test_parse_combat_type(self):
        assert parse_combat_type('non-lethal') == CombatType.NONLETHAL
        assert parse_combat_type('ULTRA-VIOLENT') == CombatType.ULTRAVIOLENT
        assert parse_combat_type('Sparring') == CombatType.SPARRING
        assert parse_combat_type('cartoony') == CombatType.CARTOONY
        assert parse_combat_type('wuxia wire-fu') is None
        assert parse_combat_type('') is None
        assert parse_combat_type(None) is None

    def test_lethality_guidance(self):
        assert 'Nobody dies' in lethality_guidance('non-lethal', False)
        assert 'controlled practice' in lethality_guidance('sparring', False)
        assert 'slapstick' in lethality_guidance('cartoony', False)
        assert 'Death is possible' in lethality_guidance('historical', True)
        assert 'Do not sanitize' in lethality_guidance('ultra-violent', True)
        # free text: lethal flag alone picks the guidance
        assert 'Nobody dies' in lethality_guidance('wuxia wire-fu', False)
        assert 'Death is possible' in lethality_guidance('wuxia wire-fu', True)

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
        attacker.stats.weapon_skills.set(WeaponType.UNARMED, 100)
        attacker2.stats.level = 10
        attacker2.stats.weapon_skills.set(WeaponType.UNARMED, 100)

        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')

        combat = Combat(attackers=[attacker, attacker2], defenders=[defender])

        text = combat.resolve_attack()

        self._assert_combat(attacker, defender, text)
        assert('attacker attacks')
        assert('attacker2 attacks')

    def test_start_attack_no_combat_points(self):
        attacker = Player(name='att', gender='m')
        attacker.stats.action_points = 0
        defender = LivingNpc(name='lucky rat', gender='m', age=2, personality='A squeeky fighter')

        assert attacker.start_attack(defender) == None
        assert ['You are too tired to attack.\n'] == attacker.test_get_output_paragraphs()