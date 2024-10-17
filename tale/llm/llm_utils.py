from copy import deepcopy
import json
import os
import sys
from typing import Any, Tuple
import yaml
from tale.base import Location, MudObject
from tale.image_gen.base_gen import ImageGeneratorBase
from tale.llm import llm_config
from tale.llm.character import CharacterBuilding
from tale.llm.contexts.ActionContext import ActionContext
from tale.llm.contexts.CharacterContext import CharacterContext
from tale.llm.contexts.DungeonLocationsContext import DungeonLocationsContext
from tale.llm.contexts.EvokeContext import EvokeContext
from tale.llm.contexts.FollowContext import FollowContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.contexts.DialogueContext import DialogueContext
from tale.llm.quest_building import QuestBuilding
from tale.llm.responses.ActionResponse import ActionResponse
from tale.llm.responses.LocationDescriptionResponse import LocationDescriptionResponse
from tale.llm.responses.LocationResponse import LocationResponse
from tale.llm.responses.WorldCreaturesResponse import WorldCreaturesResponse
from tale.llm.responses.WorldItemsResponse import WorldItemsResponse
from tale.llm.story_building import StoryBuilding
from tale.llm.world_building import WorldBuilding
from tale.mob_spawner import MobSpawner
from tale.player import PlayerConnection
from tale.player_utils import TextBuffer
import tale.parse_utils as parse_utils
import tale.llm.llm_cache as llm_cache
from tale.quest import Quest
from tale.web.web_utils import copy_single_image
from tale.zone import Zone

