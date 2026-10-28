from copy import deepcopy
import json

from tale import json_util, parse_utils
from tale.base import Location
from tale.llm import llm_config
from tale.llm.character_card import CharacterCard
from tale.llm.contexts.ActionContext import ActionContext
from tale.llm.contexts.CharacterContext import CharacterContext
from tale.llm.contexts.FollowContext import FollowContext
from tale.llm.llm_io import IoUtil
from tale.llm.contexts.DialogueContext import DialogueContext
from tale.llm.responses.ActionResponse import ActionResponse
from tale.llm.responses.FollowResponse import FollowResponse
from tale.llm.schemas import ActionListSchema, CharacterSchema, DialogueSchema, FollowSchema
from tale.load_character import CharacterV2


class CharacterBuilding():

    def __init__(self, backend: str, io_util: IoUtil, default_body: dict):
        self.pre_prompt = llm_config.params['PRE_PROMPT']
        self.dialogue_prompt = llm_config.params['DIALOGUE_PROMPT']
        self.character_prompt = llm_config.params['CREATE_CHARACTER_PROMPT']
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body
        self.travel_prompt = llm_config.params['TRAVEL_PROMPT']
        self.reaction_prompt = llm_config.params['REACTION_PROMPT']
        self.idle_action_prompt = llm_config.params['IDLE_ACTION_PROMPT']
        self.free_form_action_prompt = llm_config.params['ACTION_PROMPT']
        self.dialogue_template = llm_config.params['DIALOGUE_TEMPLATE']
        self.action_template = llm_config.params['ACTION_TEMPLATE']
        self.character_template = llm_config.params['CHARACTER_TEMPLATE']
        self.request_follow_prompt = llm_config.params['REQUEST_FOLLOW_PROMPT']
        self.follow_template = llm_config.params['FOLLOW_TEMPLATE']

    def generate_dialogue(self,
                          context: DialogueContext,
                          sentiment = '',
                          short_len : bool=False):
        prompt = self.pre_prompt

        prompt += self.dialogue_prompt.format(
                context = '{context}',
                previous_conversation=context.conversation,
                character2=context.speaker_name,
                character1=context.target_name,
                dialogue_template=self.dialogue_template,
                sentiment=sentiment)
        request_body = deepcopy(self.default_body)

        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=DialogueSchema, context=context.to_prompt_string())
            text = model.response
            new_sentiment = model.sentiment if model.sentiment else None
            item = model.give if isinstance(model.give, str) else None
        except Exception as exc:
            print(f'Failed to parse dialogue {exc}')
            return None, None, None

        return text, item, new_sentiment

    def generate_character(self, character_context: CharacterContext) -> CharacterV2:
        """ Generate a character card based on the current story context"""
        prompt = self.character_prompt.format(
            context = '{context}',
            character_template=self.character_template,
            keywords=', '.join(character_context.key_words))
        request_body = deepcopy(self.default_body)
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=CharacterSchema, context=character_context.to_prompt_string())
            return CharacterV2().from_json(model.model_dump())
        except Exception as exc:
            print(f'Exception while generating character: {exc}')
            return None

    def perform_idle_action(self, character_name: str, location: Location, story_context: str, character_card: CharacterCard, sentiments: dict = {}, last_action: str = '', event_history: str = '') -> list:
        characters = {}
        for living in location.livings:
            if living.visible and living.name != character_name.lower():
                if living.alive:
                    characters[living.name] = living.short_description
                else:
                    characters[living.name] = f"{living.short_description} (dead)"
        items = [item.name for item in location.items if item.visible]
        prompt = self.idle_action_prompt.format(
            last_action=last_action if last_action else f"{character_name} arrives in {location.name}",
            location=": ".join([location.title, location.short_description]),
            story_context=story_context,
            character_name=character_name,
            character=character_card,
            items=items,
            characters=json.dumps(characters),
            history=event_history.replace('<break>', '\n'),
            sentiments=json.dumps(sentiments))
        request_body = deepcopy(self.default_body)
        if self.backend == 'kobold_cpp':
            request_body['banned_tokens'] = ['You']

        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        if not text:
            return None
        text = json_util.strip_reasoning_sections(text)
        return parse_utils.trim_response(text)

    def perform_travel_action(self, character_name: str, location: Location, locations: list, directions: list, character_card: CharacterCard):
        if location.name in locations:
            locations.remove(location.name)

        prompt = self.pre_prompt
        prompt += self.travel_prompt.format(
            location_name=location.name,
            locations=locations,
            directions=directions,
            character=character_card,
            character_name=character_name)
        request_body = deepcopy(self.default_body)
        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        text = json_util.strip_reasoning_sections(text)
        return parse_utils.trim_response(text)

    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, story_context: str, character_card: CharacterCard, sentiment: str = '', event_history: str = ''):
        prompt = self.pre_prompt
        prompt += self.reaction_prompt.format(
            action=action,
            location_name=location.name,
            character_name=character_name,
            character=character_card,
            acting_character_name=acting_character_name,
            story_context=story_context,
            history=event_history.replace('<break>', '\n'),
            sentiment=sentiment)
        request_body = deepcopy(self.default_body)
        text = self.io_util.synchronous_request(request_body, prompt=prompt)
        text = json_util.strip_reasoning_sections(text)
        return parse_utils.trim_response(text) + "\n"

    def free_form_action(self, action_context: ActionContext) -> list:
        prompt = self.pre_prompt
        prompt += self.free_form_action_prompt.format(
            context = '{context}',
            character_name=action_context.character_name,
            previous_events=action_context.event_history.replace('<break>', '\n'),
            action_template=self.action_template)
        request_body = deepcopy(self.default_body)
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=ActionListSchema, context=action_context.to_prompt_string())
            return [ActionResponse(action) for action in model.actions]
        except Exception as exc:
            print('Failed to parse action ' + str(exc))
            return None

    def request_follow(self, follow_context: FollowContext) -> FollowResponse:
        prompt = self.pre_prompt
        prompt += self.request_follow_prompt.format(
            context=follow_context.to_prompt_string(),
            character_name=follow_context.character_name,
                                                    target=follow_context.asker_name,
                                                    follow_template=self.follow_template,
                                                    target_reason=follow_context.asker_reason)
        request_body = deepcopy(self.default_body)
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=FollowSchema)
            return FollowResponse(model)
        except Exception as exc:
            print(f'Failed to parse follow response: {exc}')
            return None
