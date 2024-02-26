class CombatContext():

    def __init__(self, attacker_name: str, attacker_health: float, attacker_weapon: str, defender_name: str, defender_health: float, defender_weapon: str, location_description: str) -> None:
        self.victim_info = {"name": defender_name, 
                       "health": defender_health, 
                       "weapon": defender_weapon}

        self.attacker_info = {"name": attacker_name, 
                         "health": attacker_health, 
                         "weapon": attacker_weapon}
        self.location_description = location_description

    def to_prompt_string(self) -> str:
        return f"Attacker: {self.attacker_info['name']} ({self.attacker_info['health']}); Defender: {self.victim_info['name']} ({self.victim_info['health']}); Location: {self.location_description}"