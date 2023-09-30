

import json
import random
from tale.llm import llm_config
from tale import parse_utils
from tale.llm.requests.llm_request import LlmRequest


class StartZone(LlmRequest):
    """
    Generates a zone.
    """

    def __init__(self) -> None:
        super().__init__()
        self.pre_json_prompt = llm_config.params['PRE_JSON_PROMPT'] # Type: str
        self.zone_prompt = llm_config.params['CREATE_ZONE_PROMPT'] # Type: str
        

    def build_prompt(self, args: dict) -> str:
        location_desc = args['location_desc']
        story_type = args['story_type']
        world_info = args['world_info']
        story_context = args['story_context']

        prompt = self.pre_json_prompt
        prompt += self.zone_prompt.format(
            world_info=world_info,
            mood = parse_utils.mood_string_from_int(random.gauss(world_info["world_mood"], 2)),
            story_type=story_type,
            direction='',
            zone_info='',
            story_context=story_context,
            exit_location='',
            location_desc=location_desc)
        return prompt;