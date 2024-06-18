from typing import List


class CombatContext():

    def __init__(self, attackers: List['base.Living'], defenders: List['base.Living'], location_description: str) -> None:
        self.attackers = attackers
        self.defenders = defenders
        self.location_description = location_description

    def to_prompt_string(self) -> str:
        attackers_info = []
        for attacker in self.attackers:
            attackers_info.append(f"{attacker.name}: Health:({str(attacker.stats.hp / attacker.stats.max_hp)}). Weapon: {attacker.wielding.name}.")
        defenders_info = []
        for defender in self.defenders:
            defenders_info.append(f"{defender.name}: Health:({str(defender.stats.hp / defender.stats.max_hp)}). Weapon: {defender.wielding.name}.")
        return f"Attackers: {attackers_info}; Defenders: {defenders_info}; Location: {self.location_description}."