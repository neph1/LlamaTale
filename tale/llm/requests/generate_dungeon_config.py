

from tale.llm import llm_config
from tale.llm.requests.llm_request import LlmRequest


class GenerateDungeonConfig(LlmRequest):
    """
    Generates a dungeon configuration for a zone.
    """

    def build_prompt(self, args: dict) -> str:
        zone_info = args['zone_info']
        
        prompt = llm_config.params['PRE_JSON_PROMPT']
        prompt += llm_config.params['CREATE_DUNGEON_CONFIG_PROMPT'].format(
            context='{context}',
            zone_info=zone_info,
            dungeon_config_template=llm_config.params['DUNGEON_CONFIG_TEMPLATE'])
        return prompt
