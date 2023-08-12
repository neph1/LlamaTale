from tale.llm_ext import LivingNpc
from tests.supportstuff import FakeDriver
import tale.combat as combat
import tale.util as util


class TestCombat():

    def test_resolve_attack(self):
        attacker = LivingNpc(name='attacker', gender='m', age=42, personality='A fierce fighter')
        defender = LivingNpc(name='defender', gender='f', age=37, personality='A fierce fighter')

        text, damage_to_attacker, damage_to_defender = combat.resolve_attack(attacker, defender)

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
        
    # def test_produce_remains(self):
    #     ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
    #     rat = LivingNpc(name='Giant Rat', gender='m', age=4, personality='Sneaky and nasty')
    #     remains = combat.produce_remains(ctx, rat)
    #     assert(remains)
