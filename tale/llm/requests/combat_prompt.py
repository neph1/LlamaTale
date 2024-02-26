

from tale import lang, player
from tale.llm.LivingNpc import LivingNpc
from tale.llm import llm_config
from tale.llm.requests.llm_request import LlmRequest


class CombatPrompt(LlmRequest):
   
   def __init__(self) -> None:
        super().__init__()
        self.pre_json_prompt = llm_config.params['PRE_JSON_PROMPT'] # Type: str
        self.combat_prompt = llm_config.params['COMBAT_PROMPT'] # Type: str
   
   
   def build_prompt(self, attacker: LivingNpc, 
                              victim: LivingNpc, 
                              location_title: str, 
                              location_description: str, 
                              attacker_msg: str):
        """ TODO: A bad work around. Need to find a better way to do this."""
        attacker_name = lang.capital(attacker.title)
        victim_name = lang.capital(victim.title)

        if isinstance(attacker, player.Player):
            attacker_name += " (as 'You')"
            attacker_msg.replace(attacker_name, "you")
        if isinstance(victim, player.Player):
            victim_name += " (as 'You')"
            attacker_msg.replace(victim_name, "you")

        victim_info = {"name": victim_name, 
                       "health": victim.stats.hp / victim.stats.max_hp, 
                       "weapon": victim.wielding.title}

        attacker_info = {"name": attacker_name, 
                         "health": attacker.stats.hp / attacker.stats.max_hp, 
                         "weapon": attacker.wielding.title}

        return self.combat_prompt.format(attacker=attacker_info, 
                                                    victim=victim_info,
                                                    attacker_msg=attacker_msg,
                                                    location=location_title,
                                                    location_description=location_description) 