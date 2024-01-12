

import json
import random
from tale.llm import llm_config
from tale import parse_utils
from tale.llm.requests.llm_request import LlmRequest


class GenerateZone(LlmRequest):
    """
    Generates a zone.
    """

    def build_prompt(self, args: dict) -> str:
        direction = args['direction']
        current_zone_info = args['current_zone_info']
        exit_location_name = args['exit_location_name']
        location_desc = args['location_desc']
        world_mood = args['world_mood']
        catalogue = args['catalogue']

        prompt = llm_config.params['PRE_JSON_PROMPT']
        prompt += llm_config.params['CREATE_ZONE_PROMPT'].format(
            context='',
            mood = parse_utils.mood_string_from_int(random.gauss(world_mood, 2)),
            direction=direction,
            zone_info=json.dumps(current_zone_info),
            exit_location=exit_location_name,
            location_desc=location_desc,
            catalogue=catalogue,
            zone_template=llm_config.params['ZONE_TEMPLATE'])
        return prompt