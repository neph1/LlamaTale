

import json
import random
from tale import parse_utils
from tale.llm.requests.llm_request import LlmRequest


class GenerateZone(LlmRequest):
    """
    Generates a zone.
    """

    def __init__(self, pre_json_prompt: str, zone_prompt: str) -> None:
        super().__init__()
        self.pre_json_prompt = pre_json_prompt
        self.zone_prompt = zone_prompt
        

    def build_prompt(self, args: dict) -> str:
        direction = args['direction']
        current_zone_info = args['current_zone_info']
        exit_location_name = args['exit_location_name']
        location_desc = args['location_desc']
        story_type = args['story_type']
        world_info = args['world_info']
        world_mood = args['world_mood']
        self.story_context = args['story_context']

        prompt = self.pre_json_prompt
        prompt += self.zone_prompt.format(
            world_info=world_info,
            mood = parse_utils.mood_string_from_int(random.gauss(world_mood, 2)),
            story_type=story_type,
            direction=direction,
            zone_info=json.dumps(current_zone_info),
            story_context=self.story_context,
            exit_location=exit_location_name,
            location_desc=location_desc)
        return prompt;