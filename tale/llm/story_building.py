# This file contains the StoryBuilding class, which is responsible for generating the story background
from tale import parse_utils
from tale.llm import llm_config
from tale.llm.contexts.AdvanceStoryContext import AdvanceStoryContext
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.story_context import StoryContext


class StoryBuilding():

    def __init__(self, io_util: IoUtil, default_body: dict, backend: str = 'kobold_cpp'):
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body
        self.story_background_prompt = llm_config.params['STORY_BACKGROUND_PROMPT'] # Type: str
        self.advance_story_prompt = llm_config.params['ADVANCE_STORY_PROMPT'] # Type: str

    def generate_story_background(self, world_mood: int, world_info: str, story_type: str) -> str:
        prompt = self.story_background_prompt.format(
            story_type=story_type,
            world_mood=parse_utils.mood_string_from_int(world_mood),
            world_info=world_info)
        request_body = self.default_body
        return self.io_util.synchronous_request(request_body, prompt=prompt)
    
    def advance_story_section(self, story_context: StoryContext) -> str:
        context = AdvanceStoryContext(story_context)
        prompt = self.advance_story_prompt.format(context=context.to_prompt_string())
        request_body = self.default_body
        result = self.io_util.synchronous_request(request_body, prompt=prompt)
        story_context.set_current_section(result)
        return result
    