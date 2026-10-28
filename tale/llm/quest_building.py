from copy import deepcopy
from tale import parse_utils
from tale.base import Location
from tale.llm import llm_config
from tale.llm.character_card import CharacterCard
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
from tale.llm.llm_io import IoUtil
from tale.llm.schemas import NoteQuestSchema
from tale.quest import Quest, QuestType

class QuestBuilding():

    def __init__(self, backend: str, io_util: IoUtil, default_body: dict):
        self.default_body = default_body
        self.pre_prompt = llm_config.params['PRE_PROMPT']
        self.backend = backend
        self.io_util = io_util

    def generate_quest(self, base_quest: dict, character_name: str, location: Location, context: WorldGenerationContext, character_card: CharacterCard, story_type: str = '', world_info: str = '', zone_info: str = '') -> Quest:
        prompt = self.pre_prompt
        prompt += llm_config.params['QUEST_PROMPT'].format(
            context='{context}',
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
        prompt += llm_config.params['NOTE_QUEST_PROMPT'].format(
            context='{context}',
            zone_info=zone_info)
        request_body = deepcopy(self.default_body)
        model = self.io_util.structured_request(request_body, prompt=prompt, model=NoteQuestSchema, context=context)
        return Quest(name=model.name, type=QuestType[model.type.upper()], reason=model.reason, target=model.target)
