
import random
from tale import parse_utils
from tale.llm import llm_config
from tale.llm.requests.llm_request import LlmRequest


class BuildLocation(LlmRequest):

    def __init__(self) -> None:
        super().__init__()
        self.pre_json_prompt = llm_config.params['PRE_JSON_PROMPT'] # Type: str
        self.location_prompt = llm_config.params['CREATE_LOCATION_PROMPT'] # Type: str
        self.spawn_prompt = llm_config.params['SPAWN_PROMPT'] # Type: str
        self.items_prompt = llm_config.params['ITEMS_PROMPT'] # Type: str

    def build_prompt(self, args: dict) -> str:
        # TODO: this is a just a placeholder algo to create some things randomly.
        zone_info = args['zone_info'] # Type: dict
        location = args['location'] # Type: Location
        exit_location_name = args['exit_location_name'] # Type: str
        story_type = args['story_type'] # Type: str
        world_info = args['world_info'] # Type: str
        story_context = args['story_context'] # Type: str

        spawn_prompt = ''
        spawn_chance = 0.25
        spawn = random.random() < spawn_chance
        if spawn:
            mood = zone_info.get('mood', 0)
            if isinstance(mood, str):
                num_mood = parse_utils.mood_int_from_string(mood)
            else:
                num_mood = mood
            num_mood = (int) (random.gauss(zone_info.get('mood', 0), 2))
            level = (int) (random.gauss(zone_info.get('level', 1), 2))
            mood_string = parse_utils.mood_string_from_int(num_mood)
            spawn_prompt = self.spawn_prompt.format(alignment=mood_string, level=level)

        items_prompt = ''
        item_amount = (int) (random.gauss(1, 2))
        if item_amount > 0:
            items_prompt = self.items_prompt.format(items=item_amount)

        prompt = self.pre_json_prompt
        prompt += self.location_prompt.format(
            story_type=story_type,
            world_info=world_info,
            zone_info=zone_info,
            story_context=story_context,
            exit_locations=exit_location_name,
            location_name=location.name,
            spawn_prompt=spawn_prompt,
            items_prompt=items_prompt,)
        return prompt