from abc import ABC
from enum import Enum


class MagicType(Enum):
    HEAL = 1
    BOLT = 2
    DRAIN = 3
    REJUVENATE = 4
    HIDE = 5
    REVEAL = 6



class Spell(ABC):
    def __init__(self, name: str, base_cost: int, base_value: int = 1, max_level: int = -1):
        self.name = name
        self.base_value = base_value
        self.base_cost = base_cost
        self.max_level = max_level

    def check_cost(self, magic_points: int, level: int) -> bool:
        return magic_points >= self.base_cost * level

spells = {
    MagicType.HEAL: Spell('heal', base_cost=2, base_value=5),
    MagicType.BOLT: Spell('bolt', base_cost=3, base_value=5),
    MagicType.DRAIN: Spell('drain', base_cost=3, base_value=5),
    MagicType.REJUVENATE: Spell('rejuvenate', base_cost=2, base_value=4),
    MagicType.HIDE: Spell('hide', base_cost=3),
    MagicType.REVEAL: Spell('reveal', base_cost=3)
}

class MagicSkill:
    def __init__(self, spell: Spell, skill: int = 0):
        self.spell = spell
        self.skill = skill
