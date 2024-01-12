
from copy import deepcopy
import json
from tale import parse_utils
from tale.base import Location
from tale.llm import llm_config
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
from tale.llm.llm_io import IoUtil
from tale.quest import Quest, QuestType

class QuestBuilding():

    def __init__(self, backend: str, io_util: IoUtil, default_body: dict):
        self.default_body = default_body
        self.pre_prompt = llm_config.params['PRE_PROMPT']
        self.backend = backend
        self.io_util = io_util
        self.json_grammar = llm_config.params['JSON_GRAMMAR']
        self.quest_prompt = llm_config.params['QUEST_PROMPT']
        self.note_quest_prompt = llm_config.params['NOTE_QUEST_PROMPT']
        self.note_lore_prompt = llm_config.params['NOTE_LORE_PROMPT']

    def generate_quest(self, base_quest: dict, character_name: str, location: Location, context: WorldGenerationContext, character_card: str = '', story_type: str = '', world_info: str = '', zone_info: str = '') -> Quest:
        prompt = self.pre_prompt
        prompt += self.quest_prompt.format(
            context='',
            base_quest=base_quest,
            location_name=location.name,
            character_name=character_name,
            character=character_card,
            zone_info=zone_info)
        request_body = deepcopy(self.default_body)
        text = self.io_util.synchronous_request(request_body, prompt=prompt, context=context)
        return parse_utils.trim_response(text)
    
    def generate_note_quest(self, context: WorldGenerationContext, zone_info: str) -> Quest:
        prompt = self.pre_prompt
        prompt += self.note_quest_prompt.format(
            context='',
            zone_info=zone_info)
        request_body = deepcopy(self.default_body)
        request_body['grammar'] = self.json_grammar
        text = self.io_util.synchronous_request(request_body, prompt=prompt, context=context)
        quest_data = json.loads(parse_utils.sanitize_json(text))
        return Quest(name=quest_data['name'], type=QuestType[quest_data['type'].upper()], reason=quest_data['reason'], target=quest_data['target'])