"""LLM-facing "brain" of an NPC.

All LLM calls made by a LivingNpc go through NpcAgent. The LlmUtil is
injectable (tests pass a fake/stub); by default it resolves lazily to the
global driver's llm_util at call time, so NPCs can be constructed before the
driver exists.
"""

from tale import mud_context
from tale.base import Location, MudObject
from tale.llm.character_card import CharacterCard
from tale.llm.responses.FollowResponse import FollowResponse


class NpcAgent:

    def __init__(self, llm_util=None):
        self._llm_util = llm_util

    @property
    def llm_util(self):
        if self._llm_util is not None:
            return self._llm_util
        return mud_context.driver.llm_util

    def generate_dialogue(self, *, conversation: str, character_card: CharacterCard,
                          character_name: str, target: str, target_description: str = '',
                          sentiment: str = '', location_description: str = '', short_len: bool = False):
        """Returns (response, item, sentiment)."""
        return self.llm_util.generate_dialogue(
            conversation=conversation,
            character_card=character_card,
            character_name=character_name,
            target=target,
            target_description=target_description,
            sentiment=sentiment,
            location_description=location_description,
            short_len=short_len)

    def perform_reaction(self, *, action: str, character_card: CharacterCard, character_name: str,
                         location: Location, acting_character_name: str = '',
                         event_history: str = '', sentiment: str = ''):
        return self.llm_util.perform_reaction(
            action=action,
            character_name=character_name,
            acting_character_name=acting_character_name,
            location=location,
            character_card=character_card,
            sentiment=sentiment,
            event_history=event_history)

    def perform_idle_action(self, *, character_card: CharacterCard, character_name: str,
                            location: Location, last_action='', event_history: str = '',
                            sentiments: dict = None):
        return self.llm_util.perform_idle_action(
            character_name=character_name,
            location=location,
            character_card=character_card,
            sentiments=sentiments or {},
            last_action=last_action,
            event_history=event_history)

    def free_form_action(self, *, character_card: CharacterCard, character_name: str,
                         location: Location, event_history: str = '') -> list:
        """Returns a list of ActionResponse, or None on parse failure."""
        return self.llm_util.free_form_action(
            location=location,
            character_name=character_name,
            character_card=character_card,
            event_history=event_history)

    def request_follow(self, *, actor: MudObject, character_name: str, character_card: CharacterCard,
                       event_history: str, location: Location, asker_reason: str) -> FollowResponse:
        return self.llm_util.request_follow(
            actor=actor,
            character_name=character_name,
            character_card=character_card,
            event_history=event_history,
            location=location,
            asker_reason=asker_reason)

    def generate_image(self, name: str, description='') -> bool:
        return self.llm_util.generate_image(name, description)
