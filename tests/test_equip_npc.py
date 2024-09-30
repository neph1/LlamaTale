from tale import mud_context, util
from tale.driver_if import IFDriver
from tale.equip_npcs import equip_npc
from tale.items import generic
from tale.llm.LivingNpc import LivingNpc
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

    def test_equip_wolf(self):

        items = generic.generic_items.get('fantasy')

        npc = LivingNpc('Test', gender='m', occupation='Soldier', race='wolf')
        npc.stats.bodytype = 'QUADRUPED'

        equip_npc(npc, items)

        assert not npc.inventory
        assert npc.money == 0