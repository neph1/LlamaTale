
from typing import Any

class CombatContext():

    class CombatContext():
        def __init__(self, attacker: Any, defender: Any, location: Any) -> None:
            self.victim_info = {"name": defender.name, 
                                "health": defender.stats.hp / defender.stats.max_hp, 
                                "weapon": defender.wielding.title}

            self.attacker_info = {"name": attacker.name, 
                                  "health": attacker.stats.hp / attacker.stats.max_hp, 
                                  "weapon": attacker.wielding.title}
            self.location_description = location.description

    def to_prompt_string(self) -> str:
        return f"Attacker: {self.attacker_info['name']} ({self.attacker_info['health']}); Defender: {self.victim_info['name']} ({self.victim_info['health']}); Location: {self.location_description}"