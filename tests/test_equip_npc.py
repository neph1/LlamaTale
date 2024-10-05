from tale import mud_context, util
from tale.driver_if import IFDriver
from tale.equip_npcs import _get_item_by_name_or_random, dress_npc, equip_npc
from tale.items import generic
from tale.llm.LivingNpc import LivingNpc
from tale.races import BodyType
from tale.story import MoneyType


class TestEquipNPC:


    mud_context.driver = IFDriver()
    

    def test_equip_soldier(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.moneyfmt = util.MoneyFormatterFantasy()
        items = generic.generic_items.get('fantasy')

        npc = LivingNpc('Test', gender='m', occupation='Soldier')

        equip_npc(npc, items)

        assert npc.inventory
        assert npc.money > 0
        assert npc.wielding.name in ['sword', 'spear']

    def test_equip_wolf(self):

        items = generic.generic_items.get('fantasy')

        npc = LivingNpc('Test', gender='m', occupation='Soldier', race='wolf')
        npc.stats.bodytype = 'QUADRUPED'

        equip_npc(npc, items)

        assert not npc.inventory
        assert npc.money == 0
        assert npc.wielding.name not in ['sword', 'spear']

    def test_equip_centaur(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.moneyfmt = util.MoneyFormatterFantasy()
        items = generic.generic_items.get('fantasy')

        npc = LivingNpc('Test', gender='m', occupation='Soldier')
        npc.stats.bodytype = BodyType.SEMI_BIPEDAL

        equip_npc(npc, items)

        assert npc.inventory
        assert npc.money > 0
        assert npc.wielding
        assert npc.wielding.name in ['sword', 'spear']

    def test_dress_npc_with_wearables(self):
        npc = LivingNpc('Test', gender='m')
        setting = 'fantasy'
        dress_npc(npc, setting, max_attempts=50)
        assert npc.inventory
        assert npc.get_worn_items()

    def test_get_by_name_or_random(self):
        items = [{"name": "Sword", "type": "weapon", "value": 100, "weapon_type":"ONE_HANDED"}, {"name": "Spear", "type": "weapon", "value": 100, "weapon_type":"TWO_HANDED"}, {"name": "shield", "type": "armor", "value": 60}, {"name": "boots", "type": "armor", "value": 50}]
        weapon = _get_item_by_name_or_random('Sword', {item['name']: item for item in items})
        assert weapon
