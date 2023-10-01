
import random
from tale.llm import llm_config
from tale.llm.requests.llm_request import LlmRequest


class StartLocation(LlmRequest):

    def __init__(self) -> None:
        super().__init__()
        self.pre_json_prompt = llm_config.params['PRE_JSON_PROMPT'] # Type: str
        self.location_prompt = llm_config.params['CREATE_LOCATION_PROMPT'] # Type: str
        self.start_location_prompt = llm_config.params['START_LOCATION_PROMPT'] # Type: str
        self.items_prompt = llm_config.params['ITEMS_PROMPT'] # Type: str

    def build_prompt(self, args: dict) -> str:
        # TODO: this is a just a placeholder algo to create some things randomly.
        zone_info = args['zone_info'] # Type: dict
        location = args['location'] # Type: Location
        story_type = args['story_type'] # Type: str
        world_info = args['world_info'] # Type: str
        story_context = args['story_context'] # Type: str

        items_prompt = ''
        item_amount = random.randint(0, 2)
        if item_amount > 0:
            items_prompt = self.items_prompt.format(items=item_amount)

        prompt = self.pre_json_prompt
        prompt += self.start_location_prompt.format(
            story_type=story_type,
            world_info=world_info,
            location_description=location.description,
            zone_info=zone_info,
            story_context=story_context,
            spawn_prompt='',
            items_prompt=items_prompt)
        
        return prompt