class LlmUtil():
    """ Prepares prompts for various LLM requests"""

    def __init__(self, io_util: IoUtil = None):
        self.backend = llm_config.params['BACKEND']
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../../backend_{self.backend}.yaml")), "r") as stream:
            try:
                backend_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.default_body = json.loads(backend_config['DEFAULT_BODY'])
        self.memory_size = llm_config.params['MEMORY_SIZE']
        self.pre_prompt = llm_config.params['PRE_PROMPT'] # type: str
        self.evoke_prompt = llm_config.params['BASE_PROMPT'] # type: str
        self.combat_prompt = llm_config.params['COMBAT_PROMPT'] # type: str
        self.word_limit = llm_config.params['WORD_LIMIT']
        self.short_word_limit = llm_config.params['SHORT_WORD_LIMIT']
        self.story_background_prompt = llm_config.params['STORY_BACKGROUND_PROMPT'] # type: str
        self.day_cycle_event_prompt = llm_config.params['DAY_CYCLE_EVENT_PROMPT'] # type: str
        self.narrative_event_prompt = llm_config.params['NARRATIVE_EVENT_PROMPT']
        self.__story = None # type: DynamicStory
        self.io_util = io_util or IoUtil(config=llm_config.params, backend_config=backend_config)
        self.stream = backend_config['STREAM']
        self.connection = None # type: PlayerConnection
        self._image_gen = None # type: ImageGeneratorBase
        self.__story_context = ''
        self.__story_type = ''
        self.__world_info = ''
        self.action_list = llm_config.params['ACTION_LIST']
        json_grammar_key = backend_config['JSON_GRAMMAR_KEY']
        
        #self._look_hashes = dict() # type: dict[int, str] # location hashes for look command. currently never cleared.
        self._world_building = WorldBuilding(default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend,
                                             json_grammar_key=json_grammar_key)
        self._character = CharacterBuilding(backend=self.backend,
                                    io_util=self.io_util,
                                    default_body=self.default_body,
                                             json_grammar_key=json_grammar_key)
        self._story_building = StoryBuilding(default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend)
        self._quest_building = QuestBuilding(default_body=self.default_body,
                                             io_util=self.io_util,
                                             backend=self.backend,
                                             json_grammar_key=json_grammar_key)

    def evoke(self, message: str, short_len: bool=False, rolling_prompt: str = '', alt_prompt: str = '', extra_context: str = '', skip_history: bool = True):
        """Evoke a response from LLM. Async if stream is True, otherwise synchronous.
        Update the rolling prompt with the latest message.
        Will put generated text in lm_cache.look_hashes, and reuse it if same hash is generated."""
        output_template = 'Original:[<it><rev> {message}</>] <bright><rev>Generated:</>{text}'

        if not message or str(message) == "\n":
            str(message), rolling_prompt

        rolling_prompt = self.update_memory(rolling_prompt, message)

        text_hash_value = llm_cache.generate_hash(message + extra_context)

        cached_look = llm_cache.get_looks([text_hash_value])
        if cached_look:
            return output_template.format(message=message, text=cached_look), rolling_prompt
        trimmed_message = parse_utils.remove_special_chars(str(message))
        time_of_day = ''
        if self.__story.config.day_night:
            time_of_day = self.__story.day_cycle.time_of_day.__str__
        story_context = EvokeContext(story_context=self.__story_context, 
                                        time_of_day=time_of_day,
                                        history=rolling_prompt if not (skip_history or alt_prompt) else '', 
                                        extra_context=extra_context)
        prompt = self.pre_prompt
        prompt += (alt_prompt or self.evoke_prompt).format(
            context = '{context}',
            max_words=self.word_limit if not short_len else self.short_word_limit,
            input_text=str(trimmed_message))
        request_body = deepcopy(self.default_body)

        if not self.stream:
            text = self.io_util.synchronous_request(request_body, prompt=prompt, context=story_context.to_prompt_string())
            llm_cache.cache_look(text, text_hash_value)
            return output_template.format(message=message, text=text), rolling_prompt
        if self.connection:
            self.connection.output(output_template.format(message=message, text=''))
        text = self.io_util.stream_request(request_body=request_body, prompt=prompt, context=story_context.to_prompt_string(), io=self.connection)
        llm_cache.cache_look(text, text_hash_value)
        return '\n', rolling_prompt
    
    def generate_dialogue(self, conversation: str, 
                          character_card: str, 
                          character_name: str, 
                          target: str, 
                          target_description: str='', 
                          sentiment = '', 
                          location_description = '',
                          short_len : bool=False):
        dialogue_context = DialogueContext(story_context=self.__story_context,
                                           location_description=location_description,
                                           speaker_card=character_card,
                                           speaker_name=character_name,
                                           target_name=target,
                                           target_description=target_description,
                                           conversation=conversation)
        return self._character.generate_dialogue(context=dialogue_context,
                                                sentiment=sentiment,
                                                short_len=short_len)
    
    def update_memory(self, rolling_prompt: str, response_text: str):
        """ Keeps a history of the last couple of events"""
        rolling_prompt += response_text
        if len(rolling_prompt) > self.memory_size:
            rolling_prompt = rolling_prompt[len(rolling_prompt) - self.memory_size + 1:]
        return rolling_prompt
    
    def generate_character(self, story_context: str = '', keywords: list = [], story_type: str = ''):
        character = self._character.generate_character(CharacterContext(story_context=story_context or self.__story_context,
                                                                       story_type=story_type or self.__story_type,
                                                                       world_info=self.__world_info,
                                                                       world_mood=self.__story.config.world_mood,
                                                                       key_words=keywords))
        if not character.avatar and self.__story.config.image_gen:
            self.generate_image(character.name, f"{character.description}. Wearing: {','.join(character.wearing)}. Holding: {character.wielding}" )
        return character
    
    def get_neighbor_or_generate_zone(self, current_zone: Zone, current_location: Location, target_location: Location) -> Zone:
        return self._world_building.get_neighbor_or_generate_zone(current_zone, current_location, target_location, self.__story)

    def build_location(self, location: Location, exit_location_name: str, zone_info: dict, world_items: dict = {}, world_creatures: dict = {}, neighbors: dict = {}) -> Tuple[LocationResponse, MobSpawner]:
        """ Generate a location based on the current story context"""
        world_generation_context = WorldGenerationContext(story_context=self.__story_context,
                                                            story_type=self.__story_type,
                                                            world_info=self.__world_info,
                                                            world_mood=self.__story.config.world_mood)
        location_result, spawner = self._world_building.build_location(location, 
                                                    exit_location_name, 
                                                    zone_info,
                                                    context=world_generation_context,
                                                    world_creatures=world_creatures if world_creatures else self.__story.catalogue._creatures,
                                                    world_items=world_items if world_items else self.__story.catalogue._items,
                                                    neighbors=neighbors)
        
        if not location.avatar and self.__story.config.image_gen:
            self.generate_image(location.name, location.description)
        return location_result, spawner
                    
     
    def perform_idle_action(self, character_name: str, location: Location, character_card: str = '', sentiments: dict = {}, last_action: str = '', event_history: str = '') -> list:
        return self._character.perform_idle_action(character_name, location, self.__story_context, character_card, sentiments, last_action, event_history=event_history)
    
    def perform_travel_action(self, character_name: str, location: Location, locations: list, directions: list, character_card: str = ''):
        return self._character.perform_travel_action(character_name, location, locations, directions, character_card)
    
    def perform_reaction(self, action: str, character_name: str, acting_character_name: str, location: Location, character_card: str = '', sentiment: str = '', event_history: str = ''):
        return self._character.perform_reaction(action=action, 
                                                character_name=character_name, 
                                                acting_character_name=acting_character_name, 
                                                location=location, character_card=character_card, 
                                                sentiment=sentiment, 
                                                story_context=self.__story_context,
                                                event_history=event_history)
    
    def generate_story_background(self, world_mood: int, world_info: str, story_type: str):
        return self._story_building.generate_story_background(world_mood, world_info, story_type)
    
    def generate_start_location(self, location: Location, zone_info: dict, story_type: str, story_context: str, world_info: str, world_mood: int = 0, world_items: dict = {}) -> LocationResponse:
        return self._world_building.generate_start_location(location, zone_info, WorldGenerationContext(story_context=story_context, 
                                                                                                        story_type=story_type, 
                                                                                                        world_info=world_info, 
                                                                                                        world_mood=world_mood), world_items=world_items)
        
    def generate_start_zone(self, location_desc: str, story_type: str, story_context: str, world_info: dict) -> Zone:
        world_generation_context = WorldGenerationContext(story_context=story_context, story_type=story_type, world_info=world_info, world_mood=world_info['world_mood'])
        return self._world_building.generate_start_zone(location_desc, context=world_generation_context)
    
    def generate_world_items(self, story_context: str = '', story_type: str = '', world_info: str = '', world_mood: int = None, item_types: list = []) -> WorldItemsResponse:
        world_generation_context = WorldGenerationContext(story_context=story_context or self.__story_context,
                                                            story_type=story_type or self.__story_type,
                                                            world_info=world_info or self.__world_info,
                                                            world_mood=world_mood or self.__story.config.world_mood)
        return self._world_building.generate_world_items(world_generation_context, item_types=item_types)
        
    
    def generate_world_creatures(self, story_context: str = '', story_type: str = '', world_info: str = '', world_mood: int = None) -> WorldCreaturesResponse:
        world_generation_context = WorldGenerationContext(story_context=story_context or self.__story_context,
                                                            story_type=story_type or self.__story_type,
                                                            world_info=world_info or self.__world_info,
                                                            world_mood=world_mood or self.__story.config.world_mood)
        return self._world_building.generate_world_creatures(world_generation_context)
        
    def generate_random_spawn(self, location: Location, zone_info: dict) -> bool:
        return self._world_building.generate_random_spawn(location=location, 
                                                          zone_info=zone_info,
                                                          context=self._get_world_context(),
                                                          world_creatures=self.__story.catalogue._creatures,
                                                          world_items=self.__story.catalogue._items)
    
    def generate_quest(self, base_quest: dict, character_name: str, location: Location, character_card: str, zone_info: dict, event_history: str = '') -> Quest:
        return self._quest_building.generate_quest(base_quest=base_quest,
                                            context=self._get_world_context(),
                                            character_name=character_name, 
                                            character_card=character_card, 
                                            location=location,
                                            zone_info=zone_info, 
                                            event_history=event_history)
    
    def generate_note_quest(self, zone_info: dict) -> Quest:
        return self._quest_building.generate_note_quest(context=self._get_world_context(), 
                                                        zone_info=zone_info)
  
    def generate_note_lore(self, zone_info: dict) -> str:
        return self._world_building.generate_note_lore(context=self._get_world_context(), 
                                                        zone_info=zone_info)
    
    def generate_dungeon_locations(self, zone_info: dict, locations: list, depth: int, max_depth: int) -> LocationDescriptionResponse:
        return self._world_building.generate_dungeon_locations(context=DungeonLocationsContext(story_context=self.__story_context,
                                                                                                    story_type=self.__story.config.type,
                                                                                                    world_info=self.__story.config.world_info,
                                                                                                    world_mood=self.__story.config.world_mood,
                                                                                                    zone_info=zone_info,
                                                                                                    rooms=locations,
                                                                                                    depth=depth,
                                                                                                    max_depth=max_depth))

    # visible for testing
    def generate_image(self, name: str, description: dict = '', save_path: str = "./resources", copy_file: bool = True, target: MudObject = None, id: str = None) -> bool:
        if not self._image_gen:
            return False
        image_name = name.lower().replace(' ', '_')
        if self._image_gen.generate_in_background:

            def on_complete():
                 if self.connection:
                    self.connection.io.send_data('{"data":"result", "id":"image"}'.format(result=image_name, image=id if id else name))
                 if copy_file:  
                    copy_single_image('./', image_name + '.jpg')
                 if target:
                    target.avatar = image_name + '.jpg'
            #on_complete = lambda : self.connection.io.send_data('{"data":"result", "id":"image"}'.format(result=image_name, image=name)) if self.connection else None;copy_single_image('./', image_name + '.jpg') if copy_file else None;target.avatar = name + '.jpg' if target else None
            return self._image_gen.generate_background(prompt=description, save_path=save_path , image_name=image_name, on_complete=on_complete)
        else:
            result = self._image_gen.generate_image(prompt=description, save_path=save_path , image_name=image_name)
            if result and copy_file:
                copy_single_image('./', image_name + '.jpg')
            if result and target:
                target.avatar = image_name + '.jpg'
            return result

    def free_form_action(self, location: Location, character_name: str,  character_card: str = '', event_history: str = '') -> list:
        action_context = ActionContext(story_context=self.__story_context,
                                       story_type=self.__story_type,
                                       character_name=character_name,
                                       character_card=character_card,
                                       event_history=event_history,
                                       location=location,
                                       actions=self.action_list)
        return self._character.free_form_action(action_context)

    def request_follow(self, actor: MudObject, character_name: str, character_card: str, event_history: str, location: Location, asker_reason: str):
        return self._character.request_follow(FollowContext(story_context=self.__story_context,
                                        story_type=self.__story_type,
                                        character_name=character_name,
                                        character_card=character_card,
                                        event_history=event_history,
                                        location=location,
                                        asker_name=actor.title,
                                        asker_card=actor.short_description,
                                        asker_reason=asker_reason))
    
    def describe_day_cycle_transition(self, player: PlayerConnection, from_time: str, to_time: str) -> str:
        prompt = self.pre_prompt
        location = player.player.location
        context = self._get_world_context()
        prompt += self.day_cycle_event_prompt.format(
            context= '{context}',
            location_name=location.name,
            from_time=from_time,
            to_time=to_time)
        request_body = deepcopy(self.default_body)

        if not self.stream:
            text = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string() + f'Location: {location.name, location.description};')
            location.tell(text, evoke=False)
            return text
        text = self.io_util.stream_request(request_body=request_body, prompt=prompt, context=context.to_prompt_string() + f'Location: {location.name, location.description};', io=player)
        return text
    
    def generate_narrative_event(self, location: Location) -> str:
        prompt = self.pre_prompt
        context = self._get_world_context()
        prompt += self.narrative_event_prompt.format(
            context= '{context}',
            location_name=location.name)
        request_body = deepcopy(self.default_body)

        text = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string() + f'Location: {location.name, location.description};')
        location.tell(text, evoke=False)
        return text
  
    def set_story(self, story: DynamicStory):
        """ Set the story object."""
        self.__story = story
        self.__story_context = story.config.context
        self.__story_type = story.config.type
        self.__world_info = story.config.world_info
        if story.config.image_gen:
            self._init_image_gen(story.config.image_gen)

    def _init_image_gen(self, image_gen: str):
        """ Initialize the image generator"""
        clazz =  getattr(sys.modules['tale.image_gen.' + image_gen.lower()], image_gen)
        self._image_gen = clazz()

    def _get_world_context(self):
        return WorldGenerationContext(story_context=self.__story_context,
                                        story_type=self.__story_type,
                                        world_info=self.__world_info,
                                        world_mood=self.__story.config.world_mood)




