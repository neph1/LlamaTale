from abc import ABC
from enum import Enum


class MagicType(Enum):
    HEAL = 1



class Spell(ABC):
    def __init__(self, name: str, base_cost: int, base_value: int = 1, max_level: int = -1):
        self.name = name
        self.base_value = base_value
        self.base_cost = base_cost
        self.max_level = max_level

    def do_cast(self, player, target, level):
        pass

spells = {
    MagicType.HEAL: Spell('heal', base_cost=2, base_value=5)
}

class MagicSkill:
    def __init__(self, spell: Spell, skill: int = 0):
        self.spell = spell
        self.skill = skill
