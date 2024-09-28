from tale import mud_context, util
from tale.driver_if import IFDriver
from tale.equip_npcs import equip_npc
from tale.items import generic
from tale.llm.LivingNpc import LivingNpc
from tale.story import MoneyType


class TestEquipNPC:

    items = generic.generic_items.get('fantasy')

    mud_context.driver = IFDriver()
    mud_context.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.FANTASY)

    def test_equip_soldier(self):
        npc = LivingNpc('Test', gender='m', occupation='Soldier')

        equip_npc(npc, self.items)

        assert npc.inventory
        assert npc.money > 0