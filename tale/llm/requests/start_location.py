import random
from tale.llm import llm_config
from tale.llm.requests.llm_request import LlmRequest


class StartLocation(LlmRequest):

    def __init__(self) -> None:
        super().__init__()
        self.location_prompt = llm_config.params['CREATE_LOCATION_PROMPT']
        self.start_location_prompt = llm_config.params['START_LOCATION_PROMPT']
        self.items_prompt = llm_config.params['ITEMS_PROMPT']

    def build_prompt(self, args: dict) -> str:
        zone_info = args['zone_info']
        location = args['location']
        story_type = args['story_type']
        world_info = args['world_info']
        story_context = args['story_context']

        items_prompt = ''
        item_amount = random.randint(0, 2)
        if item_amount > 0:
            items_prompt = self.items_prompt.format(items=item_amount)

        prompt = self.start_location_prompt.format(
            story_type=story_type,
            world_info=world_info,
            location_description=location.description,
            zone_info=zone_info,
            story_context=story_context,
            spawn_prompt='',
            items_prompt=items_prompt)

        return prompt
